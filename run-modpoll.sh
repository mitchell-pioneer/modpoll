#!/usr/bin/bash
cd /opt/modpoll
source venv/bin/activate
. /home/pi/.eboostrc
echo "HOST=$EBOOST_MODPOLL_HOST"
echo "CFG=$EBOOST_MODPOLL_FILE"
echo "MQTTHOST=$EBOOST_PUBLIC_MQTT_HOST"
echo "MQTTTOPIC=$EBOOST_MODPOLL_TOPIC_ROOT\\$EBOOST_CUSTOMER\\$EBOOST_PRODUCT"
python3 main.py \
  --tcp $EBOOST_MODPOLL_HOST \
   -f $EBOOST_MODPOLL_FILE \
   --mqtt-host $EBOOST_PUBLIC_MQTT_HOST \
   --mqtt-single \
   --mqtt-onchange \
   --delay 5 \
   --daemon \
   --mqtt-topic /$EBOOST_MODPOLL_TOPIC_ROOT/$EBOOST_CUSTOMER/$EBOOST_PRODUCT/



