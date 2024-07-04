#!/usr/bin/bash
cd /opt/modpoll
source venv/bin/activate
python3 main.py \
 --tcp 10.1.1.88 \
  -f modpoll-settings.csv \
  --mqtt-host devmqtt.eboostmobile.com \
  --mqtt-single \
  --mqtt-onchange \
  --delay 5 \
  --daemon \
  --mqtt-topic "pioneer/modbus/vinfast/vinfast1/" 



