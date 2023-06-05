# Brickmaster2 Network handling module

import time
import os
import sys
import board
import busio
import time

import digitalio
from digitalio import DigitalInOut
import adafruit_logging
import adafruit_minimqtt.adafruit_minimqtt as MQTT
from adafruit_datetime import datetime

import brickmaster2.scripts
import brickmaster2.controls


class BM2Network:
    def __init__(self, core, config):
        # Save the config.
        self._config = config
        # Save a reference to the core. This allows callbacks to the core.
        self._core = core
        self._logger = adafruit_logging.getLogger('BrickMaster2')
        # null_handler = adafruit_logging.NullHandler()
        # self._logger.addHandler(null_handler)
        self._logger.info("Initializing network...")
        self._logger.debug("Received config: {}".format(self._config))
        self._topic_prefix = "brickmaster2/" + self._config['name']

        # Create network status indicator GPIO controls, if defined.
        self._led_neton = None
        self._led_netoff = None
        if self._config['net_on'] is not None:
            self._logger.debug("Network: Net on indicator created")
            self._led_neton = digitalio.DigitalInOut(getattr(board, str(self._config['net_on'])))
            self._led_neton.switch_to_output(value=False)
        if self._config['net_off'] is not None:
            self._logger.debug("Network: Net off indicator created")
            self._led_netoff = digitalio.DigitalInOut(getattr(board, str(self._config['net_off'])))
            self._led_netoff.switch_to_output(value=True)

        # If not on a general-purpose system, set up WIFI.
        if os.uname().sysname.lower() != 'linux':
            # Conditionally import to global.
            global adafruit_esp32spi
            global socket
            global rtc
            from adafruit_esp32spi import adafruit_esp32spi
            import adafruit_esp32spi.adafruit_esp32spi_socket as socket
            import rtc
            # Connect to the network
            self._setup_wifi()
            self._connect_wifi()
            self._clock_set = False
            self._clock_last_set = 0
            self._set_clock()
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
                'repeat': True,
                'retain': True,
                'previous_value': 'Unknown'
            },
            'active_script': {
                'topic': self._topic_prefix + '/active_script',
                'repeat': False,
                'retain': False,
                'obj': self._core,
                'value_attr': 'active_script',
                'previous_value': 'Unknown'
            }
        }
        # Topics for discovery.
        self._topics_discovery = {}
        try:
            self._ha_topic_base = self._config['ha_base']
        except KeyError:
            self._ha_base = 'homeassistant'

        # Set up initial MQTT tracking values.
        self._mqtt_timeouts = 0
        self._reconnect_timestamp = time.monotonic()
        self._setup_mini_mqtt()
        # MQTT is set up, now connect.
        self._connect_mqtt()
        self._logger.info("Network: Initializiation complete.")

    # Main polling loop. This gets called by the main system run loop when it's time to poll the network.
    def poll(self):
        self._logger.debug("Network: Poll Called")
        # Do an NTP update.
        if os.uname().sysname.lower() != 'linux':
            if not self._clock_set:
                if time.monotonic() - self._clock_last_set > 15:
                    self._logger.info("Network: Trying to set clock.")
                    self._set_clock()
                    self._clock_last_set = time.monotonic()
            else:
                if time.monotonic() - self._clock_last_set > 43200:
                    self._logger.debug("Network: Resetting clock after 12 hours.")
                    self._set_clock()
                    self._clock_last_set = time.monotonic()

        # Check to see if the MQTT client is connected.
        # If we need to reconnect do it. If that fails, we'll return here, since everything past this is MQTT related.
        self._logger.debug("Network: Checking MQTT connectivity.")
        if not self._mqtt_client.is_connected():
            self._logger.debug("Network: MQTT not connected.")
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
        except MQTT.MMQTTException:
            self._logger.warning("Network: MQTT poll timed out.")
            self._logger.debug("Network MQTT connection state: {}".format(self._mqtt_client.is_connected()))
            return

        # Publish an online message.
        # self._publish('connectivity', 'online')

        # Publish any outbound topics.
        self._publish_outbound()

    # Connect to the MQTT broker.
    def _connect_mqtt(self):
        try:
            self._mqtt_client.connect(host=self._config['broker'], port=self._config['port'])
        except Exception as e:
            self._logger.warning('Network: Could not connect to MQTT broker.')
            self._logger.warning('Network: ' + str(e))
            self._set_indicator("off")
            return False
        else:
            self._set_indicator("on")

        # Send a discovery message and an online notification.
        # if self._settings['homeassistant']:
        #     self._ha_discovery()

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
                self._esp.connect_AP(self._config['SSID'], self._config['password'])
            except OSError as e:
                self._logger.warning("Network: Could not connect to WIFI SSID {}. Retrying in 30s.".format(self._config['SSID']))
                time.sleep(30)
                continue

    # Internal setup methods.
    def _setup_wifi(self):
        self._logger.info("Network: Connecting to WIFI SSID {}".format(self._config['SSID']))

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
        mac_string = "{:X}:{:X}:{:X}:{:X}:{:X}:{:X}".format(
            self._esp.MAC_address[5], self._esp.MAC_address[4], self._esp.MAC_address[3], self._esp.MAC_address[2],
            self._esp.MAC_address[1],
            self._esp.MAC_address[0], )
        self._logger.info("Network: ESP32 MAC address: {}".format(mac_string))

    # Method to setup as MiniMQTT
    def _setup_mini_mqtt(self):
        # Set the socket if we're on a CircuitPython board.
        if os.uname().sysname.lower() != 'linux':
            MQTT.set_socket(socket, self._esp)
        # Create the MQTT object.
        self._mqtt_client = MQTT.MQTT(
            broker=self._config['broker'],
            port=self._config['port'],
            username=self._config['mqtt_username'],
            password=self._config['mqtt_password'],
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

    def _set_clock(self):
        try:
            esp_time = self._esp.get_time()
        except OSError:
            self._logger.warning("Network: Failed to fetch time. Retry in 15s.")
            self._clock_set = False
            return
        else:
            rtc.RTC().datetime = datetime.fromtimestamp(esp_time[0]).timetuple()
            dt = rtc.RTC().datetime
            # (tm_year=2023, tm_mon=6, tm_mday=3, tm_hour=11, tm_min=34, tm_sec=55, tm_wday=5, tm_yday=154, tm_isdst=-1)
            self._logger.info("Network: Updated time from network. New time: {}/{}/{} {}:{}:{}".
                              format(dt.tm_mday, dt.tm_mon, dt.tm_year, dt.tm_hour, dt.tm_min, dt.tm_sec))
            self._clock_last_set = time.monotonic()
            self._clock_set = True

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


    # Catchall callback message.
    def _cb_message(self, client, topic, message):
        self._logger.debug("Network: Received message on topic {0}: {1}".format(topic, message))

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
        # If repeat is False, check to see if the value has changed.
        if not self._topics_outbound[topic]['repeat']:
            if message == self._topics_outbound[topic]['previous_value']:
                self._logger.debug("Network: No value change. Not publishing.")
                return
        else:
            self._logger.debug("Network: Set to repeat, publishing regardless of value.")

        self._logger.debug("Network: Publishing...")
        # Roll over the value.
        self._topics_outbound[topic]['previous_value'] = message
        self._mqtt_client.publish(self._topics_outbound[topic]['topic'], message,
                                  self._topics_outbound[topic]['retain'])

    # Set up a new control or script
    def add_item(self, input_obj):
        self._logger.debug("Network: Adding item to Network handler of type: {}".format(type(input_obj)))
        # Some slight differentiation between controls and scripts.
        # Separate topic prefixes to keep them clear.
        # Different callback organization. Controls will get direct callbacks, since they're quick.
        # Scripts get managed through the core run loop, which keeps nesting under control.
        if issubclass(type(input_obj), brickmaster2.controls.Control):
            prefix = self._topic_prefix + '/' + "controls"
            callback = input_obj.callback
        elif isinstance(input_obj, brickmaster2.scripts.BM2Script):
            prefix = self._topic_prefix + '/' + "scripts"
            callback = self._core.callback_scr
        else:
            raise TypeError("Network: Handler cannot add object of type {}".format(type(input_obj)))
        # Add the topics which need to be listened to.
        for obj_topic in input_obj.topics:
            # For inbound topics, subscribe and add callback.
            if obj_topic['type'] == 'inbound':
                self._logger.debug("Network: Adding callback for topic: {}".
                                    format(prefix + '/' + obj_topic['topic']))
                self._topics_inbound.append(
                    {'topic': prefix + '/' + obj_topic['topic'], 'callback': callback})
                # Subscribe to this new topic, specifically.
                self._mqtt_client.subscribe(prefix + '/' + obj_topic['topic'])
                self._mqtt_client.add_topic_callback(prefix + '/' + obj_topic['topic'], callback)
            # For outbound topics, add it so status is collected.
            if obj_topic['type'] == 'outbound':
                self._topics_outbound[input_obj.name] = {
                    'topic': prefix + '/' + obj_topic['topic'],
                    'retain': obj_topic['retain'],
                    'repeat': obj_topic['repeat'],
                    'obj': obj_topic['obj'],
                    'value_attr': obj_topic['value_attr'],
                    'previous_value': None
                }
                if self._mqtt_client.is_connected():
                    self._publish(input_obj.name,getattr(self._topics_outbound[input_obj.name]['obj'],
                                                         self._topics_outbound[input_obj.name]['value_attr']))

    # # HA Discovery
    # def _ha_discovery(self):
    #     pass
    #
    # def _ha_discovery_gpio(self, gpio_control):
    #     """
    #     Create Home Assistant discovery messages for GPIO Control.
    #
    #     :param gpio_control:
    #     :return:
    #     """
    #     availability_topic =
    #     topic_base = self._ha_base + '/' + self._config['name'] + '/' + gpio_control.name
    #     object_id = self._config['name'] + "_" + gpio_control.name
    #     payload_available = ""