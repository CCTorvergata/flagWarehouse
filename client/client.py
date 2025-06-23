#!/usr/bin/env python3
import argparse
import logging
import math
import os
import os.path
import re
import signal
import subprocess
import sys
import time
import random
from datetime import datetime
from multiprocessing import Pool, Manager
from threading import Timer, Thread, Event
from queue import Empty

import requests


END				= "\033[0m"

GREY			= "\033[30m"
RED				= "\033[31m"
GREEN			= "\033[32m"
YELLOW			= "\033[33m"
BLUE			= "\033[34m"
PURPLE			= "\033[35m"
CYAN			= "\033[36m"

HIGH_RED		= "\033[91m"



BANNER = '''
  ___ __               ________                    __
.'  _|  |.---.-.-----.|  |  |  |.---.-.----.-----.|  |--.-----.--.--.-----.-----.
|   _|  ||  _  |  _  ||  |  |  ||  _  |   _|  -__||     |  _  |  |  |__ --|  -__|
|__| |__||___._|___  ||________||___._|__| |_____||__|__|_____|_____|_____|_____|
               |_____|

          The perfect solution for running all your exploits in one go!

'''[1:]

# --- NUOVA COSTANTE ---
SUBMISSION_INTERVAL = 15  # Invia flag ogni 15 secondi

