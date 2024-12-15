import datetime,json,logging,re,signal,sys,threading,math,csv,time,traceback,requests,os
from typing import  List
from prettytable import PrettyTable
from pymodbus import ModbusException
from pymodbus.client import ModbusSerialClient, ModbusTcpClient, ModbusUdpClient
from pymodbus.constants import Endian
from pymodbus.payload import BinaryPayloadDecoder

from deepsea.DeepSeaModBusCalculator import DeepSeaModBusCalculator
from modpoll.Device import Device
from modpoll.CsvParser import CsvParser
from modpoll.Element import Element
from modpoll.MqttControl import MqttControl
from modpoll.Poller import Poller
from modpoll.YamlParser import YamlParser

from pymodbus import pymodbus_apply_logging_config

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)


class ModbusControl:
    def __init__(self,args,yparser : YamlParser,mcontrol : MqttControl):
        self.cmdLineArgs = args
        self.args = args
        self.modbusConnection = {}
        self.deepdebug = False
        self.deviceList : List[Device] = yparser.deviceList
        self.mqttControl : MqttControl = mcontrol
        self.log = log
        self.modbusDebug = self.deviceList[0].modbusDebug
        self.modbusPrint = self.deviceList[0].modbusPrint
        if(self.modbusDebug):
            # enable internal modbus logging
            pymodbus_apply_logging_config(logging.DEBUG)

    def modbus_setup(self,deviceId : int ):

        # IP: pass ipadress and device name
        if self.args.rtu:
            self.setupSerialConnection(deviceId)
        elif self.args.tcp:
            self.setupTcpConnection(deviceId)
        elif self.args.udp:
            self.setupUdpConnection(deviceId)
        else:
            self.log.error("You must specify a modbus access method, either --rtu, --tcp or --udp" )
            return False

        assert self.modbusConnection, "No modbus connection was created"
        return True

    def setupUdpConnection(self,deviceId: int):
        ipAddress = self.deviceList[deviceId].ipAddress
        port  = self.deviceList[deviceId].modbusPort
        tout = self.deviceList[deviceId].modbusTimeout

        if self.args.framer == "default":
            self.modbusConnection = ModbusUdpClient(host=ipAddress, port=port, timeout=tout)
        else:
            self.modbusConnection = ModbusUdpClient(host=ipAddress, port=port, timeout=tout, framer=self.args.framer)

    def setupTcpConnection(self,deviceId : int):
        ipAddress = self.deviceList[deviceId].ipAddress
        port  = self.deviceList[deviceId].modbusPort
        tout = self.deviceList[deviceId].modbusTimeout

        if self.args.framer == "default":
            self.modbusConnection = ModbusTcpClient(host=ipAddress, port=port, timeout=tout)
        else:
            self.modbusConnection = ModbusTcpClient(host=ipAddress, port=port, framer=self.args.framer, timeout=tout )


    def setupSerialConnection(self,deviceId :int ):
        if self.args.rtu_parity == "odd":
            parity = "O"
        elif self.args.rtu_parity == "even":
            parity = "E"
        else:
            parity = "N"
        if self.args.framer == "default":
            self.modbusConnection = ModbusSerialClient(
                self.args.rtu,
                baudrate=int(self.args.rtu_baud),
                bytesize=8,
                parity=parity,
                stopbits=1,
                timeout=self.args.timeout,
            )
        else:
            self.modbusConnection = ModbusSerialClient(
                self.args.rtu,
                baudrate=int(self.args.rtu_baud),
                bytesize=8,
                parity=parity,
                stopbits=1,
                framer=self.args.framer,
                timeout=self.args.timeout,
            )

    def modbus_polling_loop(self) -> bool:
        self.modbus_setup(0)
        self.modbusConnection.connect()

        connected = None
        for dev in self.deviceList:
            if(dev.enabled):
                if(dev.deepDebug): self.log.debug(f"Waiting to start {dev.name} ...")
                if(dev.deepDebug): self.log.debug(f"Looping device {dev.name} ...")
                for p in dev.pollList:
                    if p.enabled:
                        if(dev.deepDebug): self.log.debug(f"Looping poller {p.name} ...")
                        connected = True
                        if(p.poll(self.modbusConnection) == False):
                            connected = False
                            break  # if error no sense in trying other pollers

                        if self.modbusPrint: self.modbus_print(p)
                        time.sleep(p.loopDelay)
                time.sleep(dev.deviceLoopDelay)
        self.modbusConnection.close()
        return connected


    def modbus_publish(self):
        for dev  in self.deviceList:
            if not dev.pollSuccess:
                if(dev.deepDebug): self.log.debug(f"Skip publishing for disconnected device: {dev.name}")
                continue
            if(self.deepdebug):  self.log.debug(f"Start publishing data for device: {dev.name} ...")
            for pol in dev.pollList:
                if(pol.enabled == False):
                    if self.deepdebug: log.debug(f"Polling for {pol.name} is disabled")
                    continue


                on_change = pol.mqttOnChange and pol.mqttQueue is not None
                #for ele in dev.refList.values():
                for ele in  pol.readableElements:
                    if self.deepdebug: log.debug(f"name={ele.name} value={ele.val}")
                    try:
                        if (ele.val == None):
                            continue
                        match ele.dtype.lower():
                            case "b1-16" | "b2-16" | "b3-16" | "b4-16" | "b5-16" | "b6-16" | "b7-16" | "b8-16" | "b9-16" | "b10-16" | "b11-16" | "b12-16" | "b13-16" | "b14-16" | "b15-16" | "b16-16":
                                if on_change:
                                    if (isinstance(ele.val, int)):
                                        if ele.val == ele.last_val:
                                            continue
                                else:
                                    if ele.val == ele.last_val:
                                        continue
                                    continue

                            case "float16" | "float32" | "uint16" | "int16" | "uint32" | "int32":
                                if on_change:
                                    if (isinstance(ele.val, str)):
                                        if ele.val == ele.last_val:
                                            continue
                                    if (isinstance(ele.val, int)):
                                        if not (ele.lrange == None or  ele.hrange == None):
                                            high = int(ele.last_val + ele.hrange)
                                            low = int(ele.last_val - ele.lrange)
                                            if not (ele.val >= high or ele.val <= low):
                                                # Within bounds.. Do nothing
                                                continue
                                            else:
                                                # Change detected
                                                log.info(f"Change Detected:{ele.name} val={ele.val} last={ele.last_val} outside of {high}:{low}")
                                        else:
                                            # onchange is enabled but no range specified.  Do normal if == detection
                                            if  ele.val == ele.last_val:
                                                continue

                                    if (isinstance(ele.val,float)):
                                        if not (ele.lrange == None or  ele.hrange == None):
                                            if(ele.last_val is not None):
                                                high = round(ele.last_val * (1+ele.hrange),2)
                                                low = round(ele.last_val * (1-ele.lrange),2)
                                                if  not (ele.val > high or ele.val < low):
                                                    #log.debug(f"Within Limits:{ele.name} val={ele.val} last={ele.last_val} within limits {high}:{low}")
                                                    continue
                                                else:
                                                    log.info(f"Change Detected:{ele.name} val={ele.val} last={ele.last_val} outside of {high}:{low}")
                                        else:
                                            # onchange is enabled but no range specified.  Do normal if == detection
                                            if  ele.val == ele.last_val:
                                                    continue
                            case "u16n3" | "u16n2" | "u16n1" | "u16n0":
                                if not (ele.lrange == None or ele.hrange == None):
                                    high = round(ele.last_val * (1 + ele.hrange),2)
                                    low = round(ele.last_val * (1 - ele.lrange),2)
                                    if not (ele.val > high or ele.val < low):
                                        # log.debug(f"Within Limits:{ele.name} val={ele.val} last={ele.last_val} within limits {high}:{low}")
                                        continue
                                    else:
                                        log.info(
                                            f"Change Detected:{ele.name} val={ele.val} last={ele.last_val} outside of {high}:{low}")
                                else:
                                    # onchange is enabled but no range specified.  Do normal if == detection
                                    if ele.val == ele.last_val:
                                        continue
                            case _:
                                if on_change and ele.val == ele.last_val:
                                    continue

                        ele.last_val = ele.val      # with on_change: only update last value when reporting change
                        if(pol.mqttTopicSingle):
                            # all messages value in a single topic
                            topic = self.mqtt_topic_format(pol.mqttQueue)
                            msg = f"{ele.name}={ele.val}"
                        else:
                            # each messages has its own key
                            topic = self.mqtt_topic_format(pol.mqttQueue)+"/"+ele.name
                            msg = ele.val

                        self.mqttControl.mqttc_publish(topic, msg)

                        self.log.debug(f"Mqtt Change {ele.name} New={ele.val} Old={ele.last_val} ")
                    except Exception as e:
                        self.log.debug(f"Exception processing [{ele.name}] Exception=[{e}] ")
            if(dev.deepDebug): self.log.debug(f"Completed Publishing data for device: {dev.name} ...")

    def mqtt_topic_format(self,fmtstr ) -> str:
        # if there are {} in the topic,  Pull values from system environment
        if(fmtstr.find("{}")):
            try:
                ret = f"{fmtstr.format(**os.environ)}"
            except Exception as e:
                raise AssertionError(f"Invalid mqtt format string: Missing Environment Var {e}")
        else:
            # just us the topic without subsitutions
            ret = fmtstr
        return ret

    def modbus_close(self):
        if self.modbusConnection:
            self.modbusConnection.close()


    def modbus_write_coil(self,device_name, address: int, value):
        if not self.modbusConnection:
            return False
        self.modbusConnection.connect()
        time.sleep(self.cmdLineArgs.delay)
        self.log.debug(f"Master connected. Delay of {self.cmdLineArgs.delay} seconds.")
        for d in self.deviceList:
            if d.name == device_name:
                self.log.info(f"Writing coil(s): device={device_name}, address={address}, value={value}")
                if isinstance(value, int):
                    result = self.modbusConnection.write_coil(address, value, slave=d.devid)
                elif isinstance(value, list):
                    result = self.modbusConnection.write_coils(address, value, slave=d.devid)
                return result.function_code < 0x80
        self.modbusConnection.close()
        return False

    def modbus_write_register(self,device_name, address: int, value):
        if not self.modbusConnection:
            return False
        self.modbusConnection.connect()
        time.sleep(self.cmdLineArgs.delay)
        self.log.debug(f"Master connected. Delay of {self.cmdLineArgs.delay} seconds.")
        for d in self.deviceList:
            if d.name == device_name:
                self.log.info(
                    f"Writing register(s): device={device_name}, address={address}, value={value}"
                )
                if isinstance(value, int):
                    result = self.modbusConnection.write_register(address, value, slave=d.devid)
                elif isinstance(value, list):
                    result = self.modbusConnection.write_registers(address, value, slave=d.devid)
                return result.function_code < 0x80
        self.modbusConnection.close()
        return False

    def modbus_print(self,pol):
        # https: // ptable.readthedocs.io / en / latest / tutorial.html  # displaying-your-table-in-ascii-form
        table = PrettyTable(["name", "address", "value","last value","scale","unit"])
        for ref in pol.readableElements:
            if isinstance(ref.val, float):
                value = f"{ref.val:g}"
            else:
                value = ref.val
            row = [ref.name, ref.address, value,ref.last_val,ref.scale,ref.unit]
            table.add_row(row)
        self.log.debug("\n"+table.get_string())
