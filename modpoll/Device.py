import logging
from typing import List

from modpoll import Poller
from modpoll.EventProcessor import EventProcessor

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)
class Device:
    def __init__(self,deviceTree):
        self.name = deviceTree.get("name", "noName")
        self.versionNumber = deviceTree.get("versionNumber", "1.0")
        self.enabled : bool = deviceTree.get("enabled", True)
        self.devId = deviceTree.get("device_id", "noDevId")
        self.osCmd = deviceTree.get("osCmd", "")
        self.mqttHost = deviceTree.get("mqttHost", None)
        self.ipAddress = deviceTree.get("ipAddress", "NoIpAddress")
        # if(self.ipAddress == "NoIpAddress"):
        #     self.ipList = deviceTree.get("addressList", [])
        self.loopDelay :int = deviceTree.get("loopDelay", 5)
        self.deviceLoopDelay :int = deviceTree.get("deviceLoopDelay", 0)
        self.execCondition  = EventProcessor()
        self.modbusTimeout :int = deviceTree.get("modbusTimeout", "5")
        self.modbusPort :int = deviceTree.get("modbusPort", "502")
        self.modbusDebug :bool= deviceTree.get("modbusDebug", False)
        self.deepDebug :bool= deviceTree.get("deepDebug", False)
        self.deepModbusPrint :bool = deviceTree.get("deepModbusPrint", False)
        self.onChangeReset :int = deviceTree.get("onChangeReset", 0)
        self.neverEnd :int = deviceTree.get("neverEnd", False)

        self.pollList : List[Poller] = []
        self.refList = {}
        self.errorCount = 0
        self.pollCount = 0
        self.pollSuccess = False
        if(self.deepDebug): log.info(f"Adding new device {self.name}")

    def add_reference_mapping(self, ref):
        self.refList[ref.name] = ref

    def saveLastValueForDiffCalc(self, ref):
        self.refList[ref.name].last_val = ref.last_val
        self.refList[ref.name].val = ref.val
