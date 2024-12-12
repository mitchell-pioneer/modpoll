import csv,json,math,logging
log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)

class DeepSeaModBusCalculator:
    BasicPageName = 'Basic instrumentation'
    ExtendedPageName = 'Extended instrumentation'
    GenSetStatusName= 'Generating set status information'
    AccumulatedName = 'Accumulated Instrumentation'
    NamedAlarmConditions = 'Named Alarm Conditions'


    def __init__(self):
        self.pages={e['Desc']:e for e in self.readFile('deepsea/pages.json')}
        self.basic={e['Name']:e for e in self.readFile('deepsea/basic.json')}
        self.extend={e['name']:e for e in self.readFile('deepsea/extended.json')}
        self.named={e['Name']:e for e in self.readFile('deepsea/namedAlarms.json')}
        self.manufacture={e['name']:e for e in self.readFile('deepsea/manufacture.json')}
        self.accumulated={e['name']:e for e in self.readFile('deepsea/accumulated.json')}
        self.log = log

    def readFile(self,fname):
        try:
            with open(fname) as f:
                return json.load(f)
        except Exception as err:
            self.log.debug(f"Cant find file json specificaton file={fname}")

    def getPageStartAddress(self,pageName):
        poffset = self.pages[pageName]['Page']
        return poffset*256      # each page is 256 bytes apart

    def getModbusSetting(self,pageName,cmdName):
        sec,i = self.getModbusSection(pageName,cmdName)
        return i

    def getModbusSection(self,pageName,cmdName):
        poffset = self.pages[pageName]['Page']
        self.lastSection = []
        match pageName:
            case self.AccumulatedName:
                self.lastSection = self.accumulated
            case self.BasicPageName:
                self.lastSection = self.basic
            case self.ExtendedPageName:
                self.lastSection = self.extend
            case self.NamedAlermConditions:
                self.lastSection = self.named

            case _:
                self.log.debug(f"Unknown deepsea page:{pageName}")
                return 0
        try:
            xx = self.lastSection[cmdName]['offset']
        except Exception as e:
            assert True, f"Cant process Element cmd={cmdName} in={self.NamedAlermConditions}"

        if isinstance(xx,str) and xx.find('-') :
            xl = xx.split("-")
            xx = int(xl[0])
        pp = (poffset * 256)
        return self.lastSection, pp + xx

    def getModbusFormatted(self,pageName,cmdName,rawValue):
        sect,i = self.getModbusSection(pageName,cmdName)
        cmd = sect[cmdName]
        realValue = rawValue * sect['scale']


    def testCases(self):
        op = self.getModbusSetting(self.BasicPageName, 'Oil pressure')
        if not op == 1024:
            print(f"Failed test for :{self.BasicPageName}:{'Oil pressure'}")
            return
        bv = self.getModbusSetting(self.BasicPageName, 'Engine Battery voltage')
        if not op == 1029:
            print(f"Failed test for :{self.BasicPageName}:{'Engine Battery voltage'}")
            return

