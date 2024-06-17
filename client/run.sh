#!/bin/bash

# Edit
SERVER="localhost"
PORT=5555
USERNAME="CC_TorVergata"
TOKEN="your_token"
TYPE="ccit"
THREADS=12

#echo "REMEMBER chmod +x ./exploit.py"

python3 client.py -s http://$SERVER:$PORT -u $USERNAME --type $TYPE -t $TOKEN -d ./exploits/ -n $THREADS -v
