import logging,traceback,yaml,requests

from typing import List, Dict, Union
from deepsea.DeepSeaModBusCalculator import DeepSeaModBusCalculator
from modpoll.Device import Device
from modpoll.Element import Element
from modpoll.Poller import Poller

# # Define type hints for better code clarity
# AddressReference = Dict[str, Union[str, int, float]]
# PollReference = Dict[str, Union[str, int, List[AddressReference]]]
# DeviceConfiguration = Dict[str, Union[str, int, List[PollReference]]]

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)

class YamlParser:
    def __init__(self, args):
        self.args = args
        self.log = log
        self.deviceList : List[Device] = []
        self.configFilePath  = self.args.config
        self.deepsea = DeepSeaModBusCalculator()
        self.yamlText = ""
        self.yamlParseTree = self.load_yaml(self.configFilePath)
        newDevice = self.parseDevice(self.yamlParseTree)
        assert newDevice,"YamlParser newDevice was not created"
        self.deviceList.append(newDevice)

    def load_yaml(self, file):
        if file.startswith(("http", "https")):
            with requests.Session() as s:
                response = s.get(file)
                self.yamlText = response.content.decode("utf-8")
                yamlParseTree = yaml.safe_load(self.yamlText, Loader=yaml.FullLoader)
        else:
            with open(file, "r") as self.yamlText:
                yamlParseTree  = yaml.load(self.yamlText, Loader=yaml.FullLoader)
        return yamlParseTree


    def parseDevice(self, yamlParseTree):
        dList = []
        current_poller = []
        pageName = ""
        try:
            deviceTree = self.yamlParseTree.get("device")
            assert deviceTree, "Device data is missing in YAML configuration"

            newDevice = Device(deviceTree)
            assert newDevice, "Device object was not created"

            dList.append(newDevice)

            poll_entries = deviceTree.get("poll", [])
            assert poll_entries, "poll_entries data is missing in YAML configuration"

            for poll in poll_entries:
                newPoler = self.parse_poll(newDevice,poll)

                if(newPoler is None):
                    nn = poll.get("name","")
                    self.log.debug(f"Skipping Poller {nn}")
                    continue
                newDevice.pollList.append(newPoler)

            return newDevice
        except Exception as e:
            error_message = traceback.format_exc()
            self.log.debug(f"Failed to parse YAML Error=ParseConfig:parse={e}:{error_message}")
            exit(1)

    def parse_poll(self, cDevice,pollTree):

        try:
            assert cDevice,"No device to add poller."
            assert pollTree, "No pollTree to parse."

            if(pollTree.get('enabled') == False):
                return None
            name = pollTree.get('name')
            modRegType = pollTree.get('modRegType').lower()

            modStartPage = pollTree.get('modStartPage','0')
            modPageSize = pollTree.get('modPageSize','0')


            if(modStartPage.startswith('dsp')):
                try:
                    ptype = modStartPage.split('!')[1]
                    iBaseAddress = self.deepsea.getPageStartAddress(ptype)
                    iModPageSize = int(modPageSize)
                except Exception as e:
                    raise ValueError(f"Deepsea modStartPage or modPageSize is not properly formatted {modStartPage} ps={modPageSize}")
            else:
                    try:
                        iBaseAddress = int(eval(modStartPage))
                        iModPageSize = int(eval(modPageSize))
                    except Exception as e:
                        raise ValueError(f"Normal modStartPage or modPageSize is not properly formatted {modStartPage} ps={modPageSize}")

            if modRegType == "coil":
                function_code = 1
                if iModPageSize > 2000:
                    raise Exception("Too many coils (max. 2000). Ignoring poller.")
            elif modRegType == "discrete_input":
                function_code = 2
                if iModPageSize > 2000:
                    raise Exception("Too many discrete inputs (max. 2000). Ignoring poller.")
            elif modRegType == "holding_register":
                function_code = 3
                if iModPageSize > 123:
                    raise Exception("Too many holding registers (max. 123). Ignoring poller.")
            elif modRegType == "input_register":
                function_code = 4
                if iModPageSize > 123:
                    raise Exception(f"Too many input registers (max. 123): {iModPageSize}. Ignoring poller.")
            else:
                raise Exception(f"Unknown function code ({modRegType}) ignoring poller.")

            cPoller = Poller(cDevice,pollTree, self.args,function_code, iBaseAddress, iModPageSize )

            if(cPoller.deepdebug):  self.log.info(f"Add poller [{name}] to device=[{cDevice.name}]")
            elementsParseTree = pollTree.get("elements", [])
            assert elementsParseTree, "elements section is missing in YAML configuration"

            for element in elementsParseTree:
                self.parse_elements(cDevice,cPoller,element,name)

        except Exception as e:
            self.log.debug('Poller parser ',e)
            raise e
        return cPoller

    def parse_elements(self, cDevice, cPoller, data, pageName):
        assert cDevice,"no cDevice in parse_elements"
        assert cPoller,"no cPoller in parse_elements"
        assert data,"no data in parse_elements"

        try:
            name    = data.get('name').replace(" ", "_")
            address     = data.get('address', "")

            dtype       = data.get('dtype', '').lower().strip()
            rw          = data.get('rw', "r").strip()
            unit        = data.get('unit',"")
            scale       = data.get('scale', 1.0)
            lowRange    = data.get('lowR', None)
            highRange   = data.get('highR', None)
            osCondition = data.get('condition', "")
            osArgument  = data.get('argument', "")
            valueMap    = data.get("valueMap", [])
            try:
                if address.startswith("dse"):
                    dsarg = cPoller.modStartPage.split("!")
                    dsele = address.split("!")[1]
                    address = self.deepsea.getModbusSetting(dsarg[1], dsele)
                else:
                    address = int(eval(address))

            except Exception as e:
                raise ValueError(f"Failed to parse address or is not properly formatted {address} ")

            ref = Element(cPoller.device, name, address, dtype, rw, unit, scale, lowRange,highRange,osCondition,osArgument,valueMap)
            assert ref, "Element was create created"

            if ref in cPoller.readableElements:
                raise Exception(f"Element [{ref.name}] is already added. All element names must be unique.")

            if "r" in rw.lower():
                cPoller.add_readable_reference(ref)

            cDevice.add_reference_mapping(ref)
        except Exception as e:
            self.log.debug(f"Failed to parse {str(e)}")
            raise ValueError(f"Failed to parse {str(e)}")


