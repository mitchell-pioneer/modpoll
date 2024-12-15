import sys

from pymodbus import ModbusException
from pymodbus.constants import Endian
import logging

from pymodbus.exceptions import ConnectionException

from modpoll.Element import Element
from modpoll.IndexableBinaryPayloadDecoder import IndexableBinaryPayloadDecoder,ModReadSigned,ModReadLength
log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)

class BitTools:
    # https://realpython.com/python-bitwise-operators/#getting-a-bit
    @classmethod
    def get_bit(self, value, bit_index):
        return value & (1 << bit_index)
    @classmethod
    def get_bit_bool(self, value, bit_index) -> bool:
        return bool(value & (1 << bit_index))

    @classmethod
    def get_normalized_bit(self,value, bit_index):
        return (value >> bit_index) & 1
    @classmethod
    def clear_bit(self,value, bit_index):
        return value & ~(1 << bit_index)
    @classmethod
    def clear_bit(self,value, bit_index):
        return value & ~(1 << bit_index)
    @classmethod
    def toggle_bit(value, bit_index):
        return value ^ (1 << bit_index)

class Poller:
    def __init__(self, device,pollTree,args,function_code, iBaseAddress, iModPageSize):
        assert device   ,"No valid device was provided"
        assert args     ,"No valid args was provided"
        assert pollTree ,"No pollTree args was provided"

        self.device = device
        self.args = args
        self.pollTree = pollTree
        self.fc = function_code

        self.name : str = pollTree.get('name','defaultName')
        self.modRegType : str = pollTree.get('modRegType').lower()
        self.modStartPage = pollTree.get('modStartPage', 0)
        self.modPageSize = int(pollTree.get('modPageSize', 0))
        #assert self.modPageSize > 125, "modPageSize must be 125bytes or smaller "
        self.loopDelay : int = pollTree.get('loopDelay',5)
        self.endian : str = pollTree.get('endian', 'BE_BE')
        self.customer : str = pollTree.get('customer', 'customer')
        self.truck : str = pollTree.get('truck', 'truck')
        self.mqttQueue : str = pollTree.get('mqttQueue',None)
        self.mqttTopicSingle : bool = pollTree.get('mqttTopicSingle',False)
        self.mqttOnChange : bool = pollTree.get('mqttOnChange',False)
        self.enabled : bool = pollTree.get('enabled', False)
        self.iBaseAddress= iBaseAddress
        self.iModPageSize = iModPageSize
        self.args = args
        self.fc = function_code
        self.endian = self.endian.lower()
        self.readableElements : list[Element] = []
        self.failcounter = 0
        self.master = None
        self.deepdebug = device.deepDebug
        self.log = log
        if(self.deepdebug): log.info(f"Adding new Poller {self.name}")

    def fromIntToBinary(self, rr: int):
        return format(rr, '#016b')

    def applyValueMap(self,element,index:int):
        ret = index
        if (element.valueMap is not [] and len(element.valueMap) > 0):
            if(index <= len(element.valueMap)):
                ret = element.valueMap[index]
        return ret
    def poll(self, m) -> bool:
        self.master = m
        baseAddress :str

        try:
            data, result = self.readModbusRegisters()
            if not data:
                self.update_statistics(False)
                self.log.error(f"ErrorReading: device:{self.device.name}, fc:{self.fc}, startAddress:{self.modStartPage} Size:{self.modPageSize}")
                self.log.debug(result)
                return False

            decoder = self.loadCorrectModbusDecoder(data)
            for element in self.readableElements:
                baseAddress = element.address
                thisAddress = (baseAddress - self.iBaseAddress)
                match element.dtype.lower():
                    case "uint16":
                        rr = decoder.decodeIndexed(thisAddress, ModReadLength.BITS16, ModReadSigned.Unsigned)
                        vv = self.applyValueMap(element,rr)
                        element.scaleValue(vv)
                        if(self.deepdebug): self.log.debug(f"decode-uint16 [{element.name}] [{element.address + thisAddress}] raw=[{rr}] v=[{vv}]]")

                    case "int16":
                        rr = decoder.decodeIndexed(thisAddress, ModReadLength.BITS16, ModReadSigned.Signed)
                        element.scaleValue(rr)
                        if(self.deepdebug): self.log.debug(f"decode-int16 [{element.name}] [{element.address + thisAddress}] raw=[{rr}] ")
                    case "uint32":
                        rr = decoder.decodeIndexed(thisAddress, ModReadLength.BITS32, ModReadSigned.Unsigned)
                        if(rr == 4294967295):
                            # if returned as max - just return NA
                            rr = "NA"
                        element.scaleValue(rr)
                        if(self.deepdebug): self.log.debug(f"decode-uint32 [{element.name}] [{element.address + thisAddress}] raw=[{rr}] ")
                    case "int32":
                        rr = decoder.decodeIndexed(thisAddress, ModReadLength.BITS32, ModReadSigned.Signed)
                        if(rr == -sys.maxsize - 1):
                            # if returned as max - just return NA
                            rr = "NA"
                        element.scaleValue(rr)
                        if(self.deepdebug): self.log.debug(f"decode-int32 [{element.name}] [{element.address + thisAddress}] raw=[{rr}] ")

                    case "b1-16"  | "b2-16" | "b3-16" | "b4-16" | "b5-16" | "b6-16" | "b7-16" | "b8-16" | "b9-16" | "b10-16" | "b11-16" | "b12-16" | "b13-16" | "b14-16" | "b15-16"  | "b16-16":
                        rr = decoder.decodeIndexed(thisAddress, ModReadLength.BITS16, ModReadSigned.Unsigned)
                        parts = element.dtype.lower()[1:].split("-")
                        i = int(parts[0]) -1
                        vv = BitTools.get_bit_bool(rr,i)
                        if(self.deepdebug): self.log.debug(f"decode-bx-16 [{element.name}] [{element.address + thisAddress}] bx-16=[{vv}] raw=[{rr:016b}] val=[{vv:04b}]")
                        element.scaleValue(vv)
                    case "u16n0":
                        rr = decoder.decodeIndexed(thisAddress, ModReadLength.BITS16, ModReadSigned.Unsigned)
                        vv = (rr & 0x000F)
                        if(self.deepdebug): self.log.debug(f"decode-nibble0 [{element.name}] [{element.address + thisAddress}] rawb10=[{rr}] raw=[{rr:016b}] val=[{vv:04b}]")
                        if (element.valueMap is not []):
                            vv = element.valueMap[vv]
                        element.scaleValue(vv)
                    case "u16n1":
                        rr = decoder.decodeIndexed(thisAddress, ModReadLength.BITS16, ModReadSigned.Unsigned)
                        vv = (rr & 0x00F0) >> 4
                        if self.deepdebug: self.log.debug(f"decode-nibble1 [{element.name}] [{element.address + thisAddress}] rawb10=[{rr}] raw=[{rr:016b}] val=[{vv:04b}]")
                        if (element.valueMap is not []):
                            vv = element.valueMap[vv]
                        element.scaleValue(vv)
                    case "u16n2":
                        rr = decoder.decodeIndexed(thisAddress, ModReadLength.BITS16, ModReadSigned.Unsigned)
                        vv = (rr & 0x0F00) >> 8
                        if self.deepdebug: self.log.debug(
                            f"decode-nibble2 [{element.name}] [{element.address + thisAddress}] rawb10=[{rr}] raw=[{rr:016b}] val=[{vv:04b}]")
                        if (element.valueMap is not []):
                            vv = element.valueMap[vv]
                        element.scaleValue(vv)
                    case "u16n3":
                        rr = decoder.decodeIndexed(thisAddress, ModReadLength.BITS16, ModReadSigned.Unsigned)
                        vv = (rr & 0xF000) >> 12
                        if self.deepdebug: self.log.debug(
                            f"decode-nibble3 [{element.name}] [{element.address + thisAddress}] rawb10=[{rr}] raw=[{rr:016b}] val=[{vv:04b}]")
                        if (element.valueMap is not []):
                            vv = element.valueMap[vv]
                        element.scaleValue(vv)
                    case "uint64":
                        rr = decoder.decodeIndexed(thisAddress, ModReadLength.BITS64, ModReadSigned.Unsigned)
                        element.scaleValue(rr)
                        if(self.deepdebug): self.log.debug(f"decode-uint64 [{element.name}] [{element.address + thisAddress}] rawb=[{rr}]")

                    case "int64":
                        rr = decoder.decodeIndexed(thisAddress, ModReadLength.BITS64, ModReadSigned.Signed)
                        element.scaleValue(rr)
                        if(self.deepdebug): self.log.debug(f"decode-int64 [{element.name}] [{element.address + thisAddress}] rawb=[{rr}]")

                    case "float16":
                        rr = decoder.decodeIndexed(thisAddress, ModReadLength.BITS16, ModReadSigned.Float)
                        element.scaleValue(rr)
                        if(self.deepdebug): self.log.debug(f"decode-float16 [{element.name}] [{element.address + thisAddress}] raw=[{rr}]")

                    case "float32":
                        rr  =decoder.decodeIndexed(thisAddress, ModReadLength.BITS32, ModReadSigned.Float)
                        element.scaleValue(rr)
                        if(self.deepdebug): self.log.debug(f"decode-float32 [{element.name}] [{element.address + thisAddress}] raw=[{rr}]")
                    case "float64":
                        rr = decoder.decodeIndexed(thisAddress, ModReadLength.BITS64, ModReadSigned.Float)
                        element.scaleValue(rr)
                        if(self.deepdebug): self.log.debug(f"decode-float64 [{element.name}] [{element.address + thisAddress}] raw=[{rr}]")
                    case "bool8":
                        rr = decoder.decode_bits()
                        element.scaleValue(rr)
                        if(self.deepdebug): self.log.debug(f"decode-bool8 [{element.name}] [{element.address + thisAddress}] raw=[{rr}]")
                    case "bool16":
                        rr = decoder.decode_bits() + decoder.decode_bits()
                        element.scaleValue(rr)
                        if(self.deepdebug): self.log.debug(f"decode-bool16 [{element.address + thisAddress}] raw=[{rr}]")
                    case _:
                        if element.dtype.startswith("string"):
                            element.scaleValue(decoder.decode_string())
                        else:
                            self.log.error("not found")

            # update the diff
