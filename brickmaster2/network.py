# Brickmaster2 Network handling module

import os
import sys
import board
import busio
import time
import json

import digitalio
from digitalio import DigitalInOut
import adafruit_logging
import adafruit_minimqtt.adafruit_minimqtt as af_mqtt

# from adafruit_datetime import datetime
import brickmaster2.scripts
import brickmaster2.controls
import gc
#import supervisor


class BM2Network:
    def __init__(self, core, system_id, system_name, broker, mqtt_username, mqtt_password, ssid=None, password=None,
                 net_on=None, net_off=None, port=1883, ha_discover=False, ha_base='homeassistant', ha_area=None,
                 ha_meminfo='unified', wifihw=None, time_mqtt=False, **kwargs):

        self._system_name = system_name
        self._system_id = system_id
        self._broker = broker
        self._mqtt_port = port
        self._mqtt_username = mqtt_username
        self._mqtt_password = mqtt_password
        self._mqtt_connected = False
        self._mqtt_failure_notice = False
        self._ssid = ssid
        self._ssid_password = password
        self._ha_discover = ha_discover
        self._ha_base = ha_base
        self._ha_area = ha_area
        self._ha_meminfo = ha_meminfo
        self._time_mqtt = time_mqtt

        # Save a reference to the core. This allows callbacks to the core.
        self._core = core
        self._logger = adafruit_logging.getLogger('BrickMaster2')
        # Log some things, if we want.
        self._logger.info("Network System Name: {}".format(self._system_name))
        self._logger.debug("Received extra arguments - {}".format(kwargs))

        if wifihw is None:
            self._logger.info("Network: WiFi type not set in config. Attempting to auto-detect.")
            if os.uname().sysname.lower() in ('samd51'):
                self._logger.warning("Network: System type is '{}'. Trying 'esp32spi' co-processor. "
                                     "Better to set 'wifihw' in 'system' config section.".format(os.uname().sysname))
                self._wifihw = 'esp32spi'
            elif os.uname().sysname.lower() in ('esp32'):
                self._logger.warning("Network: System type is '{}'. Trying native 'esp32'. "
                                     "Better to set 'wifihw' in 'system' config section.".format(os.uname().sysname))
                self._wifihw = 'esp32'
            else:
                self._logger.critical("Network: System type '{}' does not have a known wifi type! Cannot continue!")
                self._logger.critical("Halting now!")
                sys.exit(1)
        else:
            self._logger.info("Network: WiFi type set to '{}' via config file.".format(wifihw))
            self._wifihw = wifihw


        self._logger.info("Network MQTT options: {}@{}:{}".format(self._mqtt_username, self._broker, self._mqtt_port))

        if self._ha_discover:
            self._logger.info("Network Home Assistant options:\n\tDiscovery prefix: {}\n\tDefault Area: {}".
                              format(self._ha_base, self._ha_area))
        else:
            self._logger.info("Network: Home Assistant options disabled.")

        # null_handler = adafruit_logging.NullHandler()
        # self._logger.addHandler(null_handler)
        self._logger.info("Initializing network...")
        self._topic_prefix = "brickmaster2/" + self._system_id

        # Create network status indicator GPIO controls, if defined.
        if net_on is not None:
            self._logger.debug("Network: Net on indicator created")
            self._led_neton = digitalio.DigitalInOut(getattr(board, str(net_on)))
            self._led_neton.switch_to_output(value=False)
        else:
            self._led_neton = None
        if net_off is not None:
            self._logger.debug("Network: Net off indicator created")
            self._led_netoff = digitalio.DigitalInOut(getattr(board, str(net_off)))
            self._led_netoff.switch_to_output(value=True)
        else:
            self._led_netoff = None

        # If not on a general-purpose system, set up WIFI.
        if os.uname().sysname.lower() == 'linux':
            # On a general-purpose Linux system, the OS handles the network. We only need the socket library.
            global socket
            import socket

        elif self._wifihw == 'esp32':
            self._logger.info("Network: Importing esp32 support.".format(os.uname().sysname))
            global wifi
            global socketpool
            global supervisor
            import wifi
            import socketpool
            import supervisor
        elif self._wifihw == 'esp32spi':
            self._logger.info("Network: Importing esp32 co-processor support.".
                              format(os.uname().sysname))
            global adafruit_esp32spi
            global socket
            global supervisor
            from adafruit_esp32spi import adafruit_esp32spi
            import adafruit_esp32spi.adafruit_esp32spi_socket as socket
            import supervisor

        else:
            raise ValueError("Wifi Hardware setting '{}' not valid.".format(self._wifihw))

        # Connect to the network
        self._setup_wifi()
        self._clock_set = False
        self._clock_last_set = 0
        # self._set_clock()

        # Initialize MQTT topic variables.
        # Inbound starts empty and will be expanded as controls are added.
        self._topics_inbound = []
        # Default startup topics.
        self._topics_outbound = {
            'connectivity': {
                'topic': self._topic_prefix + '/connectivity',
                'repeat': False,
                'retain': True,
                'previous_value': 'Unknown',
                'publish_after_discovery': 120,
                'discovery_time': 0.0,
                'obj': None  # No object, but include this to prevent breakage.
            },
            'meminfo': {
              'topic': self._topic_prefix + '/meminfo',
              'repeat': False,
              'retain': False,
              'previous_value': 'Unknown',
              'publish_after_discovery': 1,
              'discovery_time': 0.0,
              'obj': None
            },
            'active_script': {
                'topic': self._topic_prefix + '/active_script',
                'repeat': False,
                'retain': False,
                'obj': self._core,
                'value_attr': 'active_script',
                'previous_value': 'Unknown',
                'publish_after_discovery': 120,
                'discovery_time': 0.0
            }
        }

        # Topics for discovery.
        self._topics_discovery = {}
        # Set up initial MQTT tracking values.
        self._mqtt_timeouts = 0
        self._reconnect_timestamp = time.monotonic()
        self._setup_mini_mqtt()
        self._logger.info("Network: Initialization complete. Making initial connection")
        # Make initial connection.
        self._connect_wifi()
        self._connect_mqtt()

    # Main polling loop. This gets called by the main system run loop when it's time to poll the network.
    def poll(self):
        """
        Main network polling loop.

        :return:
        """
        # Do connectivity check.
        if not self._connectivity_check():
            return

        try:
            timeout = 0.25
            self._logger.debug("Network: Polling MQTT Broker. Timeout is {}s".format(timeout))
            start_time = time.monotonic()
            self._mqtt_client.loop(timeout=timeout)
            end_time = time.monotonic()
            if self._time_mqtt:
                self._logger.info("Network: MQTT poll took {}s".format(end_time-start_time))
        except af_mqtt.MMQTTException:
            # self._logger.warning("Network: MQTT poll timed out.")
            self._logger.debug("Network MQTT connection state: {}".format(self._mqtt_client.is_connected()))
            return
        except ConnectionError:
            self._logger.warning("Network: Connection error when polling MQTT broker.")
            return
        except TimeoutError as e:
            if os.uname().sysname.lower() != 'linux':
                self._logger.critical("Network: Wifi device not responding. Resetting.")
                self._logger.info(str(e))
                # Call setup to set the interface up again.
                supervisor.reload()
            else:
                raise

        # Publish an online message.
        self.publish('connectivity', 'online')
        # Publish memory stats.
        self.publish('meminfo', self._meminfo())

        # Publish any outbound topics.
        self._publish_outbound()
        # Garbage collect.
        gc.collect()

    def _connectivity_check(self):
        # If on non-Linux system, check to see if the network is connected.
        # There are different connection requirements for the ESP32 vs. the ESP32 co-processor.
        # This also sets the MQTT connection to be false, since definitionally if we've lost the network we've also
        # lost the MQTT connection.
        if self._wifihw == 'esp32':
            if not self._wifi.connected:
                self._mqtt_connected = False
                self._logger.warning("Network: WiFi not connected!")
                self._set_indicator("off")
                self._connect_wifi()
        elif self._wifihw == 'esp32spi':
            if not self._esp.is_connected:
                self._mqtt_connected = False
                self._logger.warning("Network: WiFi not connected!")
                self._set_indicator("off")
                self._connect_wifi()

        # If network connectivity is up, check for MQTT connectivity
        if not self._mqtt_connected:
            if self._mqtt_failure_notice is False:
                self._logger.warning("Network: MQTT client not connected! Will retry in 30s.")
                self._mqtt_failure_notice = True
            # Has is been 30s since the previous attempt?
            if time.monotonic() - self._reconnect_timestamp > 30:
                self._mqtt_failure_notice = False
                self._logger.info("Network: Attempting MQTT reconnect...")
                self._reconnect_timestamp = time.monotonic()
                # If MQTT isn't connected, nothing else to do.
                if not self._connect_mqtt():
                    self._logger.warning("Network: MQTT not reconnected!")
                    return False
                else:
                    self._logger.warning("Network: MQTT client reconnected.")
            else:
                return False
        else:
            self._logger.debug("Network: MQTT connected. Continuing.")
            return True

    # Connect to the MQTT broker.
    def _connect_mqtt(self):
        try:
            if self._mqtt_client.is_connected():
                self._mqtt_client.reconnect()
            else:
                self._mqtt_client.connect(host=self._broker, port=self._mqtt_port)
        except Exception as e:
            self._logger.warning('Network: Could not connect to MQTT broker. Waiting 30s')
            self._logger.warning('Network: ' + str(e))
            self._set_indicator("off")
            time.sleep(30)
            return False
        else:
            self._set_indicator("on")
            self._mqtt_connected = True

        # Subscribe to the system command topic.
        try:
            self._mqtt_client.subscribe(self._topic_prefix + '/syscmd')
        except af_mqtt.MMQTTException:
            self._logger.error("Network: Could not subscribe to system command topic '{}'".
                               format(self._topic_prefix + '/syscmd'))
        else:
            self._mqtt_client.add_topic_callback(self._topic_prefix + '/syscmd', self._cb_syscmd)

        # Send a discovery message and an online notification.
        if self._ha_discover:
            self._ha_discovery()

        # # Send the online notification.
        self.publish('connectivity', 'online')
        # Publish all the topics.
        self._publish_outbound()
        return True

    def _connect_wifi(self):
        if self._wifihw == 'esp32':
            self._wifi.connect(ssid=self._ssid, password=self._ssid_password)
            ip = self._wifi.ipv4_address
        if self._wifihw == 'esp32spi':
            # Try to do the connection
            while not self._esp.is_connected:
                self._set_indicator("off")
                try:
                    self._logger.debug("Connecting to '{}' with password '{}'".
                                       format(self._ssid, self._ssid_password))
                    self._esp.connect_AP(self._ssid, self._ssid_password)
                except OSError as e:
                    self._logger.warning("Network: Could not connect to WIFI SSID '{}'. "
                                         "Retrying in 30s.".format(self._ssid))
                    self._logger.warning(str(e))
                    time.sleep(30)
                    continue
                else:
                    ip = self._esp.pretty_ip(self._esp.ip_address)
        self._logger.info("Connected to WIFI! Got IP: {}".format(ip))

    # Internal setup methods.
    def _setup_wifi(self):
        if self._wifihw == 'esp32':
            self._logger.info("Network: Configuring Native ESP32...")
            self._wifi = wifi.radio
            self._mac_string = "{:X}{:X}{:X}{:X}{:X}{:X}".\
                format(self._wifi.mac_address[0], self._wifi.mac_address[1], self._wifi.mac_address[2],
                       self._wifi.mac_address[3], self._wifi.mac_address[4], self._wifi.mac_address[5])
            # Set the hostname
            # self._wifi.hostname(self._system_name)
        if self._wifihw == 'esp32spi':
            # See if the board has pins defined for an ESP32 coprocessor. If so, we use the ESP32SPI library.
            # Tested on the Metro M4 Airlift.
            self._logger.info("Network: Configuring ESP32 Co-Processor...")
            try:
                esp32_cs = DigitalInOut(board.ESP_CS)
                esp32_ready = DigitalInOut(board.ESP_BUSY)
                esp32_reset = DigitalInOut(board.ESP_RESET)
                spi = busio.SPI(board.SCK, board.MOSI, board.MISO)
                self._esp = adafruit_esp32spi.ESP_SPIcontrol(spi, esp32_cs, esp32_ready, esp32_reset)
            except AttributeError as e:
                self._logger.error("Network: ESP32 Co-Processor not defined.")
                self._logger.error(str(e))
            else:
                # Define the ESP controls
                # Define the ESP controls
                if self._esp.status == adafruit_esp32spi.WL_IDLE_STATUS:
                    self._logger.info("Network: ESP32 co-processor found and idle.")
                else:
                    self._logger.warning("Network: ESP32 co-processor busy. Resetting!")
                    supervisor.reload()
                time.sleep(5)
                self._logger.info("Network: ESP32 Firmware version is '{}.{}.{}'".format(
                     self._esp.firmware_version[0], self._esp.firmware_version[1], self._esp.firmware_version[2]))
                self._mac_string = "{:X}{:X}{:X}{:X}{:X}{:X}".format(
                    self._esp.MAC_address[5], self._esp.MAC_address[4], self._esp.MAC_address[3],
                    self._esp.MAC_address[2], self._esp.MAC_address[1], self._esp.MAC_address[0])
                # Set the hostname
                self._esp.set_hostname(self._system_id)
                self._logger.info("Network: Set hostname to '{}'".format(self._system_id))

        self._logger.info("Network: WiFi MAC address: {}".format(self._mac_string))
        self._logger.info("Network: Hardware initialization complete.")

    # Method to set up MiniMQTT
    def _setup_mini_mqtt(self):
        # Set the socket if we're on a CircuitPython board.
        if os.uname().sysname.lower() != 'linux':
            if self._wifihw == 'esp32':
                self._logger.info("Configuring MiniMQTT for ESP32")
                pool = socketpool.SocketPool(wifi.radio)
                # Create the MQTT object.
                self._mqtt_client = af_mqtt.MQTT(
                    broker=self._broker,
                    port=self._mqtt_port,
                    username=self._mqtt_username,
                    password=self._mqtt_password,
                    socket_pool=pool,
                    socket_timeout=1
                )
            elif self._wifihw == 'esp32spi':
                self._logger.info("Configuring MiniMQTT for ESP32 co-processor")
                af_mqtt.set_socket(socket, self._esp)
                # Create the MQTT object.
                self._mqtt_client = af_mqtt.MQTT(
                    broker=self._broker,
                    port=self._mqtt_port,
                    username=self._mqtt_username,
                    password=self._mqtt_password,
                    socket_pool=socket,
                    socket_timeout=1
                )
        # Enable the MQTT logger.
        # self._mqtt_logger = self._mqtt_client.enable_logger(adafruit_logging, log_level=adafruit_logging.DEBUG,
        #                                                     logger_name="MQTT")
        # Set the last will
        self._mqtt_client.will_set(topic=self._topics_outbound['connectivity']['topic'], payload='offline', retain=True)
        # Connect base callbacks.
        self._mqtt_client.on_connect = self._cb_connected
        self._mqtt_client.on_disconnect = self._cb_disconnected

    def _set_indicator(self, status):
        if self._led_neton is not None and self._led_netoff is not None:
            if status == 'on':
                self._led_netoff.value = False
                self._led_neton.value = True
            elif status == 'off':
                self._led_neton.value = False
                self._led_netoff.value = True

    def _cb_connected(self, client, userdata, flags, rc):
        self._logger.info("Network: MQTT connection successful.")
        # Turn the indicator LED on.
        self._set_indicator("on")
        # Send online message.
        self.publish('connectivity', 'online')
        # Publish all registered item statuses.
        self._logger.debug("Network: Publishing outbound statuses, if any.")
        self._publish_outbound()

    # Callback to catch MQTT disconnections.
    # Used to log and set the flag for the main loop logic.
    def _cb_disconnected(self, client, userdata, rc):
        self._logger.warning("Network: Disconnected from MQTT!")
        self._set_indicator("off")
        self._topics_outbound['connectivity']['previous_value'] = 'offline'

    # System command callback.
    def _cb_syscmd(self, client, topic, message):
        """
        Take callbacks for system commands.

        :param client:
        :param topic:
        :param message:
        :return:
        """
        # Convert the message payload (which is binary) to a string.
        self._logger.debug("Network: Received system command '{}'".format(message))
        valid_values = ['rediscover', 'restart', 'dumpconfig']
        # If it's not a valid option, just ignore it.
        if message.lower() not in valid_values:
            self._logger.warning("Network: Received invalid system command '{}'. Ignoring.".format(message))
        else:
            if message == 'rediscover':
                self._logger.info("Network: Rerunning Home Assistant discovery.")
                self._ha_discovery()
            elif message == 'restart':
                self._logger.critical("Network: Restart requested! Restarting in 5s!")
                time.sleep(5)
                if os.uname().sysname.lower() != 'linux':
                    supervisor.reload()
                else:
                    sys.exit(0)
            elif message == 'dumpconfig':
                # Dump the JSON straight to the current_config topic. This is only ever sent when requested.
                self._mqtt_client.publish(self._topic_prefix + '/current_config', msg=self._core.current_config(),
                                          retain=False)

    def _publish_outbound(self):
        """
        Publish all outbound values for registered objects.
        :return:
        """
        # Publish current statuses.
        self._logger.debug("Current items in outbound topics: {}".format(self._topics_outbound))
        for outbound in self._topics_outbound:
            self._logger.debug("Sys: Free memory - {}".format(gc.mem_free()))
            self._logger.debug("Network: Outbound topic '{}'".format(outbound))
            if 'obj' in self._topics_outbound[outbound] and 'value_attr' in self._topics_outbound[outbound]:
                # If we have an object and value attribute set, retrieve the value and send it.
                # Using getattr this way allows
                self.publish(
                    outbound,
                    getattr(self._topics_outbound[outbound]['obj'], self._topics_outbound[outbound]['value_attr']))
            else:
                self._logger.debug("Network: Outbound topic '{}' is push-only. Skipping.".
                                   format(outbound))

    def publish(self, topic, message):
        self._logger.debug("Network: Publish request on topic '{}' - '{}'".
                           format(self._topics_outbound[topic]['topic'], message))
        self._logger.debug("Network: Message type is '{}'".format(type(message)))
        # If message value hasn't changed, check if we should send anyway.
        publish = True
        if message == self._topics_outbound[topic]['previous_value']:
            publish = False
            now_time = time.monotonic()
            if now_time - self._topics_outbound[topic]["discovery_time"] < self._topics_outbound[topic][
                    "publish_after_discovery"]:
                self._logger.debug("Network: Discovery time was {}, time now is {}. Difference is {}".format(
                    self._topics_outbound[topic]["discovery_time"], now_time,
                    now_time - self._topics_outbound[topic]["discovery_time"]
                ))
                publish = True
            if self._topics_outbound[topic]['repeat']:
                self._logger.debug("Network: Repeat set true, forcing publish.")
                publish = True

        if not publish:
            return

        self._logger.debug("Network: Publishing...")
        # Roll over the value.
        try:
            self._mqtt_client.publish(self._topics_outbound[topic]['topic'], message,
                                      self._topics_outbound[topic]['retain'])
        except (ConnectionError, OSError) as e:
            self._logger.error("Could not publish due to an error ({}). Had attempted to publish '{}' to '{}'".
                               format(e, message, self._topics_outbound[topic]['topic']))
            # Presumably, any failure to publish means we're not connected, so set MQTT Connected to false.
            self._mqtt_connected = False
        else:
            self._topics_outbound[topic]['previous_value'] = message

    # Set up a new control or script
    def add_item(self, input_obj):
        self._logger.debug("Network: Adding item to Network handler of type: {}".format(type(input_obj)))
        # Some slight differentiation between controls and scripts.
        # Separate topic prefixes to keep them clear.
        # Different callback organization. Controls will get direct callbacks, since they're quick.
        # Scripts get managed through the core run loop, which keeps nesting under control.
        if issubclass(type(input_obj), brickmaster2.controls.Control):
            self._topics_outbound[input_obj.id] = {}
            prefix = self._topic_prefix + '/' + "controls"
            callback = input_obj.callback
            if self._ha_discover:
                self._logger.info("Network: Sending HA discovery for item '{}' ({})".
                                  format(input_obj.name, input_obj.id))
                if isinstance(input_obj, brickmaster2.controls.CtrlGPIO) and self._mqtt_client.is_connected():
                    self._ha_discovery_gpio(input_obj)
        elif isinstance(input_obj, brickmaster2.scripts.BM2Script):
            self._topics_outbound[input_obj.id] = {}
            prefix = self._topic_prefix + '/' + "scripts"
            callback = self._core.callback_scr
        else:
            raise TypeError("Network: Handler cannot add object of type {}".format(type(input_obj)))
        # Add the topics which need to be listened to.
        outbound_topics = []
        inbound_topics = []
        self._logger.debug("{}".format(input_obj.topics))
        for item in input_obj.topics:
            if item['type'] == 'outbound':
                outbound_topics.append(item)
            elif item['type'] == 'inbound':
                inbound_topics.append(item)
        self._logger.debug("Outbound topics: {}".format(outbound_topics))
        self._logger.debug("Inbound topics: {}".format(inbound_topics))
        # Process the outbound topics. This sends out control status before we subscribe so external systems (eg: Home
        # Assistant) have an initial status.
        for obj_topic in outbound_topics:
            self._logger.debug("Network: Processing outbound topic '{}'".format(prefix + '/' + obj_topic['topic']))
            # Copy the topic dict.
            self._topics_outbound[input_obj.id] = obj_topic
            # Extend the topic.
            self._topics_outbound[input_obj.id]['topic'] = prefix + '/' + self._topics_outbound[input_obj.id]['topic']
            # Initialize the previous publication keys.
            self._topics_outbound[input_obj.id]['previous_value'] = None
            self._topics_outbound[input_obj.id]['discovery_time'] = 0
            self._logger.debug("Network: Outbound topic dict '{}'".format(self._topics_outbound[input_obj.id]))

            if self._mqtt_client.is_connected():
                self.publish(input_obj.id, getattr(self._topics_outbound[input_obj.id]['obj'],
                                                   self._topics_outbound[input_obj.id]['value_attr']))
        # Process the inbound topics. This creates subscriptions and connects callbacks for those subscribed topics
        # to the control objects callback attribute.
        for obj_topic in inbound_topics:
            tgt_topic = prefix + '/' + obj_topic['topic']
            self._logger.debug("Network: Processing inbound topic '{}'".format(tgt_topic))
            self._topics_inbound.append({'topic': tgt_topic, 'callback': callback})
            # Subscribe to this new topic, specifically.
            try:
                self._mqtt_client.subscribe(tgt_topic)
            except af_mqtt.MMQTTException:
                self._logger.error("Network: Could not subscribe to topic '{}'".format(tgt_topic))
            else:
                self._mqtt_client.add_topic_callback(tgt_topic, callback)

    # Create JSON for memory information topic
    @staticmethod
    def _meminfo():
        return_dict = {
            'mem_free': gc.mem_free(),
            'mem_used': gc.mem_alloc()
        }
        return_dict['mem_total'] = return_dict['mem_used'] + return_dict['mem_free']
        return_dict['pct_free'] = "{:0.2f}".format((return_dict['mem_free'] / return_dict['mem_total']) * 100)
        return_dict['pct_used'] = "{:0.2f}".format((return_dict['mem_used'] / return_dict['mem_total']) * 100)
        return_json = json.dumps(return_dict)
        return return_json

    # HA Discovery
    def _ha_discovery(self):
        """
        Run discovery for everything.
        :return:
        """
        # Set up the Connectivity entities.
        self._ha_discovery_connectivity()
        # Set up the Memory Info entities.
        self._ha_discovery_meminfo()

        # The outbound topics dict includes references to the objects, so we can get the objects from there.
        for item in self._topics_outbound:
            if isinstance(self._topics_outbound[item]['obj'], brickmaster2.controls.CtrlGPIO):
                self._ha_discovery_gpio(self._topics_outbound[item]['obj'])

    def _ha_discovery_connectivity(self):
        """
        Create Home Assistant discovery message for system connectivity

        :return:
        """
        discovery_dict = {
            'name': "Connectivity",
            'object_id': self._system_id + "_connectivity",
            'device': self._ha_device_info,
            'device_class': 'connectivity',
            'unique_id': self._mac_string + "_connectivity",
            'state_topic': self._topic_prefix + '/connectivity',
            'payload_on': 'online',
            'payload_off': 'offline'
        }
        discovery_json = json.dumps(discovery_dict)
        # Publish it!
        discovery_topic = self._ha_base + '/binary_sensor/' + 'bm2_' + self._mac_string + '/connectivity/config'
        self._mqtt_client.publish(discovery_topic, discovery_json, True)
        self._topics_outbound['connectivity']['discovery_time'] = time.monotonic()

    def _ha_discovery_meminfo(self):
        """
        Create Home Assistant discovery message for free memory.

        :return: None
        """
        # Define all the entity options, then send based on what's been configured.

        # Memfreepct
        memfreepct_dict = {
            'name': "Memory Available (Pct)",
            'object_id': self._system_id + "_memfreepct",
            'device': self._ha_device_info,
            'unique_id': self._mac_string + "_memfreepct",
            'state_topic': self._topic_prefix + '/meminfo',
            'unit_of_measurement': '%',
            'value_template': '{{ value_json.pct_free }}',
            'icon': 'mdi:memory',
            'availability_topic': self._topic_prefix + '/connectivity'
        }
        memusedpct_dict = {
            'name': "Memory Used (Pct)",
            'object_id': self._system_id + "_memusedpct",
            'device': self._ha_device_info,
            'unique_id': self._mac_string + "_memusedpct",
            'state_topic': self._topic_prefix + '/meminfo',
            'unit_of_measurement': '%',
            'value_template': '{{ value_json.pct_used }}',
            'icon': 'mdi:memory',
            'availability_topic': self._topic_prefix + '/connectivity'
        }
        memfreebytes_dict = {
            'name': "Memory Available (Bytes)",
            'object_id': self._system_id + "_memfree",
            'device': self._ha_device_info,
            'unique_id': self._mac_string + "_memfree",
            'state_topic': self._topic_prefix + '/meminfo',
            'unit_of_measurement': 'B',
            'value_template': '{{ value_json.mem_free }}',
            'icon': 'mdi:memory',
            'availability_topic': self._topic_prefix + '/connectivity'
        }
        memusedbytes_dict = {
            'name': "Memory Used (Bytes)",
            'object_id': self._system_id + "_memusedpct",
            'device': self._ha_device_info,
            'unique_id': self._mac_string + "_memusedpct",
            'state_topic': self._topic_prefix + '/meminfo',
            'unit_of_measurement': 'B',
            'value_template': '{{ value_json.mem_used }}',
            'icon': 'mdi:memory',
            'availability_topic': self._topic_prefix + '/connectivity'
        }

        if self._ha_meminfo == 'unified':
            # Unified just sets up Memory, Percent Free. Add in the other memory info as JSON attributes.
            memfreepct_dict['json_attributes_topic'] = self._topic_prefix + '/meminfo'
            self._mqtt_client.publish(self._ha_base + '/sensor/' + 'bm2_' + self._mac_string + '/memfreepct/config',
                                      json.dumps(memfreepct_dict), True)
        elif self._ha_meminfo == 'unified-used':
            memusedpct_dict['json_attributes_topic'] = self._topic_prefix + '/meminfo'
            self._mqtt_client.publish(self._ha_base + '/sensor/' + 'bm2_' + self._mac_string + '/memusedpct/config',
                                      json.dumps(memusedpct_dict), True)
        elif self._ha_meminfo == 'split-pct':
            # When providing separate memory percentages, add JSON attributes on free or used.
            memfreepct_dict['json_attributes_topic'] = self._topic_prefix + '/meminfo'
            memfreepct_dict['json_attributes_template'] = \
                "{{ {'mem_free': value_json.mem_free, 'mem_total': value_json.mem_total} | tojson }}"
            self._mqtt_client.publish(self._ha_base + '/sensor/' + 'bm2_' + self._mac_string + '/memfreepct/config',
                                      json.dumps(memfreepct_dict), True)
            memusedpct_dict['json_attributes_topic'] = self._topic_prefix + '/meminfo'
            memusedpct_dict['json_attributes_template'] = \
                "{{ {'mem_used': value_json.mem_used, 'mem_total': value_json.mem_total} | tojson }}"
            self._mqtt_client.publish(self._ha_base + '/sensor/' + 'bm2_' + self._mac_string + '/memusedpct/config',
                                      json.dumps(memusedpct_dict), True)
        elif self._ha_meminfo == 'split-all':
            # If we're splitting everything, we don't need to add JSON attributes.
            self._mqtt_client.publish(self._ha_base + '/sensor/' + 'bm2_' + self._mac_string + '/memfreepct/config',
                                      json.dumps(memfreepct_dict), True)
            self._mqtt_client.publish(self._ha_base + '/sensor/' + 'bm2_' + self._mac_string + '/memusedpct/config',
                                      json.dumps(memusedpct_dict), True)
            self._mqtt_client.publish(self._ha_base + '/sensor/' + 'bm2_' + self._system_id + '/memfreebytes/config',
                                      json.dumps(memfreebytes_dict), True)
            self._mqtt_client.publish(self._ha_base + '/sensor/' + 'bm2_' + self._mac_string + '/memusedbytes/config',
                                      json.dumps(memusedbytes_dict), True)
        self._topics_outbound['meminfo']['discovery_time'] = time.monotonic()

    def _ha_discovery_gpio(self, gpio_control):
        """
        Create Home Assistant discovery message for GPIO Control.

        :param gpio_control:
        :return:
        """
        discovery_dict = {
            'name': gpio_control.name,
            'object_id': self._system_id + "_" + gpio_control.id,
            'device': self._ha_device_info,
            'icon': gpio_control.icon,
            'unique_id': self._mac_string + "_" + gpio_control.id,
            'command_topic': self._topic_prefix + '/controls/' + gpio_control.id + '/set',
            'state_topic': self._topic_prefix + '/controls/' + gpio_control.id + '/status',
            'availability_topic': self._topic_prefix + '/connectivity'
        }
        discovery_json = json.dumps(discovery_dict)
        # Publish it!
        discovery_topic = self._ha_base + '/switch/' + 'bm2_' + self._mac_string + '/' + gpio_control.id + '/config'
        self._mqtt_client.publish(discovery_topic, discovery_json, True)
        self._topics_outbound[gpio_control.id]['discovery_time'] = time.monotonic()

    @property
    def _ha_device_info(self):
        """
        Generate device info for Home Assistant discovery
        :return:
        """
        return_dict = {
            'name': self._system_name,
            'identifiers': [self._mac_string],
            'manufacturer': "ConHugeCo",
            'model': "BrickMaster Lego Control",
            'sw_version': brickmaster2.version.__version__
        }
        if self._ha_area is not None:
            return_dict['suggested_area'] = self._ha_area
        return return_dict
