#!/usr/bin/env python3
import argparse
import json
import logging
import os.path
import re
import signal
import sys
import time
import random

from datetime import datetime
from multiprocessing import Pool
from threading import Timer

import requests

import flagids
import exploits

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

    parser.add_argument('-p', '--type',
                        type=str,
                        required=False,
                        default="ccit",
                        choices=["ccit", "hitb"],
                        help='Maximum number of threads to spawn')

    parser.add_argument('-n', '--num-threads',
                        type=int,
                        metavar='THREADS',
                        required=False,
                        default=64,
                        help='Maximum number of threads to spawn')

    return parser.parse_args()


def get_config_from_server(server_url, token):
    # Retrieve configuration from server
    logging.info('Connecting to the flagWarehouse server...')

    r = None
    try:
        r = requests.get(server_url + '/api/get_config',
                         headers={'X-Auth-Token': token})
        if r.status_code == 403:
            logging.error('Wrong authorization token.')
            logging.info('Exiting...')
            sys.exit(0)

        if r.status_code != 200:
            logging.error(f'GET {server_url}/api/get_config responded with [{r.status_code}].')
            logging.info('Exiting...')
            sys.exit(0)

    except requests.exceptions.RequestException as e:
        logging.error(f'Could not connect to {server_url}: ' +
                      e.__class__.__name__)
        logging.info('Exiting...')
        sys.exit(0)

    # Parse server config
    config = r.json()
    # Print server config
    if verbose:
        logging.debug(json.dumps(config, indent=4, sort_keys=True))

    return config


def main(args):
    global pool
    print(BANNER)

    # Parse parameters
    server_url = args.server_url
    user = args.user
    token = args.token
    global verbose
    verbose = args.verbose
    exploit_directory = args.exploit_directory
    num_threads = args.num_threads

    logging.basicConfig(format='%(asctime)s %(levelname)s - %(message)s',
                        datefmt='%H:%M:%S', level=logging.DEBUG if verbose else logging.INFO)

    config = get_config_from_server(server_url, token)
    flag_format = re.compile(config['format'])
    round_duration = config['round']
    teams = config['teams']
    nopTeam = config.get('nop_team', '')
    flagid_url = config.get('flagid_url', '')
    team_token = config['team_token']
    logging.info('Client correctly configured.')

    flag_ids_downloader = flagids.Flag_Ids_Downloader(flagid_url, nopTeam, team_token, args.type)

    # MAIN LOOP
    while True:
        try:
            requests.head(server_url)
            s_time = time.time()

            # Retrieve flag_ids
            if flagid_url:
                if not flag_ids_downloader.download_flag_ids():
                    continue

            # Load exploits
            scripts = exploits.load_exploits(exploit_directory)

            if scripts:
                logging.info(f'Starting new round. Running {len(scripts)} exploits.')
                logging.debug(f"Exploits: [{', '.join(map(lambda script: os.path.basename(script), scripts))}]")
            else:
                logging.info('No exploits found: retrying in 15 seconds')
                time.sleep(15)
                continue

            original_sigint_handler = signal.signal(signal.SIGINT, signal.SIG_IGN)
            pool = Pool(min(num_threads, len(scripts) * len(teams)))
            signal.signal(signal.SIGINT, original_sigint_handler)

            # Run exploits
            random.shuffle(scripts)
            random.shuffle(teams)

            for script in scripts:
                for team in teams:
                    pool.apply_async(
                        exploits.run_exploit, (script, team, round_duration, server_url, token, flag_format, user))
            pool.close()
            pool.join()

            duration = time.time() - s_time
            logging.debug(f'round took {round(duration, 1)} seconds')

            if duration < round_duration:
                logging.debug(f'Sleeping for {round(round_duration - duration, 1)} seconds')
                time.sleep(round_duration - duration)

        # Exceptions
        except KeyboardInterrupt:
            logging.info('Caught KeyboardInterrupt. Bye!')
            pool.terminate()
            break
        except requests.exceptions.RequestException:
            logging.error('Could not communicate with the server: retrying in 5 seconds.')
            time.sleep(5)
            continue


if __name__ == '__main__':
    main(parse_args())
