#!/usr/bin/bash
cd ~/modpoll
source venv/bin/activate
python3 main.py\
 --tcp 10.1.1.88\
  -f tristar-test.csv\
  --mqtt-host devmqtt.eboostmobile.com\
  --mqtt-single\
  --mqtt-onchange\
  --mqtt-topic "pioneer/modbus/customer/product/"
