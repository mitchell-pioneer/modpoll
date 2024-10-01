import csv,json,math

class DeepSeaModBusCalculator:
    BasicPageName = 'Basic instrumentation'
    ExtendedPageName = 'Extended instrumentation'
    GenSetStatusName= 'Generating set status information'
    AccumulatedName = 'Accumulated Instrumentation'

    def __init__(self):
        self.pages={e['Desc']:e for e in self.readFile('deepsea/pages.json')}
        self.basic={e['name']:e for e in self.readFile('deepsea/basic.json')}
        self.extend={e['name']:e for e in self.readFile('deepsea/extended.json')}
        self.manufacture={e['name']:e for e in self.readFile('deepsea/manufacture.json')}
        self.accumulated={e['name']:e for e in self.readFile('deepsea/accumulated.json')}

    def readFile(self,fname):
        try:
            with open(fname) as f:
                return json.load(f)
        except Exception as err:
            print(f"Cant find file {fname}")

    def getPageStartAddress(self,pageName):
        poffset = self.pages[pageName]['Page']
        return poffset*256 ,123

    def getModbusSetting(self,pageName,cmdName):
        sec,i = self.getModbusSection(pageName,cmdName)
        return i

    def getModbusSection(self,pageName,cmdName):
        poffset = self.pages[pageName]['Page']
        self.lastSection = []
        match pageName:
            case self.BasicPageName:
                self.lastSection = self.basic
            case self.ExtendedPageName:
                self.lastSection = self.extend
            case _:
                print(f"Unknown deepsea page:{pageName}")
                return 0
        return self.lastSection, (poffset * 256) + self.lastSection[cmdName]['offset']


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