def parse_args():
    # noinspection PyTypeChecker
    parser = argparse.ArgumentParser(description='''Run all the exploits in the specified
                                                directory against all the teams.''',
                                     formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    parser.add_argument('-s', '--server-url',
                        type=str,
                        metavar='URL',
                        default='http://localhost:5555',
                        help='The URL of your flagWarehouse server. Please specify the protocol')

    parser.add_argument('-u', '--user',
                        type=str,
                        metavar='USER',
                        required=True,
                        help='Your username')

    parser.add_argument('-t', '--token',
                        type=str,
                        metavar='TOKEN',
                        required=True,
                        help='The authorization token used for the flagWarehouse server API')

    parser.add_argument('-d', '--exploit-directory',
                        type=str,
                        metavar='DIR',
                        required=True,
                        help='The directory that holds all your exploits')

    parser.add_argument('-v', '--verbose',
                        action='store_true',
                        help='Verbose output')

    parser.add_argument('-y', '--type',
                        type=str,
                        choices=['ccit', 'hitb'],
                        default='ccit',
                        help='type of flagids')

    parser.add_argument('-n', '--num-threads',
                        type=int,
                        metavar='THREADS',
                        required=False,
                        default=64,
                        help='Maximum number of threads to spawn')

    return parser.parse_args()


def parse_flag(flag_str):
    """Funzione helper per parsare la flag e gestire eccezioni."""
    try:
        # Usiamo sempre stringhe per consistenza nelle chiavi
        round_number = str(int(flag_str[0:2], 36))
        team_number = str(int(flag_str[2:4], 36))
        service_number = str(int(flag_str[4:6], 36))
        return round_number, team_number, service_number
    except (ValueError, IndexError):
        return None, None, None


def run_exploit(exploit_path, team_ip, rounds, round_duration, flag_pattern, user, 
                service_status, exploit_to_service_map, last_success_memory, flag_queue):
    """
    Esegue un exploit usando una struttura dati condivisa "piatta" e salvando il nome dell'exploit.
    """
    def timer_out(process):
        timer.cancel()
        try: process.kill()
        except ProcessLookupError: pass

    exploit_name = os.path.basename(exploit_path)
    team_number_str = team_ip.split('.')[2]

    for round_num in rounds:
        round_num_str = str(round_num)
        
        known_service_id = exploit_to_service_map.get(exploit_name)
        if known_service_id:
            status_key = f"{known_service_id}:{team_number_str}:{round_num_str}"
            if service_status.get(status_key):
                #logging.debug(f"SKIP: Key {status_key} already completed by {service_status.get(status_key)}. Skipping {exploit_name}.")
                continue

        p = None
        try:
            p = subprocess.Popen([exploit_path, team_ip, str(round_num)], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            timer = Timer(math.ceil(0.9 * round_duration / len(rounds)), timer_out, args=[p])
            timer.start()

            for line in iter(p.stdout.readline, b''):
                output = line.decode(errors='ignore').strip()
                if not output: continue

                for f in set(flag_pattern.findall(output)):
                    parsed_round, parsed_team, parsed_service = parse_flag(f)
                    if not parsed_service:
                        logging.warning(f"Flag malformata da {exploit_name}: {f}")
                        continue

                    if exploit_name not in exploit_to_service_map:
                        exploit_to_service_map[exploit_name] = parsed_service
                        logging.info(f"LEARNED: {BLUE}{exploit_name}{END} targets service {CYAN}{parsed_service}{END}")

                    status_key = f"{parsed_service}:{parsed_team}:{parsed_round}"
                    service_status[status_key] = exploit_name

                    memory_key = f"{parsed_service}:{parsed_team}"
                    current_max_round, _ = last_success_memory.get(memory_key, (-1, None))

                    # Parsiamo il round corrente come intero per il confronto
                    current_round_int = int(parsed_round)

                    if current_round_int > current_max_round:
                        last_success_memory[memory_key] = (current_round_int, exploit_name)
                        # logging.info(f"MEMORY UPDATE: For {memory_key}, new best exploit is {exploit_name} from round {current_round_int}")
                    
                    logging.info(f"Got flag from {BLUE}{exploit_name}{END} for service {CYAN}{parsed_service}{END}, team {parsed_team}, round {parsed_round}")
                    
                    flag_data = {'flag': f, 'exploit_name': exploit_name, 'team_ip': team_ip, 'time': datetime.now().isoformat(sep=' ')}
                    flag_queue.put(flag_data)

            p.stdout.close()
            return_code = p.wait()
            timer.cancel()

            if return_code not in [0, -9, -15]:  # 0=OK, -9=SIGKILL, -15=SIGTERM
                stderr_output = p.stderr.read().decode(errors='ignore').strip()
                if stderr_output: # Logga solo se c'è un output di errore
                    logging.error(f'{RED}{exploit_name}{END}@{team_ip} (round {round_num}) terminato con codice {HIGH_RED}{return_code}{END}. Stderr: {stderr_output}')
            
            p.stderr.close()

        except Exception as e:
            logging.error(f"Errore imprevisto eseguendo {exploit_name} su {team_ip}: {e}")
        finally:
            if p and p.poll() is None:
                p.kill()

# --- NUOVA FUNZIONE ---
def flag_submitter(flag_queue, server_url, token, user, stop_event):
    """
    Un thread che raccoglie le flag dalla coda e le invia al server in batch.
    """
    logging.info(f"Thread submitter avviato. Invierà le flag ogni {SUBMISSION_INTERVAL} secondi.")
    while not stop_event.is_set():
        try:
            # Aspetta l'intervallo di tempo prima di provare a inviare
            stop_event.wait(SUBMISSION_INTERVAL)

            flags_to_send = []
            while not flag_queue.empty():
                try:
                    flags_to_send.append(flag_queue.get_nowait())
                except Empty:
                    # La coda è stata svuotata da un altro processo nel frattempo, usciamo dal ciclo
                    break
            
            if not flags_to_send:
                continue

            logging.info(f"Invio di {YELLOW}{len(flags_to_send)}{END} flag al server...")
            msg = {'username': user, 'flags': flags_to_send}
            
            try:
                requests.post(f"{server_url}/api/upload_flags", headers={'X-Auth-Token': token}, json=msg, timeout=10)
                logging.info(f"{GREEN}Batch di flag inviato con successo!{END}")
            except requests.exceptions.RequestException as e:
                logging.error(f"{RED}Errore nell'invio del batch di flag al server: {e}. Rimetto le flag in coda.{END}")
                # Reinserisci le flag nella coda per il prossimo tentativo
                for flag_data in flags_to_send:
                    flag_queue.put(flag_data)

        except Exception as e:
            logging.error(f"Errore critico nel thread submitter: {e}")


def main(args):
    pool = None
    manager = None
    submitter_thread = None
    stop_event = Event()
    
    print(BANNER)

    server_url, user, token, verbose, exploit_directory, num_threads = \
        args.server_url, args.user, args.token, args.verbose, args.exploit_directory, args.num_threads

    logging.basicConfig(format='%(asctime)s %(levelname)s - %(message)s', datefmt='%H:%M:%S', level=logging.DEBUG if verbose else logging.INFO)

    try:
        r = requests.get(server_url + '/api/get_config', headers={'X-Auth-Token': token}, timeout=10)
        r.raise_for_status()
    except Exception as e:
        logging.error(f"Impossibile ottenere la configurazione dal server: {e}")
        sys.exit(1)

    config = r.json()
    flag_format = re.compile(config['format'])
    round_duration = config['round']
    teams = config['teams']
    logging.info('Client configurato correttamente.')

    try:
        manager = Manager()
        service_status = manager.dict()
        exploit_to_service_map = manager.dict()
        last_success_memory = manager.dict()
        flag_queue = manager.Queue()

        submitter_thread = Thread(target=flag_submitter, args=(flag_queue, server_url, token, user, stop_event))
        submitter_thread.start()

        original_sigint_handler = signal.signal(signal.SIGINT, signal.SIG_IGN)
        pool = Pool(num_threads)
        signal.signal(signal.SIGINT, original_sigint_handler)

        while True:
            s_time = time.time()

            logging.info("Cerco nuovi exploit...")
            try:
                scripts = [os.path.basename(s) for s in os.listdir(exploit_directory)
                           if s.endswith('.py') and not s.startswith('.') and os.path.isfile(os.path.join(exploit_directory, s))]
                
                for s_name in scripts:
                    s_path = os.path.join(exploit_directory, s_name)
                    if not os.access(s_path, os.X_OK):
                        os.chmod(s_path, 0o755)
                        logging.warning(f'{s_name} non era eseguibile, imposto i permessi...')
            except (FileNotFoundError, PermissionError) as e:
                logging.error(f"Errore nella directory degli exploit: {e}, salto questo round.")
                time.sleep(15)
                continue

            if not scripts:
                logging.warning("Nessun exploit .py trovato. Riprovo tra 15 secondi.")
                time.sleep(15)
                continue

            try:
                flag_ids_resp = requests.get(f'http://10.10.0.1:8081/flagIds?team=0', timeout=5)
                flag_ids_resp.raise_for_status()
                flag_ids = flag_ids_resp.json()
                service = list(flag_ids.keys())[0]
                rounds = sorted(list(flag_ids[service]['0']))
            except (requests.exceptions.RequestException, KeyError, IndexError, ValueError) as e:
                logging.error(f"Impossibile ottenere flag ID per la gestione dei round: {e}. Salto questo round.")
                time.sleep(15)
                continue
            
            logging.info(f"Inizio nuovo round. {len(scripts)} exploit su {len(teams)} team.")
            
            prioritized_tasks = []
            other_tasks = []
            
            service_to_exploits_map = {}
            current_exploit_map = dict(exploit_to_service_map) # Create a non-proxy copy for iteration
            for exploit, service in current_exploit_map.items():
                if service not in service_to_exploits_map:
                    service_to_exploits_map[service] = []
                service_to_exploits_map[service].append(exploit)

            unknown_exploits = [s for s in scripts if s not in current_exploit_map]
            if unknown_exploits:
                service_to_exploits_map['unknown'] = unknown_exploits

            all_known_services = list(service_to_exploits_map.keys())
            random.shuffle(teams)
            random.shuffle(all_known_services)

            for team in teams:
                team_number_str = team.split('.')[2]
                for service_id in all_known_services:
                    last_successful_exploit = None

                    if service_id != 'unknown':
                        memory_key = f"{service_id}:{team_number_str}"
                        # Chiediamo alla memoria chi è stato l'ultimo vincitore
                        _round, exploit_name = last_success_memory.get(memory_key, (None, None))
                        if exploit_name:
                            last_successful_exploit = exploit_name

                    current_exploits_for_service = service_to_exploits_map[service_id]

                    if last_successful_exploit and last_successful_exploit in current_exploits_for_service:
                        exploit_path = os.path.join(exploit_directory, last_successful_exploit)
                        task_args = (exploit_path, team, rounds, round_duration, flag_format, user, service_status, exploit_to_service_map, last_success_memory, flag_queue)
                        prioritized_tasks.append(task_args)

                        for exploit_name in current_exploits_for_service:
                            if exploit_name != last_successful_exploit:
                                exploit_path = os.path.join(exploit_directory, exploit_name)
                                task_args = (exploit_path, team, rounds, round_duration, flag_format, user, service_status, exploit_to_service_map, last_success_memory, flag_queue)
                                other_tasks.append(task_args)
                    else:
                        for exploit_name in current_exploits_for_service:
                            exploit_path = os.path.join(exploit_directory, exploit_name)
                            task_args = (exploit_path, team, rounds, round_duration, flag_format, user, service_status, exploit_to_service_map, last_success_memory, flag_queue)
                            other_tasks.append(task_args)
            
            random.shuffle(other_tasks)
            tasks = prioritized_tasks + other_tasks
            logging.info(f"Created {len(tasks)} tasks ({len(prioritized_tasks)} prioritized).")
            
            pool.starmap(run_exploit, tasks)

            duration = time.time() - s_time
            logging.info(f"Round completato in {duration:.2f} secondi.")
            if duration < round_duration:
                sleep_time = round_duration - duration
                logging.info(f"In attesa per {sleep_time:.2f} secondi...")
                time.sleep(sleep_time)

    except KeyboardInterrupt:
        logging.info('Caught KeyboardInterrupt. Termino i processi... Bye!')
    finally:
        logging.info("Inizio procedura di spegnimento...")
        if pool:
            pool.terminate()
            pool.join()
        
        # Ferma il thread submitter
        if submitter_thread:
            logging.info("Fermo il thread submitter...")
            stop_event.set()
            submitter_thread.join() # Attende la terminazione del thread

        # Prima di chiudere il manager, prova a inviare le flag rimaste in coda.
        if manager:
            logging.info("Tento un ultimo invio delle flag rimaste in coda...")
            # Creiamo una funzione locale o la chiamiamo direttamente
            # per svuotare la coda un'ultima volta.
            flags_to_send = []
            while not flag_queue.empty():
                try:
                    flags_to_send.append(flag_queue.get_nowait())
                except Empty:
                    break
            
            if flags_to_send:
                logging.info(f"Invio finale di {YELLOW}{len(flags_to_send)}{END} flag.")
                try:
                    msg = {'username': user, 'flags': flags_to_send}
                    requests.post(f"{server_url}/api/upload_flags", headers={'X-Auth-Token': token}, json=msg, timeout=10)
                    logging.info(f"{GREEN}Batch finale inviato con successo!{END}")
                except requests.exceptions.RequestException as e:
                    logging.error(f"{RED}Errore nell'invio del batch finale: {e}{END}")
                    logging.error(f"{RED}Le seguenti flag potrebbero essere andate perse: {[f['flag'] for f in flags_to_send]}{END}")
        
        if manager:
            manager.shutdown()
        logging.info("Spegnimento completato.")

if __name__ == '__main__':
    main(parse_args())