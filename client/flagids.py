import json
import logging
import os.path

import requests


class Flag_Ids_Downloader:
    def __init__(self, flagid_url, nopTeam, team_token, flagid_type):
        self.flagid_url = flagid_url
        self.nopTeam = nopTeam
        self.team_token = team_token

        if flagid_type.lower() == "ccit":
            self.download_flag_ids = self.__download_flag_ids_ccit
        elif flagid_type.lower() == "hitb":
            self.download_flag_ids = self.__download_flag_ids_hitb
        else:
            raise TypeError

    def __download_flag_ids_ccit(self) -> bool:
        """
        Returns True if successful
        """
        try:
            r = requests.get(self.flagid_url + "?team=" + self.nopTeam, timeout=15)

            if r.status_code != 200:
                logging.error(
                    f'{self.flagid_url} responded with {r.status_code}: Retrying in 5 seconds.')
                time.sleep(5)
                return False

            services = list(r.json().keys())
            flag_ids = {}
            fail = False
            for service in services:
                r = requests.get(self.flagid_url + "?service=" + service, timeout=15)
                if r.status_code != 200:
                    logging.error(
                        f'{self.flagid_url} responded with {r.status_code}: Retrying in 5 seconds.')
                    fail = True
                    break
                flag_ids[service] = r.json().get(service, {})
            if fail:
                time.sleep(5)
                return False

            dir_path = os.path.dirname(os.path.realpath(__file__))
            with open(f'{dir_path}/flag_ids.json', 'w', encoding='utf-8') as f:
                json.dump(flag_ids, f)
            return True

        except TimeoutError:
            logging.error(
                f'{self.flagid_url} timed out: Retrying in 5 seconds.')
            time.sleep(5)
            return False


    def __download_flag_ids_hitb(self) -> bool:
        """
        Returns True if successful
        """
        try:
            r = requests.get(self.flagid_url + "/services", timeout=15, headers={'X-Team-Token':self.team_token})

            if r.status_code != 200:
                logging.error(
                    f'{self.flagid_url} responded with {r.status_code}: Retrying in 5 seconds.')
                time.sleep(5)
                return False

            services = list(r.json().keys())
            flag_ids = {}
            fail = False
            for service in services:
                r = requests.get(self.flagid_url + "/flag_ids?service=" + service, timeout=15, headers={'X-Team-Token':self.team_token})
                if r.status_code != 200:
                    logging.error(
                        f'{self.flagid_url} responded with {r.status_code}: Retrying in 5 seconds.')
                    fail = True
                    break
                flag_ids[service] = r.json()['flag_ids']
            if fail:
                time.sleep(5)
                return False

            dir_path = os.path.dirname(os.path.realpath(__file__))
            with open(f'{dir_path}/flag_ids.json', 'w', encoding='utf-8') as f:
                json.dump(flag_ids, f)
            return True

        except TimeoutError:
            logging.error(
                f'{self.flagid_url} timed out: Retrying in 5 seconds.')
            time.sleep(5)
            return False
