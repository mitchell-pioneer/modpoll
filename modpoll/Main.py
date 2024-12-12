import datetime,json,logging,re,signal,sys,threading,argparse,time
from datetime import timezone,datetime
from modpoll.Device import Device
from modpoll.ModbusControl import ModbusControl
from modpoll.MqttControl import MqttControl
from modpoll.YamlParser import YamlParser

event_exit = threading.Event()
log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)

def _signal_handler(signal, frame):
    log.info(f"Exiting {sys.argv[0]}")
    event_exit.set()

class Main:
    def __init__(self):
        self.mqttControl : MqttControl = {}
        self.modbus = None
        self.cmdLineArgs = ""
        self.yparser : YamlParser = {}
        self.device : Device ={}
        self.log = log
        pass
    def run(self, name="modpoll"):

        while True:
            print("\nmoddelta - A New Command-line Tool for Modbus and MQTT\n", flush=True)

            signal.signal(signal.SIGINT, _signal_handler)

            self.cmdLineArgs = args = self.get_parser().parse_args()
            LOG_SIMPLE = "%(asctime)s | %(levelname).1s | %(name)s | %(message)s"
            logging.basicConfig(level=args.loglevel, format=LOG_SIMPLE)

            self.yparser = YamlParser(self.cmdLineArgs)
            assert self.yparser ,"YamlParser was not created"

            self.mqttControl = MqttControl()
            assert self.mqttControl,"MqttControl was not created"

            self.modbus = ModbusControl(self.cmdLineArgs,self.yparser,self.mqttControl)
            assert self.modbus,"modbus was not created"

            self.device = self.modbus.deviceList[0]

            if (self.device.mqttHost):
                self.log.info(f"Setup MQTT connection to {args.mqtt_host}")
                if not self.mqttControl.mqttc_setup(args):
                    self.log.debug("Failed to setup MQTT client")
                    self.mqttControl.mqttc_close()
                    exit(1)
            else:
                self.log.info("No MQTT host specified, skip MQTT setup.")

            # main loop
            last_check = 0
            last_diag = 0

            # create timer so we can reset all last_val's in Elements.
            # This will force the pol.mqttOnChange to republish all values on a schedule
            if(self.device.onChangeReset > 0 and self.device.enabled):
                changeResetTimer = threading.Timer(self.device.onChangeReset, self.onChangeResetCallback)
                changeResetTimer.start()

            try:
                running = True
                while running:
                    pol = self.device.pollList[0]
                    topic = self.modbus.mqtt_topic_format(pol.mqttQueue) + "/" + "Status"

                    if(self.modbus.modbus_polling_loop() == False):
                        # if modbus cant reach the device, write error messages in queue
                        self.mqttControl.mqttc_publish(topic, f"No connection as of {datetime.now().strftime('%m/%d/%Y, %H:%M:%S')}")
                        time.sleep(self.device.deviceLoopDelay)
                        continue

                    self.mqttControl.mqttc_publish(topic, "")
                    if self.mqttControl.enabled:
                        self.modbus.modbus_publish()
                        self.WaitForInboundMqttMsg(args)
                    self.modbus.modbus_close()
                if (self.mqttControl.enabled): self.mqttControl.mqttc_close()

            except AssertionError as e:
                print(f"Assertion error", e)
                if (self.device.neverEnd == False):
                    break


    def onChangeResetCallback(self):
        # rest all last_val so next poll everything will apepar as new
        for dev in self.yparser.deviceList:
            if (dev.deepDebug): self.log.debug("Reseting all last val's")
            if(dev.enabled):
                for pol in self.device.pollList:
                    if(pol.enabled):
                        for ele in pol.readableElements:
                            ele.last_val = -9999

    def WaitForInboundMqttMsg(self, args):
        # Check if receive mqtt request
        topic, payload = self.mqttControl.mqttc_receive()
        if topic and payload:
            device_name = re.search(
                f"^{args.mqtt_topic_prefix}([^/\n]*)/set", topic
            ).group(1)
            if device_name:
                try:
                    reg = json.loads(payload)
                    if "coil" == reg["object_type"]:
                        if self.modbus.modbus_write_coil(device_name, reg["address"], reg["value"]):
                            self.log.info("")
                    elif "holding_register" == reg["object_type"]:
                        self.modbus.modbus_write_register(device_name, reg["address"], reg["value"])
                except json.decoder.JSONDecodeError:
                    self.log.warning(f"Failed to parse json message: {payload}")

    def get_utc_time(self):
        dt = datetime.datetime.now(timezone.utc)
        utc_time = dt.replace(tzinfo=timezone.utc)
        return utc_time.timestamp()


    def get_parser(self):
        parser = argparse.ArgumentParser(description=f"modpoll - A New Command-line Tool for Modbus and MQTT")
        parser.add_argument(
            "-v",
            "--version",
            action="version",
            version=f"modpoll",
        )
        parser.add_argument(
            "-f",
            "--config",
            #required=True,-
            help="A local path or URL of Modbus configuration file. Required!",
        )
        parser.add_argument(
            "-d",
            "--daemon",
            action="store_true",
            help="Run in daemon mode without printing result. Recommended to use with docker",
        )
        parser.add_argument(
            "-r",
            "--rate",
            type=float,
            default=10.0,
            help="The sampling rate (s) to poll modbus device, Defaults to 10.0",
        )
        parser.add_argument(
            "-1", "--once", action="store_true", help="Only run polling at one time"
        )
        parser.add_argument(
            "--interval",
            type=float,
            default=1.0,
            help="The time interval in seconds between two polling, Defaults to 1.0",
        )
        parser.add_argument(
            "--tcp", help="Act as a Modbus TCP master, connecting to host TCP"
        )
        parser.add_argument(
            "--tcp-port", type=int, default=502, help="Port for MODBUS TCP. Defaults to 502"
        )
        parser.add_argument(
            "--udp", help="Act as a Modbus UDP master, connecting to host UDP"
        )
        parser.add_argument(
            "--udp-port", type=int, default=502, help="Port for MODBUS UDP. Defaults to 502"
        )
        parser.add_argument("--rtu", help="pyserial URL (or port name) for RTU serial port")
        parser.add_argument(
            "--rtu-baud",
            type=int,
            default=9600,
            help="Baud rate for serial port. Defaults to 9600",
        )
        parser.add_argument(
            "--rtu-parity",
            choices=["none", "odd", "even"],
            default="none",
            help="Parity for serial port. Defaults to none",
        )
        parser.add_argument(
            "--timeout",
            type=float,
            default=3.0,
            help="Response time-out seconds for MODBUS devices, Defaults to 3.0",
        )
        parser.add_argument(
            "-o",
            "--export",
            default=None,
            help="The file name to export references/registers",
        )
        parser.add_argument(
            "--mqtt-host",
            default=None,
            help="MQTT server address. Skip MQTT setup if not specified",
        )
        parser.add_argument(
            "--mqtt-port",
            type=int,
            default=1883,
            help="1883 for non-TLS or 8883 for TLS, Defaults to 1883",
        )
        parser.add_argument(
            "--mqtt-clientid",
            default=None,
            help="MQTT client name, If qos > 0, set unique name for multiple clients",
        )
        parser.add_argument(
            "--mqtt-topic-prefix",
            default="modpoll/",
            help='Topic prefix for MQTT subscribing/publishing. Defaults to "modpoll/"',
        )
        parser.add_argument(
            "--mqtt-qos",
            choices=[0, 1, 2],
            default=0,
            help="MQTT QoS value. Defaults to 0",
        )
        parser.add_argument(
            "--mqtt-user", default=None, help="Username for authentication (optional)"
        )
        parser.add_argument(
            "--mqtt-pass", default=None, help="Password for authentication (optional)"
        )
        parser.add_argument("--mqtt-use-tls", action="store_true", help="Use TLS")
        parser.add_argument(
            "--mqtt-insecure",
            action="store_true",
            help="Use TLS without providing certificates",
        )
        parser.add_argument("--mqtt-cacerts", default=None, help="Path to ca keychain")
        parser.add_argument(
            "--mqtt-tls-version",
            choices=["tlsv1.2", "tlsv1.1", "tlsv1"],
            default="tlsv1.2",
            help="TLS protocol version, can be one of tlsv1.2 tlsv1.1 or tlsv1",
        )
        parser.add_argument(
            "--mqtt-single",
            action="store_true",
            help="Publish each value in a single topic. If not specified, groups all values in one topic.",
        )
        parser.add_argument(
            "--diagnostics-rate",
            type=float,
            default=0,
            help="Time in seconds as publishing period for each device diagnostics",
        )
        parser.add_argument(
            "--autoremove",
            action="store_true",
            help="Automatically remove poller if modbus communication has failed 3 times.",
        )
        parser.add_argument(
            "--loglevel",
            choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
            default="INFO",
            help="Set log level, Defaults to INFO",
        )
        parser.add_argument(
            "--timestamp", action="store_true", help="Add timestamp to the result"
        )
        parser.add_argument(
            "--delay",
            type=int,
            default=0,
            help="Time to delay sending first request in seconds after connecting. Default to 0",
        )
        parser.add_argument(
            "--framer",
            default="default",
            choices=["default", "ascii", "binary", "rtu", "socket"],
            help="The type of framer for modbus message. Use default framer if not specified.",
        )
        parser.add_argument(
            "--mqtt-onchange",
            action="store_true",
            help="Publish to MQTT when values change"
        )
        parser.add_argument(
            "--runEnv",
            type=open,
            action=LoadFromFile,
            help="Use and .env file for commandline options"
        )
        return parser

class LoadFromFile (argparse.Action):
    # https://stackoverflow.com/questions/27433316/how-to-get-argparse-to-read-arguments-from-a-file-with-an-option-rather-than-pre
    def __call__ (self, parser, namespace, values, option_string = None):
        with values as f:
            # parse arguments in the file and store them in the target namespace
            parser.parse_args(f.read().split(), namespace)


