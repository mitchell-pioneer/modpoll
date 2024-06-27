#!/usr/bin/bash
cd /home/mbalsam/modpoll
source venv/bin/activate
python3 main.py --tcp 10.1.1.88 -f tristar.csv --mqtt-host devmqtt.eboostmobile.com --mqtt-single 

