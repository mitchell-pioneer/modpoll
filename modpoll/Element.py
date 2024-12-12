import logging
import math
log = logging.getLogger(__name__)
log.setLevel(logging.INFO)
import numpy as np

class Element:
    def __init__(self, device, name: str, address: int, dtype: str, rw: str, unit, scale,lrange,hrange,condition,argument,valueMap):
        self.log = log
        self.device :device = device
        self.name :str  = name
        self.address = address
        self.dtype = dtype.lower()
        self.unit :str = unit
        self.rw = rw.lower()
        self.scale :str = scale
        self.hrange :float = hrange
        self.lrange :float = lrange
        self.condition = condition
        self.argument = argument
        self.valueMap = valueMap
        # val and last_val can have a different type for each row
        self.val = None
        self.last_val = -9999
        #
        self.ref_width = 0
        if "int16" == dtype:
            self.ref_width = 1
        elif "uint16" == dtype:
            self.ref_width = 1
        elif "int32" == dtype:
            self.ref_width = 2
        elif "uint32" == dtype:
            self.ref_width = 2
        elif "int64" == dtype:
            self.ref_width = 4
        elif "uint64" == dtype:
            self.ref_width = 4
        elif "float16" == dtype:
            self.ref_width = 1
        elif "float32" == dtype:
            self.ref_width = 2
        elif "float64" == dtype:
            self.ref_width = 4
        elif "bool8" == dtype:
            self.ref_width = 1
        elif "bool" == dtype:
            self.ref_width = 1
        elif "u16n0" == dtype:
            self.ref_width = 2
        elif "u16n1" == dtype:
            self.ref_width = 2
        elif "u16n2" == dtype:
            self.ref_width = 2
        elif "u16n3" == dtype:
            self.ref_width = 2
        elif dtype.startswith('b') and dtype.find("16") != -1:
            self.ref_width = 2

        elif dtype.startswith("string"):
            try:
                self.ref_width = int(dtype[6:9])
            except ValueError:
                self.ref_width = 2

            if self.ref_width > 100:
                self.log.warning("Data type string: length must be less than 100")
                self.ref_width = 100
            if math.fmod(self.ref_width, 2) != 0:
                self.ref_width = self.ref_width - 1
                self.log.warning("Data type string: length must be divisible by 2")
        else:
            self.log.error(f"Unknown data type: {dtype}")
        if device.deepDebug:  self.log.info(f"Adding new Element {self.name}")

    def process_os_event(self):
        self.device.eventProcessor.processEvent(self.condition,self.argument)

    def check_sanity(self, reference, size):
        if self.address not in range(reference, size + reference):
            return False
        if self.address + self.ref_width - 1 not in range(reference, size + reference):
            return False
        return True


    def scaleValue(self, v):
        # calculate val using eval method
        # set last val

        if isinstance(v, str | None):
            # if v is a string we cant scale it.
            pass
        elif isinstance(self.scale, float):
            if isinstance(v,int):
                # scale is a float and v is an int so cast float back to int
                v = int(v * self.scale)
            else:
                # v was already a float
                v = v * self.scale
        elif isinstance(self.scale, str):
            # we can use more complex scaling e.g.  {}/3600 or {} * 0.1
            if self.scale.find("{") == -1:
                # evaluate it as v * 0.1
                ss = f"{v} {self.scale}"
            else:
                # evaluate it as  {}/3600 or {} * 0.1"
                ss = self.scale.format(v)
            try:
                v = eval(ss)
            except ValueError:
                pass
            if isinstance(v, int):
                v = int(v)

        self.last_val = self.val
        self.val = v

    # def update_value2(self, v):
    #     try:
    #
    #         match self.dtype:
    #             case "int16":
    #                 nv = np.int16(v) * self.scale
    #             case "int32":
    #                 nv = np.int32(v) * self.scale
    #             case "uint16":
    #                 nv = np.uint16(v) * self.scale
    #             case "uint32":
    #                 nv = np.uint32(v) * self.scale
    #             case "float16":
    #                 nv = np.float16(v) * self.scale
    #             case "float32":
    #                 nv = np.float16(v) * self.scale
    #             case _ :
    #                 self.log.debug(f"Cant scale {v} to {self.dtype}")
    #         self.last_val = self.val
    #         self.val = nv
    #     except Exception as e:
    #         self.log.debug(f"Number format error {self.dtype} {nv}")


    def __eq__(self, other):
        """Overrides the default implementation"""
        if isinstance(other,Element ):
            return self.address+hash(self.name) == other.address+hash(other.name)
        return False
