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
import adafruit_minimqtt.adafruit_minimqtt as af_MQTT
# from adafruit_datetime import datetime
import brickmaster2.scripts
import brickmaster2.controls
import gc
import supervisor


class BM2Network:
    def __init__(self, core, id, name, broker, mqtt_username, mqtt_password, SSID=None, password=None, net_on=None,
                 net_off=None, port=1883, ha_discover=False, ha_base='homeassistant', ha_area=None, ha_meminfo='unified',
                 **kwargs):

        self._system_name = name
        self._system_id = id
        self._broker = broker
        self._mqtt_port = port
        self._mqtt_username = mqtt_username
        self._mqtt_password = mqtt_password
        self._ssid = SSID
        self._ssid_password = password
        self._ha_discover = ha_discover
        self._ha_base = ha_base
        self._ha_area = ha_area
        self._ha_meminfo = ha_meminfo

        # Save a reference to the core. This allows callbacks to the core.
        self._core = core
        self._logger = adafruit_logging.getLogger('BrickMaster2')
        # Log some things, if we want.
        self._logger.info("Network System Name: {}".format(self._system_name))
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
        if os.uname().sysname.lower() != 'linux':
            # Conditionally import to global.
            global adafruit_esp32spi
            global socket
            # global rtc
            from adafruit_esp32spi import adafruit_esp32spi
            import adafruit_esp32spi.adafruit_esp32spi_socket as socket
            # import rtc
            # Connect to the network
            self._setup_wifi()
            self._connect_wifi()
            self._clock_set = False
            self._clock_last_set = 0
            # self._set_clock()
        else:
            global socket
            import socket
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
                'discovery_time': 0,
                'obj': None # No object, but include this to prevent breakage.
            },
            'meminfo': {
              'topic': self._topic_prefix + '/meminfo',
              'repeat': False,
              'retain': False,
              'previous_value': 'Unknown',
              'publish_after_discovery': 1,
              'discovery_time': 0,
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
                'discovery_time': 0
            }
        }

        # Topics for discovery.
        self._topics_discovery = {}
        # Set up initial MQTT tracking values.
        self._mqtt_timeouts = 0
        self._reconnect_timestamp = time.monotonic()
        self._setup_mini_mqtt()
        # MQTT is set up, now connect.
        self._connect_mqtt()
        self._logger.info("Network: Initializiation complete.")

    # Main polling loop. This gets called by the main system run loop when it's time to poll the network.
    def poll(self):
        # self._logger.debug("Network: Poll Called")
        # Do an NTP update.
        # if os.uname().sysname.lower() != 'linux':
        #     if not self._clock_set:
        #         if time.monotonic() - self._clock_last_set > 15:
        #             self._logger.info("Network: Trying to set clock.")
        #             self._set_clock()
        #             self._clock_last_set = time.monotonic()
        #     else:
        #         if time.monotonic() - self._clock_last_set > 43200:
        #             self._logger.debug("Network: Resetting clock after 12 hours.")
        #             self._set_clock()
        #             self._clock_last_set = time.monotonic()

        # Check to see if the MQTT client is connected.
        # If we need to reconnect do it. If that fails, we'll return here, since everything past this is MQTT related.
        # self._logger.debug("Network: Checking MQTT connectivity.")
        if not self._mqtt_client.is_connected():
            self._logger.info("Network: MQTT not connected.")
            try_reconnect = False
            # Has is been 30s since the previous attempt?
            if time.monotonic() - self._reconnect_timestamp > 30:
                self._logger.info("Network: Attempting MQTT reconnect...")
                self._reconnect_timestamp = time.monotonic()
                # If MQTT isn't connected, nothing else to do.
                if not self._connect_mqtt():
                    self._logger.warning("Network: MQTT not reconnected!")
                    return
            else:
                return
        else:
            self._logger.debug("Network: MQTT connected. Continuing.")

        try:
            timeout = 0.25
            self._logger.debug("Network: Polling MQTT Broker. Timeout is {}s".format(timeout))
            self._mqtt_client.loop(timeout=timeout)
        except af_MQTT.MMQTTException:
            self._logger.warning("Network: MQTT poll timed out.")
            self._logger.debug("Network MQTT connection state: {}".format(self._mqtt_client.is_connected()))
            return

        # Publish an online message.
        self._publish('connectivity', 'online')
        # Publish memory stats.
        self._publish('meminfo', self._meminfo())

        # Publish any outbound topics.
        self._publish_outbound()
        # Garbage collect.
        gc.collect()

    # Connect to the MQTT broker.
    def _connect_mqtt(self):
        try:
            self._mqtt_client.connect(host=self._broker, port=self._mqtt_port)
        except Exception as e:
            self._logger.warning('Network: Could not connect to MQTT broker.')
            self._logger.warning('Network: ' + str(e))
            self._set_indicator("off")
            return False
        else:
            self._set_indicator("on")

        # Subscribe to the system command topic.
        try:
            self._mqtt_client.subscribe(self._topic_prefix + '/syscmd')
        except af_MQTT.MMQTTException:
            self._logger.error("Network: Could not subscribe to system command topic '{}'".
                               format(self._topic_prefix + '/syscmd'))
        else:
            self._mqtt_client.add_topic_callback(self._topic_prefix + '/syscmd', self._cb_syscmd)


        # Send a discovery message and an online notification.
        if self._ha_discover:
             self._ha_discovery()

        # # Send the online notification.
        self._publish('connectivity', 'online')
        # Publish all the topics.
        self._publish_outbound()
        return True

    def _connect_wifi(self):
        # Try to do the connection
        while not self._esp.is_connected:
            self._set_indicator("off")
            try:
                self._esp.connect_AP(self._ssid, self._ssid_password)
            except OSError as e:
                self._logger.warning("Network: Could not connect to WIFI SSID {}. Retrying in 30s.".format(self._ssid))
                time.sleep(30)
                continue

    # Internal setup methods.
    def _setup_wifi(self):
        self._logger.info("Network: Connecting to WIFI SSID {}".format(self._ssid))

        # Set up the ESP32 connections
        esp32_cs = DigitalInOut(board.ESP_CS)
        esp32_ready = DigitalInOut(board.ESP_BUSY)
        esp32_reset = DigitalInOut(board.ESP_RESET)
        # Define the ESP controls
        spi = busio.SPI(board.SCK, board.MOSI, board.MISO)
        self._esp = adafruit_esp32spi.ESP_SPIcontrol(spi, esp32_cs, esp32_ready, esp32_reset)

        if self._esp.status == adafruit_esp32spi.WL_IDLE_STATUS:
            self._logger.info("Network: ESP32 found and idle.")
        # self._logger.info("ESP32 Firmware version: {}.{}.{}".format(
        #     self._esp.firmware_version[0],self._esp.firmware_version[1],self._esp.firmware_version[2]))
        self._mac_string = "{:X}:{:X}:{:X}:{:X}:{:X}:{:X}".format(
            self._esp.MAC_address[5], self._esp.MAC_address[4], self._esp.MAC_address[3], self._esp.MAC_address[2],
            self._esp.MAC_address[1],
            self._esp.MAC_address[0], )
        self._logger.info("Network: ESP32 MAC address: {}".format(self._mac_string))

    # Method to setup as MiniMQTT
    def _setup_mini_mqtt(self):
        # Set the socket if we're on a CircuitPython board.
        if os.uname().sysname.lower() != 'linux':
            af_MQTT.set_socket(socket, self._esp)
        # Create the MQTT object.
        self._mqtt_client = af_MQTT.MQTT(
            broker=self._broker,
            port=self._mqtt_port,
            username=self._mqtt_username,
            password=self._mqtt_password,
            socket_pool=socket,
            socket_timeout=1
        )
        # Enable the MQTT logger.
        # self._mqtt_logger = self._mqtt_client.enable_logger(adafruit_logging, log_level=adafruit_logging.DEBUG, logger_name="MQTT")
        # Set the last will
        self._mqtt_client.will_set(topic=self._topics_outbound['connectivity']['topic'], payload='offline', retain=True)
        # Connect base callbacks.
        self._mqtt_client.on_connect = self._cb_connected
        self._mqtt_client.on_disconnect = self._cb_disconnected

    # def _set_clock(self):
    #     try:
    #         esp_time = self._esp.get_time()
    #     except OSError:
    #         self._logger.warning("Network: Failed to fetch time. Retry in 15s.")
    #         self._clock_set = False
    #         return
    #     else:
    #         rtc.RTC().datetime = datetime.fromtimestamp(esp_time[0]).timetuple()
    #         dt = rtc.RTC().datetime
    #         # (tm_year=2023, tm_mon=6, tm_mday=3, tm_hour=11, tm_min=34, tm_sec=55, tm_wday=5, tm_yday=154, tm_isdst=-1)
    #         self._logger.info("Network: Updated time from network. New time: {}/{}/{} {}:{}:{}".
    #                           format(dt.tm_mday, dt.tm_mon, dt.tm_year, dt.tm_hour, dt.tm_min, dt.tm_sec))
    #         self._clock_last_set = time.monotonic()
    #         self._clock_set = True

    def _set_indicator(self, status):
        if self._led_neton is not None and self._led_netoff is not None:
            if status == 'on':
                self._led_netoff.value = False
                self._led_neton.value = True
            elif status == 'off':
                self._led_neton.value = False
                self._led_netoff.value = True

    def _cb_connected(self, client, userdata, flags, rc):
        self._logger.info("Network: Connection callback called.")
        # Turn the indicator LED on.
        self._set_indicator("on")
        # Subscribe to the appropriate topics.
        # for control in self._topics_inbound:
        #     self._mqtt_client.subscribe(control['topic'])
        #     self._mqtt_client.add_topic_callback(control['topic'], control['callback'])
        # Send online message.
        self._publish('connectivity', 'online')
        # Publish all registered item statuses.
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
        valid_values = ['rediscover', 'reset']
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
                    supervisor.reset()
                else:
                    sys.exit(0)

    def _publish_outbound(self):
        """
        Publish all outbound values for registered objects.
        :return:
        """
        # Publish current statuses.
        self._logger.debug("Network: Publishing outbound topics.")
        for outbound in self._topics_outbound:
            self._logger.debug("Network: Outbound topic '{}'".format(outbound))
            if 'obj' in self._topics_outbound[outbound] and 'value_attr' in self._topics_outbound[outbound]:
                # If we have an object and value attribute set, retrieve the value and send it.
                # Using getattr this way allows
                self._publish(
                    outbound,
                    getattr(self._topics_outbound[outbound]['obj'], self._topics_outbound[outbound]['value_attr']))
            else:
                self._logger.debug("Network: No object or attribute value. Skipping.")

    def _publish(self, topic, message):
        self._logger.debug("Network: Publish request on topic '{}' - '{}'".
                           format(self._topics_outbound[topic]['topic'], message))
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
        except ConnectionError:
            self._logger.error("Could not publish due to connection error.")
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
                self._logger.info("Network: Sending HA discovery for item '{}' ({})".format(input_obj.name, input_obj.id))
                if isinstance(input_obj, brickmaster2.controls.CtrlGPIO):
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
                self._publish(input_obj.id, getattr(self._topics_outbound[input_obj.id]['obj'],
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
            except af_MQTT.MMQTTException:
                self._logger.error("Network: Could not subscribe to topic '{}'".format(tgt_topic))
            else:
                self._mqtt_client.add_topic_callback(tgt_topic, callback)

    # Create JSON for memory information topic
    def _meminfo(self):
        return_dict = {
            'mem_free': gc.mem_free(),
            'mem_used': gc.mem_alloc()
        }
        return_dict['mem_total'] = return_dict['mem_used'] + return_dict['mem_free']
        return_dict['pct_free'] = "{:0.2f}".format((return_dict['mem_free'] / return_dict['mem_total'] ) * 100)
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
            if isinstance(self._topics_outbound[item]['obj'],brickmaster2.controls.CtrlGPIO):
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
        discovery_topic = self._ha_base + '/binary_sensor/' + self._system_id + '/connectivity/config'
        self._mqtt_client.publish(discovery_topic, discovery_json, False)
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
            self._mqtt_client.publish(self._ha_base + '/sensor/' + self._system_id + '/memfreepct/config', json.dumps(memfreepct_dict), False)
        elif self._ha_meminfo == 'unified-used':
            memusedpct_dict['json_attributes_topic'] = self._topic_prefix + '/meminfo'
            self._mqtt_client.publish(self._ha_base + '/sensor/' + self._system_id + '/memusedpct/config', json.dumps(memusedpct_dict), False)
        elif self._ha_meminfo == 'split-pct':
            # When providing separate memory percentages, add JSON attributes on free or used.
            memfreepct_dict['json_attributes_topic'] = self._topic_prefix + '/meminfo'
            memfreepct_dict['json_attributes_template'] = \
                "{{ {'mem_free': value_json.mem_free, 'mem_total': value_json.mem_total} | tojson }}"
            self._mqtt_client.publish(self._ha_base + '/sensor/' + self._system_id + '/memfreepct/config', json.dumps(memfreepct_dict), False)
            memusedpct_dict['json_attributes_topic'] = self._topic_prefix + '/meminfo'
            memusedpct_dict['json_attributes_template'] = \
                "{{ {'mem_used': value_json.mem_used, 'mem_total': value_json.mem_total} | tojson }}"
            self._mqtt_client.publish(self._ha_base + '/sensor/' + self._system_id + '/memusedpct/config', json.dumps(memusedpct_dict), False)
        elif self._ha_meminfo == 'split-all':
            # If we're splitting everything, we don't need to add JSON attributes.
            self._mqtt_client.publish(self._ha_base + '/sensor/' + self._system_id + '/memfreepct/config', json.dumps(memfreepct_dict), False)
            self._mqtt_client.publish(self._ha_base + '/sensor/' + self._system_id + '/memusedpct/config', json.dumps(memusedpct_dict), False)
            self._mqtt_client.publish(self._ha_base + '/sensor/' + self._system_id + '/memfreebytes/config', json.dumps(memfreebytes_dict), False)
            self._mqtt_client.publish(self._ha_base + '/sensor/' + self._system_id + '/memusedbytes/config', json.dumps(memusedbytes_dict), False)
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
            'icon': 'mdi:toy-brick',
            'unique_id': self._mac_string + "_" + gpio_control.id,
            'command_topic': self._topic_prefix + '/controls/' + gpio_control.id + '/set',
            'state_topic': self._topic_prefix + '/controls/' + gpio_control.id + '/status',
            'availability_topic': self._topic_prefix + '/connectivity'
        }
        discovery_json = json.dumps(discovery_dict)
        # Publish it!
        discovery_topic = self._ha_base + '/switch/' + self._system_id + '/' + gpio_control.id + '/config'
        self._mqtt_client.publish(discovery_topic, discovery_json, False)
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
