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
        self.deepModbusPrint = self.deviceList[0].deepModbusPrint

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

                        if self.deepModbusPrint: self.modbus_print(p)
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
                    if self.deepdebug: log.debug(f"Polling for {ref.name} is disabled")
                    continue

                on_change = pol.mqttOnChange
                for ref in dev.refList.values():
                    if self.deepdebug: log.debug(f"name={ref.name} value={ref.val}")
                    match ref.dtype.lower():
                        case "float16" | "float32" | "uint16" | "int16" | "uint32" | "int32":
                            badval = not ref.last_val is None
                            if on_change and math.isnan(ref.val):
                                continue
                            if(isinstance(ref.last_val,str)):
                                # we can do range calcs on strings
                                # but how did a string get in here?
                                continue
                            if badval and on_change and ref.last_val > 0.0 and ref.lrange > 0.0:
                                high = ref.last_val * (1+ref.hrange)
                                low = ref.last_val * (-1-ref.lrange)
                                if on_change and not (ref.val > high or ref.val < low):
                                    log.debug(f"Within Limits:{ref.name} val={ref.val} last={ref.last_val} within limits {high}:{low}")
                                else:
                                    log.info(f"Change Detected:{ref.name} val={ref.val} last={ref.last_val} outside of {high}:{low}")
                            else:
                                if on_change and ref.val == ref.last_val:
                                    continue
                        case "u16n3" | "u16n2" | "u16n1" | "u16n0":
                            if on_change and ref.val == ref.last_val:
                                continue
                        case _:
                            if on_change and ref.val == ref.last_val:
                                continue

                    if(pol.mqttTopicSingle):
                        # all messages value in a single topic
                        topic = self.mqtt_topic_format(pol.mqttQueue)
                        msg = f"{ref.name}={ref.val}"
                    else:
                        # each messages has its own key
                        topic = self.mqtt_topic_format(pol.mqttQueue)+"/"+ref.name
                        msg = ref.val
                    self.mqttControl.mqttc_publish(topic, msg)

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
        table = PrettyTable(["name", "unit", "address", "value"])
        for ref in pol.readableElements:
            if isinstance(ref.val, float):
                value = f"{ref.val:g}"
            else:
                value = ref.val
            row = [ref.name, ref.unit, ref.address, value]
            table.add_row(row)
        self.log.debug("\n"+table.get_string())
