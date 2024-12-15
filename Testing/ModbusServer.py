from pymodbus.server import StartTcpServer
from pymodbus.device import ModbusDeviceIdentification
from pymodbus.datastore import ModbusSlaveContext, ModbusSequentialDataBlock
import logging

class ModbusTCPTestService:
    def __init__(self, host='localhost', port=44038):
        self.host = host
        self.port = port
        self.holding_registers = list(range(0, 100))  # Adding more holding registers

    def set_holding_register(self, address, value):
        """
        Set the value of a specific holding register.
        :param address: Register address (0-based index)
        :param value: Value to set
        """
        self.datastore[0].setValues(0x03, address, [value])

    def initialize_datastore(self):
        """
        Initialize the Modbus datastore with the initial holding register values.
        """
        self.datastore = {
            0: ModbusSlaveContext(
                di=ModbusSequentialDataBlock(0, [0] * 100),  # Discrete Inputs
                co=ModbusSequentialDataBlock(0, [0] * 100),  # Coils
                hr=ModbusSequentialDataBlock(0, self.holding_registers),  # Holding Registers
                ir=ModbusSequentialDataBlock(0, [0] * 100)  # Input Registers
            )
        }
    def run(self):
        self.initialize_datastore()

        # Example: Update specific holding register values before starting the server
        self.set_holding_register(0, 0)  # Set holding register 10 to 12345
        self.set_holding_register(1, 1)  # Set holding register 15 to 67890
        self.set_holding_register(2, 2)  # Set holding register 10 to 12345
        self.set_holding_register(3, 3)  # Set holding register 10 to 12345
        self.set_holding_register(4, 4)  # Set holding register 15 to 67890
        self.set_holding_register(5, 5)  # Set holding register 10 to 12345
        self.set_holding_register(6, 6)  # Set holding register 15 to 67890
        self.set_holding_register(7, 7)  # Set holding register 10 to 12345
        self.set_holding_register(8, 7)  # Set holding register 15 to 67890

        # Set up server identification
        identity = ModbusDeviceIdentification()
        identity.VendorName = 'TestVendor'
        identity.ProductCode = 'TestServer'
        identity.VendorUrl = 'https://example.com'
        identity.ProductName = 'Modbus Test Server'
        identity.ModelName = 'ModbusTCPServer'
        identity.MajorMinorRevision = '1.0'

        # Start the Modbus TCP server
        logging.basicConfig()
        logging.getLogger().setLevel(logging.DEBUG)
        StartTcpServer(
            context=self.datastore, address=(self.host, self.port), identity=identity,
            ignore_missing_slaves=True
        )

if __name__ == '__main__':
    # Initialize and run the Modbus TCP test service
    server = ModbusTCPTestService(host='localhost', port=44038)
    server.run()


# from pymodbus.server import StartTcpServer
# from pymodbus.device import ModbusDeviceIdentification
# from pymodbus.datastore import ModbusSlaveContext, ModbusSequentialDataBlock
# import logging
#
# class ModbusTCPTestService:
#     def __init__(self, host='localhost', port=44038):
#         self.host = host
#         self.port = port
#         self.holding_registers = list(range(0, 100))  # Adding more holding registers
#
#     def run(self):
#         from pymodbus.datastore import ModbusSequentialDataBlock
#
#         # Define initial test values for registers
#         datastore = ModbusSlaveContext(
#             di=None,  # Discrete Inputs
#             co=None,  # Coils
#             hr=ModbusSequentialDataBlock(0, self.holding_registers),  # Holding Registers
#             ir=None   # Input Registers
#         )
#
#         # Example: Update specific holding register values
#         datastore.setValues('hr', 10, [12345])  # Set holding register 10 to 12345
#         datastore.setValues('hr', 15, [67890])  # Set holding register 15 to 67890
#
#         # Set up server identification
#         identity = ModbusDeviceIdentification()
#         identity.VendorName = 'TestVendor'
#         identity.ProductCode = 'TestServer'
#         identity.VendorUrl = 'https://example.com'
#         identity.ProductName = 'Modbus Test Server'
#         identity.ModelName = 'ModbusTCPServer'
#         identity.MajorMinorRevision = '1.0'
#
#         # Start the Modbus TCP server
#         logging.basicConfig()
#         logging.getLogger().setLevel(logging.DEBUG)
#         StartTcpServer(
#             context=datastore, address=(self.host, self.port), identity=identity
#         )
#
# if __name__ == '__main__':
#     # Initialize and run the Modbus TCP test service
#     server = ModbusTCPTestService(host='localhost', port=502)
#     server.run()