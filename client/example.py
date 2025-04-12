#!/usr/bin/env python3
import os
import sys
import secrets
sys.path.insert(1, '../imports/')
sys.path.insert(1, 'imports/')

import utils
import requests
import json
from bs4 import BeautifulSoup
from pwn import *

# Use this function to print stuff to client
def log(message):
    print(message, flush=True)

IP_ADDRESS = sys.argv[1]
dir_path = os.path.dirname(os.path.realpath(__file__)) + '/../'

def generate_secure_random_string(length=10):
    characters = string.ascii_letters + string.digits
    secure_random_string = ''.join(secrets.choice(characters) for _ in range(length))
    return secure_random_string

# Adjust if needed
SERVICE = "TEST"
PORT = 1234
TEAM_ID = IP_ADDRESS.split(".")[-2]
TARGET_URL = f'http://{IP_ADDRESS}:{PORT}'

with open(dir_path + 'flag_ids.json', 'r', encoding='utf-8') as f:
    flag_ids = json.loads(f.read())
    #log(flag_ids)

myfFlagIds = flag_ids[SERVICE][IP_ADDRESS]

flags = []

for i in range(myfFlagIds):
    try:
        #put your code here
    except Exception as e:
        log(e)

print(flags)