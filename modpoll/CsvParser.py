import logging,csv
import traceback
import requests

from deepsea.DeepSeaModBusCalculator import DeepSeaModBusCalculator
from modpoll.Device import Device
from modpoll.Element import Element
log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)
class CsvParser:
    def __init__(self,args):
        self.args = args
        self.deepsea = DeepSeaModBusCalculator()
        self.deviceList = []

    def fileReader(self, file):
        if (file.startswith(("http", "https"))):
            with requests.Session() as s:
                response = s.get(file)
                decoded_content = response.content.decode("utf-8")
                csv_reader = csv.reader(decoded_content.splitlines(), delimiter=",")
                devices = self.parse(csv_reader)
        else:
            with open(file, "r") as f:
                f.seek(0)
                csv_reader = csv.reader(f)
                devices = self.parse(csv_reader)
        return devices

    def parse_device(self, row):
        name = row[1]
        device_id = int(row[2])
        ipaddress = row[3]
        newDevice = Device(name, device_id)
        self.deviceList.append(newDevice)
        return newDevice

    def parse(self, csv_reader, tracebackxxx=None):
        dList = []
        current_poller = []
        pageName = ""
        try:
            for row in csv_reader:
                if not row or len(row) == 0:
                    continue
                if row[0].startswith('#'):
                    continue
                if "device" in row[0].lower():
                    cDevice = self.parse_device(row)
                    dList.append(cDevice)
                elif "poll" in row[0].lower():
                    current_poller, pageName = self.parse_poll(cDevice, row)
                elif "ref" in row[0].lower():
                    self.parse_ref(cDevice, current_poller, row, pageName)
            return dList
        except Exception as e:
            error_message = traceback.format_exc()
            log.debug(f"Failed to parse csv Error=ParseConfig:parse={e}:{error_message}")
            exit(1)

    def parse_ref(self, cDevice, cPoller, row, pageName):
        ref_name = row[1].replace(" ", "_")
        if (row[1].startswith("dsElement")):  # if this a deepsea element refrence
            dsarg = row[1].split("!")
            mbs = self.deepsea.getModbusSetting(pageName, dsarg[1])
            address = mbs
        else:
            address = int(eval(row[2]))
        dtype = row[3].lower().strip()
        rw = row[4].strip() or "r"
        try:
            unit = row[5].strip()
        except IndexError:
            unit = None
        try:
            scale = float(row[6].strip())
        except Exception:
            scale = None
        try:
            hrange = 0.0
            hrange = float(row[7].strip())
        except Exception:
            hrange = None
        try:
            lrange = 0.0
            lrange = float(row[8].strip())
        except Exception:
            lrange = None
        try:
            trans = ""
            trans = row[9].strip()
        except Exception:
            trans = None

        if not cDevice or not cPoller:
            raise Exception(f"No device/poller for reference {ref_name}.")

        # build the Refrerence and add to Poller
        ref = Element(cPoller.device, ref_name, address, dtype, rw, unit, scale, hrange, lrange, trans)
        if ref in cPoller.readableElements:
            raise Exception(f"Reference {ref.name} is already added, ignoring it.")
        if not ref.check_sanity(
                cPoller.start_address, cPoller.size
        ):
            raise Exception(
                f"Reference {ref.name} failed to pass sanity check, ignoring it."
            )
            return
        if "r" in rw.lower():
            cPoller.add_readable_reference(ref)
        cDevice.add_reference_mapping(ref)
        #log.error(f"Add reference {ref.name} to device {cDevice.name}")

    def parse_poll(self, cDevice, column):
        pName = None
        fc = column[1].lower()
        if (column[2].startswith('dsPage')):  # is this a deepsea page refrerence
            ptype = column[2].split('!')[1]
            start_address = self.deepsea.getPageStartAddress(ptype)
            size = int(column[3])
            pName = ptype
        else:
            pName = column[1]
            potexp = column[2]
            start_address = int(eval(potexp))
            size = int(column[3])

        endian = column[4]

        if not cDevice:
            raise Exception("No device to add poller.")
        if "coil" == fc:
            function_code = 1
            if size > 2000:  # some implementations don't seem to support 2008 coils/inputs
                raise Exception("Too many coils (max. 2000). Ignoring poller.")
        elif "discrete_input" == fc:
            function_code = 2
            if size > 2000:
                raise Exception("Too many discrete inputs (max. 2000). Ignoring poller.")
        elif "holding_register" == fc:
            function_code = 3
            if (size > 123):  # applies to TCP, RTU should support 125 registers. But let's be safe.
                raise Exception("Too many holding registers (max. 123). Ignoring poller.")
        elif "input_register" == fc:
            function_code = 4
            if size > 123:
                raise Exception(f"Too many input registers (max. 123): {size}. Ignoring poller.")
        else:
            raise Exception(f"Unknown function code ({fc}) ignoring poller.")

        from modpoll.Poller import Poller
        cPoller = Poller(cDevice, self.args,function_code, start_address, size, endian)
        cDevice.pollerList.append(cPoller)
        log.info(
            f"Add poller [{pName}] to device=[{cDevice.name}] (start_address={cPoller.start_address}, size={cPoller.size}) to "
        )
        return cPoller, pName