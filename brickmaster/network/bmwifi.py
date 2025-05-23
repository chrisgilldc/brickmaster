"""
Brickmaster Wifi Handling
"""
import adafruit_logging
import adafruit_connection_manager
import supervisor
import time
import brickmaster.const
import brickmaster.util

class BMWiFi:
    """
    Brickmaster WiFi Handling for CircuitPython Boards
    """
    def __init__(self, ssid, password, wifihw=None, retry_limit = 5, retry_time = 30, hostname = None, 
                 log_level=adafruit_logging.DEBUG):
        """
        Set up the Brickmaster WiFi handler. Works for ESP32s, direct or SPI connected.

        :param ssid: Network to connect to.
        :type ssid: str
        :param password: Password for the network.
        :type password: str
        :param wifihw: Hardware type. May be 'esp32', 'esp32spi' or 'none'. If 'none', system will try to autodetect.
        :type wifihw: str
        :param retry_limit: How many times to retry connecting before declaring failure.
        :type retry_limit: int
        :param retry_time: How long to wait between retries, in seconds.
        :type retry_time: int
        :param hostname: Hostname to set. Otherwise will default to whatever the board wants.
        :type hostname: str
        :param log_level:
        """
        # Create the logger and set the level to debug. This will get reset later.
        self._logger = adafruit_logging.getLogger("Brickmaster")
        self._logger.setLevel(log_level)

        self._hostname = hostname
        self._ip = None
        self._mac_string = None
        self._password = password
        self._retry_limit = retry_limit
        self._retry_time = retry_time
        self._retries = 0
        self._ssid = ssid
        if wifihw is None:
            self._logger.warning("WIFI: Hardware not defined. Trying to determine automatically.")
            self._wifihw = brickmaster.util.determine_wifi_hw()
            self._logger.warning("WIFI: Auto-determined hardware to be '{}'".format(self._wifihw))
        else:
            self._wifihw = wifihw

        self._setup_wifi()
        self._logger.info("WIFI: Initialization complete")

    # Public Methods
    def connect(self):
        """
        Connect to the wireless network.
        """
        tries = 0
        if self.is_connected:
            self._logger.debug("WIFI: Already connected, nothing more to do.")
            return brickmaster.const.NET_STATUS_CONNECTED
        else:
            if self._wifihw == 'esp32spi':
                while tries < self._retry_limit:
                    try:
                        self._logger.debug("WIFI: Connecting to '{}' with password '{}'".
                                           format(self._ssid, self._password))
                        self._wifi.connect_AP(self._ssid, self._password)
                    except ConnectionError as e:
                        if e.args[0] == "No such ssid":
                            # The ESP32 (SPI, at least), has a glitch where sometimes it can't find the network on the
                            # first try. Don't fail immediately, just try again.
                            self._logger.warning(f"WIFI: SSID '{self._ssid}' not found. Will retry in {self._retry_time}s")
                            tries += 1
                            time.sleep(self._retry_time)
                            continue
                        else:
                            raise
                    except OSError as e:
                        self._logger.warning(f"WIFI: Could not connect to WIFI SSID '{self._ssid}'. "
                                             "Retrying in {self._retry_time}s.")
                        self._logger.warning(str(e), type(e))
                        tries += 1
                        time.sleep(self._retry_time)
                        continue
                    else:
                        self._logger.info("WiFi: Setting IP to: {}".format(self._wifi.ip_address))
                        self._ip = self._wifi.pretty_ip(self._wifi.ip_address)
                        self._logger.info("WiFi: IP is now {}".format(self._ip))
                        self._logger.info(f"WiFi: Connected to '{self._ssid}', received IP '{self._ip}'")
                        return brickmaster.const.NET_STATUS_CONNECTED
                return brickmaster.const.NET_STATUS_DISCONNECTED
            else:
                self._wifi.connect(ssid=self._ssid, password=self._password)
                self._logger.info("WiFi: Setting ip to '{}'".format(self._wifi.ipv4_address))
                self._ip = self._wifi.ipv4_address
                self._logger.info("WiFi: IP is set to '{}'".format(self._ip))
                return brickmaster.const.NET_STATUS_CONNECTED

    def disconnect(self):
        """
        Disconnect from the wireless network.
        """
        if self._wifihw == 'esp32spi':
            try:
                self._logger.debug("WiFi: Attempting disconnect.")
                self._wifi.disconnect()
            except OSError:
                self._logger.critical("WiFi: Could not disconnect from WiFi Network.")
                raise brickmaster.exceptions.BMRecoverableError("WiFi could not disconnect")
            else:
                return brickmaster.const.NET_STATUS_DISCONNECTED
        else:
            return brickmaster.const.NET_STATUS_NOACTION

    @property
    def is_connected(self):
        """
        Are we connected to the wireless interface?
        :return: bool
        """
        if self._wifihw == 'esp32spi':
            return self._wifi.is_connected
        else:
            return self._wifi.connected

    def set_loglevel(self, log_level):
        """
        Set the level to log at.
        """
        self._logger.setLevel(log_level)

    # Public Properties
    # @property
    # def esp(self):
    #     """
    #     The ESP object. Needed to create the MQTT client on ESP32SPI, otherwise, really don't manipulate this!
    #     :return:
    #     """
    #     return self._esp

    @property
    def socket_pool(self):
        """
        Property to get a socket pool
        :return:
        """
        # if self._wifihw == 'esp32spi':
        #     return
        # else:
        #     return socketpool.SocketPool(wifi.radio)
        return adafruit_connection_manager.get_radio_socketpool(self._wifi)

    @property
    def wifihw(self):
        """
        The defined or determined WiFiHW.
        :return:
        """
        return self._wifihw

    @property
    def wifi_mac(self):
        """
        The MAC string of the WIFI interface.

        :return:
        """
        return self._mac_string

    @property
    def ip(self):
        """
        The IP of the interface. Returns None if not connected.

        :return: str
        """
        if self.wifihw == 'esp32spi':
            return self._wifi.pretty_ip(self._wifi.ip_address)
        else:
            return str(self._wifi.ipv4_address)

    # Private Methods
    def _setup_wifi(self):
        """
        Configure the wireless hardware.
        """
        self._logger.info("WIFI: Beginning hardware initialization.")
        if self._wifihw == 'esp32':
            # Import Wifi
            global wifi
            import wifi
            # Do the setup.
            self._logger.info("Wifi: Configuring Native ESP32...")
            self._wifi = wifi.radio
            self._mac_string = "{:X}{:X}{:X}{:X}{:X}{:X}". \
                format(self._wifi.mac_address[0], self._wifi.mac_address[1], self._wifi.mac_address[2],
                       self._wifi.mac_address[3], self._wifi.mac_address[4], self._wifi.mac_address[5])
            # Set the hostname
            if self._hostname is not None:
                try:
                    self._wifi.hostname = self._hostname
                except ValueError:
                    self._logger.error("WiFi: Hostname '{}' is not valid. Using default of '{}'".format(self._hostname, self._wifi.hostname))
                else:
                    self._logger.info(f"Wifi: Set hostname to '{self._wifi.hostname}'")
        elif self._wifihw == 'esp32spi':
            # Conditional imports for ESP32SPI boards.
            ## Board
            global board
            import board
            ## Digital pins
            global DigitalInOut
            from digitalio import DigitalInOut
            ## Bus interface
            global busio
            import busio
            ## ESP32SPI libraries
            global adafruit_esp32spi
            from adafruit_esp32spi import adafruit_esp32spi
            # See if the board has pins defined for an ESP32 coprocessor. If so, we use the ESP32SPI library.
            # Tested on the Metro M4 Airlift.
            self._logger.info("WIFI: Configuring ESP32 Co-Processor...")
            try:
                esp32_cs = DigitalInOut(board.ESP_CS)
                esp32_ready = DigitalInOut(board.ESP_BUSY)
                esp32_reset = DigitalInOut(board.ESP_RESET)
                spi = busio.SPI(board.SCK, board.MOSI, board.MISO)
                self._wifi = adafruit_esp32spi.ESP_SPIcontrol(spi, esp32_cs, esp32_ready, esp32_reset)
            except AttributeError as e:
                self._logger.error("WIFI: ESP32 Co-Processor not defined.")
                self._logger.error(str(e))
            else:
                # Define the ESP controls
                # Define the ESP controls
                if self._wifi.status == adafruit_esp32spi.WL_IDLE_STATUS:
                    self._logger.info("WIFI: ESP32 co-processor found and idle.")
                else:
                    self._logger.warning("WIFI: ESP32 co-processor busy. Resetting!")
                    supervisor.reload()
                time.sleep(5)
                self._logger.info("Wifi: ESP32 Firmware version is '{}.{}.{}'".format(
                    self._wifi.firmware_version[0], self._wifi.firmware_version[1], self._wifi.firmware_version[2]))
                self._mac_string = "{:X}{:X}{:X}{:X}{:X}{:X}".format(
                    self._wifi.MAC_address[5], self._wifi.MAC_address[4], self._wifi.MAC_address[3],
                    self._wifi.MAC_address[2], self._wifi.MAC_address[1], self._wifi.MAC_address[0])
                # # Set the hostname
                # if self._hostname is not None:
                #     self._wifi.set_hostname(self._hostname)
                #     self._logger.debug(f"Wifi: Set hostname to {self._wifi.hostname}")
        else:
            raise ValueError("WIFI: Hardware type '{}' not supported.".format(self._wifihw))

        self._logger.info("WIFI: WiFi MAC address: {}".format(self._mac_string))
        self._logger.info("WIFI: Hardware initialization complete.")