#            self.device.saveLastValueForDiffCalc(element)  # done in modbus control
            self.update_statistics(True)

            if(element.condition != ""):
                self.device.execCondition.processEvent(element.condition,rr,element.argument)

            return True
        except ConnectionException as ex:
            self.log.debug(f"ConnectionException:{ex}")
            return False
        except ModbusException as ex:
            self.log.debug(f"ModbusException:{ex}")
            self.update_statistics(False)
            # self.log.warning(
            #     f"Reading device:{self.device.name}, FuncCode:{self.fc}, "
            #     f"Start_address:{self.baseAddress}, Size:{self.size}... FAILED"
            # )
            self.log.debug(f"Disconnected from modbus device IP={element.address} Offset={self.iBaseAddress}")
        return False

    def readModbusRegisters(self):
        data = None
        if(self.deepdebug): self.log.debug(f"ModbusRead:Starting address={self.modStartPage}")
        # parser the register type
        if self.fc == 1:
            result = self.master.read_coils(self.iBaseAddress, self.iModPageSize, slave=self.device.devid)
            if not result.isError():
                data = result.bits
        elif self.fc == 2:
            result = self.master.read_discrete_inputs(self.iBaseAddress, self.iModPageSize, slave=self.device.devid)
            if not result.isError():
                data = result.bits
        elif self.fc == 3:
            result = self.master.read_holding_registers(self.iBaseAddress, self.iModPageSize, slave=self.device.devId)
            if not result.isError():
                data = result.registers
            else:
                raise AssertionError(f"Read Modbus failed fc={self.fc} ip={self.iBaseAddress} mp={self.iModPageSize}")

        elif self.fc == 4:
            result = self.master.read_input_registers(self.iBaseAddress, self.iModPageSize, slave=self.device.devid)
            if not result.isError():
                data = result.registers
        assert data != None,f"No data set in readModbusRegister fc={self.fc} base={self.iBaseAddress}"
        return data, result

    def loadCorrectModbusDecoder(self, data):
        # parse the byte format
        if "BE_BE" == self.endian.upper():
            if self.fc == 1 or self.fc == 2:
                decoder = IndexableBinaryPayloadDecoder.fromCoils(data, byteorder=Endian.BIG)
            else:
                decoder = IndexableBinaryPayloadDecoder.fromRegisters(data, byteorder=Endian.BIG, wordorder=Endian.BIG)
        elif "LE_BE" == self.endian.upper():
            if self.fc == 1 or self.fc == 2:
                decoder = IndexableBinaryPayloadDecoder.fromCoils(data, byteorder=Endian.LITTLE)
            else:
                decoder = IndexableBinaryPayloadDecoder.fromRegisters(data, byteorder=Endian.LITTLE,wordorder=Endian.BIG)
        elif "LE_LE" == self.endian.upper():
            if self.fc == 1 or self.fc == 2:
                decoder = IndexableBinaryPayloadDecoder.fromCoils(data, byteorder=Endian.LITTLE)
            else:
                decoder = IndexableBinaryPayloadDecoder.fromRegisters(data, byteorder=Endian.LITTLE,wordorder=Endian.LITTLE)
        else:
            if self.fc == 1 or self.fc == 2:
                decoder = IndexableBinaryPayloadDecoder.fromCoils(data, byteorder=Endian.BIG)
            else:
                decoder = IndexableBinaryPayloadDecoder.fromRegisters(data, byteorder=Endian.BIG,wordorder=Endian.LITTLE)
        return decoder

    def add_readable_reference(self, ref):
        if ref not in self.readableElements:
            self.readableElements.append(ref)

    def update_statistics(self, success):
        self.device.pollCount += 1
        if success:
            self.failcounter = 0
            self.device.pollSuccess = True
        else:
            self.failcounter += 1
            self.device.errorCount += 1
            self.device.pollSuccess = False
            if self.args.autoremove and self.failcounter >= 3:
                self.enabled = True
                self.log.info(
                    f"Poller {self.name} disabled (functioncode: {self.fc}, "
                    f"start_address: {self.start_address}, size: {self.size})."

                )



