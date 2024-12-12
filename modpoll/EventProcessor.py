import os,logging

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)
class EventProcessor:
    def __init__(self):
        self.log = log
        pass

    def processEvent(self,condition,val,argument):
        ee = f"{val} {condition}"
        if(eval(ee)):
            self.log.debug(f"Excute os command [{condition}] [{argument}]")
            os.system(f" {argument} >> ProcessedEvents.log")




