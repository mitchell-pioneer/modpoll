# modpoll2 - A Command-line Tool for Modbus and MQTT

[![pipeline status](https://gitlab.com/helloysd/modpoll/badges/master/pipeline.svg)](https://gitlab.com/helloysd/modpoll/-/commits/master)
[![License](https://img.shields.io/pypi/l/modpoll)](https://gitlab.com/helloysd/modpoll/-/blob/master/LICENSE)
[![Downloads](https://static.pepy.tech/badge/modpoll/week)](https://pepy.tech/project/modpoll)

## Motivation

The initial idea of creating this tool is to help myself debugging new devices during site survey. A site survey usually has limited time and space, working on-site also piles up some pressures. At that time, a portable swiss-knife toolkit is our best friend.

This program can be easily deployed to Raspberry Pi or similar embedded devices, polling data from modbus devices, users can choose to log data locally or publish to a MQTT broker for further debugging.

The MQTT broker can be setup on the same Raspberry Pi or on the cloud. Once data successfully published, users can subscribe to a specific MQTT topic to view the data via a smartphone at your fingertip.

<p align="center">
  <img src="docs/assets/modpoll-usage.png">
</p>

Moreover, you can also run this program continuously on a server as a Modbus-MQTT gateway, i.e. polling from local Modbus devices and forwarding data to a centralized cloud service.

In fact, *modpoll* helps to bridge between the traditional field-bus world and the new IoT world.

> This program is designed to be a standalone tool, it works out-of-the-box on Linux/macOS/Windows.

> If you are looing for a modbus python library, please consider the following great open source projects, [pymodbus](https://github.com/riptideio/pymodbus) or [minimalmodbus](https://github.com/pyhys/minimalmodbus)


## Feature

- Support Modbus RTU/TCP/UDP devices
- Show polling data for local debugging, like a typical modpoll tool
- Publish polling data to MQTT broker for remote debugging, especially on smart phone
- Export polling data to local storage for further investigation
- Provide docker solution for continuous data polling use case


## Installation


This program tested on python 3.8+ 

```bash
pip install modpoll
```

### On Windows

## Quickstart

*modpoll* is a python tool for communicating with Modbus devices, so ideally it makes more sense if you have a real Modbus device on hand for the following test, but it is OK if you don't, we provide a virtual Modbus TCP device deployed at `modsim.topmaker.net:502` for your quick testing purpose.

Let's start exploring *modpoll* with *modsim* device, run the following command to get a first glimpse,

```bash
modpoll \
  --tcp modsim.topmaker.net \
  --config https://raw.githubusercontent.com/gavinying/modpoll/master/examples/modsim.csv
```

<p align="center">
  <img src="docs/assets/screenshot-modpoll.png">
</p>

> the modsim code is also available [here](https://github.com/gavinying/modsim)

### Prepare Modbus configure file

The reason we can magically poll data from the online device *modsim* is because we have already provided the [Modbus configure file](https://raw.githubusercontent.com/gavinying/modpoll/master/examples/modsim.csv) for *modsim* device as following,

The configuration can be either a local file or a remote public URL resource.

> *Refer to the [documentation](https://helloysd.gitlab.io/modpoll/configure.html) site for more details.*


## Basic Usage

- Connect to Modbus TCP device

  ```bash
  modpoll \
    --tcp 192.168.1.10 \
    --config examples/modsim.csv
  ```

- Connect to Modbus RTU device

  ```bash
  modpoll \
    --rtu /dev/ttyUSB0 \
    --rtu-baud 9600 \
    --config contrib/eniwise/scpms6.csv
  ```

- Connect to Modbus TCP device and publish data to MQTT broker

  ```bash
  modpoll \
    --tcp modsim.topmaker.net \
    --tcp-port 5020 \
    --mqtt-host mqtt.eclipseprojects.io \
    --config examples/modsim.csv
  ```

- Connect to Modbus TCP device and export data to local csv file

  ```bash
  modpoll \
    --tcp modsim.topmaker.net \
    --tcp-port 5020 \
    --export data.csv \
    --config examples/modsim.csv
  ```

## Configuation 
Modpoll is configured using a yaml file.  The file has three section:
- device
- poll
- elements

### Device 
This section contains yaml elements for the system as a whole. 

    name: "BcHydro"
    customer: bchydro
    truck: bch1
    versionNumber: "1.0"
    device_id: 1
    osCmd: ""
    enabled: true
    mqttHost: "devmqtt.eboostmobile.com"
    ipAddress: "192.168.2.50"
    modbusTimeout: 3
    modbusPort: 502
    loopDelay: 1  #in seconds
    modbusPrint: False
    deepDebug: False
    deepModbusPrint: True
    onChangeReset: 60
    neverEnd: True

### Poll 
This section is contained in an array inside the Device section. It controls the polling actions of the configuraiton file.

    poll:
      - name: DeepSeaValues
        modRegType: holding_register
        modStartPage: "39424"
        modPageSize: "60"

        loopDelay: 5   #in seconds
        endian: "BE_BE"
        mqttOnChange: False
        mqttQueue: "Pioneer/{CNAME}/{PNAME}/generator"
        mqttSingle: False
        enabled: True

### Elements 
This section is contained in an array inside the Poll section. It controls the individual modbus registers that are read.

    elements:
      - { name: "Engine run time", address: "dse!Engine run time!",                 dtype: "uint32",   unit: "seconds", scale: "{}/3600" }
      - { name: "Generator positive KW hours", address: "dse!Generator positive KW hours!",       dtype: "uint32",   unit: "seconds", scale: "{} * 0.1" }
      - { name: "Generator KVA hours", address: "dse!Generator KVA hours!",       dtype: "uint32",   unit: "seconds", scale: "{} * 0.1" }
      - { name: "Generator KVAr hours", address: "dse!Generator KVAr hours!",       dtype: "uint32",   unit: "seconds", scale: "{} * 0.1" }

### Yaml file details 

#### Device fields 
    name: AppName     
    The name of the system.  This is used as the first part of the subsitutions in the mqtt topic.  

    customer: 'The Customer'
    The customer of the system.  This is used as the second part of the subsitutions in the mqtt topic
  
    truck: bch1 
    The product of the customer.  This is used as the third part of the subsitutions in the mqtt topic

    versionNumber: "1.0"  
    The version number of the app, that will be printed in the title. 
    Optional:  It will default to '1.0' if field is excluded  

    device_id: 1
    The device_id  of the app.  
    Optional:  It will default to 'noDevId' if field is excluded  

    osCmd: ""
    Not used at this time

    enabled: true
    Exclude this device and all poll sections from processing.
    Optional:  It will default to 'True' if field is excluded  

    mqttHost: "devmqtt.eboostmobile.com"
    The URI of the MQTT Server 
    Manditory field

    ipAddress: "192.168.2.50"
    The ip address of the modbus controler to be monitored
    Manditory field 

    modbusTimeout: 3
    How many modbus timeouts can be accepted. This is simply passed to the pymodpoll library
    Optional:  It will default to '5' if field is excluded

    modbusPort: 502
    The modbus IP port used to contact this server. 
    Optional:  It will default to '502' if field is excluded

    loopDelay: 1  #in seconds
    The number of seconds that the the 'Device' section will force the polling loop to delay
    Optional:  It will default to '5' if field is excluded

    modbusPrint: False
    If enabled each poll section below will include a table in the logfile showing the value of each register 
    Optional:  It will default to 'False' if field is excluded

    deepDebug: False
    If enabled detailed logging about actions contained within the processing of this section. 
    This includes the modbus data conversion  
    Optional:  It will default to 'False' if field is excluded

    deepModbusPrint: True
    If enabled more detailed logging about actions contained within the processing of this section. 
    This includes the modbus data conversion  
    Optional:  It will default to 'False' if field is excluded

    onChangeReset: 60
    When MQTT publish is run, it will determine if this modbus register is different from the last time the register was read.
    If a field does not change for a long time, it might appear that the field is never processed.
    This field controls how often this table of last values is cleared out. 
    Its in sections 
    Optional:  It will default to '0' if field is excluded

    neverEnd: True
    If errors are encountered during the procssing of this configuration, error might be enountered.
    The value of this field determins if the program exists or just prints the error and reinitialzied 
    the system and trys again.

#### Poll fields
    poll:
      - name: DeepSeaValues
        modRegType: holding_register
        modStartPage: "39424"
        modPageSize: "60"

        loopDelay: 5   #in seconds
        endian: "BE_BE"
        mqttOnChange: False
        mqttQueue: "Pioneer/{CNAME}/{PNAME}/generator"
        mqttSingle: False
        enabled: True


#### Element fields 

        elements:
          - { name: "EmergencyStop",  address: "39424 + 1",   dtype: "u16n3",   unit: "Flag",   <<: *mapFlags }
          - { name: "LowOil",         address: "39424 + 1" ,  dtype: "u16n2",   unit: "Flag",   <<: *mapFlags }

### Generator specific fields
        modStartPage: dsp!Accumulated Instrumentation!
        elements:
          - { name: "Engine run time", address: "dse!Engine run time!",                 dtype: "uint32",   unit: "seconds", scale: "{}/3600" }
          - { name: "Generator positive KW hours", address: "dse!Generator positive KW hours!",       dtype: "uint32",   unit: "seconds", scale: "{} * 0.1" }

## Credits

The implementation of this project is heavily inspired by the following two projects:
- https://github.com/owagner/modbus2mqtt (MIT license)
- https://github.com/mbs38/spicierModbus2mqtt (MIT license)

Thanks to Max Brueggemann and Oliver Wagner for their great work.


## License

MIT © [helloysd](helloysd@gmail.com)
