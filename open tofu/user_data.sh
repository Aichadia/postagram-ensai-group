#!/bin/bash
echo "userdata-start"        
set -e
apt update
apt install -y python3-pip python3.12-venv
git clone ${git_repo} projet
cd projet/webservice
python3 -m venv venv
source venv/bin/activate
rm .env
echo 'BUCKET=${bucket}' >> .env
echo 'DYNAMO_TABLE=${dynamo_table}' >> .env
pip3 install -r requirements.txt
nohup venv/bin/python app.py > /var/log/postagram.log 2>&1 &
echo "userdata-end