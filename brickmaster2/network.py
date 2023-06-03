# Brickmaster2 Network handling module

import time
import os
import sys
import board
import busio
import time

import digitalio
from digitalio import DigitalInOut
import adafruit_logging as logger
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
        self._logger = logger.getLogger('BrickMaster2')
        self._logger.info("Initializing network...")
        self._logger.debug("Received config: {}".format(self._config))
        self._topic_prefix = "brickmaster2/" + self._config['name']

        # Create network status indicator GPIO controls, if defined.
        self._led_neton = None
        self._led_netoff = None
        if self._config['net_on'] is not None:
            self._logger.debug("Net on indicator created")
            self._led_neton = digitalio.DigitalInOut(getattr(board, str(self._config['net_on'])))
            self._led_neton.switch_to_output(value=False)
        if self._config['net_off'] is not None:
            self._logger.debug("Net off indicator created")
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
                'repeat': False,
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

        # Set up initial MQTT tracking values.
        self._mqtt_connected = False
        self._mqtt_timeouts = 0
        self._reconnect_timestamp = time.monotonic()
        self._setup_mini_mqtt()
        # MQTT is set up, now connect.
        self._connect_mqtt()

    # Main polling loop. This gets called by the main system run loop when it's time to poll the network.
    def poll(self):
        # Do an NTP update.
        if os.uname().sysname.lower() != 'linux':
            if not self._clock_set:
                if time.monotonic() - self._clock_last_set > 15:
                    self._logger.info("Trying to set clock.")
                    self._set_clock()
                    self._clock_last_set = time.monotonic()
            else:
                if time.monotonic() - self._clock_last_set > 43200:
                    self._logger.debug("Resetting clock after 12 hours.")
                    self._set_clock()
                    self._clock_last_set = time.monotonic()

        # Check to see if the MQTT client is connected.
        # If we need to reconnect do it. If that fails, we'll return here, since everything past this is MQTT related.
        if not self._mqtt_connected:
            try_reconnect = False
            # Has is been 30s since the previous attempt?
            if time.monotonic() - self._reconnect_timestamp > 30:
                self._logger.debug("Attempting MQTT reconnect...")
                self._reconnect_timestamp = time.monotonic()
                # If MQTT isn't connected, nothing else to do.
                if not self._connect_mqtt():
                    self._logger.debug("Not reconnected!")
                    return

        try:
            self._mqtt_client.loop(timeout=1)
        except MQTT.MMQTTException:
            self._logger.warning("MQTT poll timed out.")

        # Publish any outbound topics.
        self._publish_outbound()

    # Connect to the MQTT broker.
    def _connect_mqtt(self):
        # try:
        self._mqtt_client.connect(host=self._config['broker'], port=self._config['port'])
        # except Exception as e:
            # self._logger.warning('Network: Could not connect to MQTT broker.')
            # self._logger.warning('Network: ' + str(e))
            # self._set_indicator("off")
            # self._mqtt_connected = False
            # return False
        # else:
        #     self._set_indicator("on")

        # Send a discovery message and an online notification.
        # if self._settings['homeassistant']:
        #     self._ha_discovery()
        # Set the internal MQTT tracker to True. Surprisingly, the client library doesn't have a way to track this itself!
        # self._mqtt_connected = True
        # # Send the online notification.
        # self._publish('connectivity', 'online')

        return True

    def _connect_wifi(self):
        # Try to do the connection
        while not self._esp.is_connected:
            self._set_indicator("off")
            try:
                self._esp.connect_AP(self._config['SSID'], self._config['password'])
            except OSError as e:
                self._logger.warning("Could not connect to network. Retrying in 30s.")
                time.sleep(30)
                continue

    # Internal setup methods.
    def _setup_wifi(self):
        self._logger.info("Connecting to WIFI SSID {}".format(self._config['SSID']))

        # Set up the ESP32 connections
        esp32_cs = DigitalInOut(board.ESP_CS)
        esp32_ready = DigitalInOut(board.ESP_BUSY)
        esp32_reset = DigitalInOut(board.ESP_RESET)
        # Define the ESP controls
        spi = busio.SPI(board.SCK, board.MOSI, board.MISO)
        self._esp = adafruit_esp32spi.ESP_SPIcontrol(spi, esp32_cs, esp32_ready, esp32_reset)

        if self._esp.status == adafruit_esp32spi.WL_IDLE_STATUS:
            self._logger.info("ESP32 found and idle.")
        # self._logger.info("ESP32 Firmware version: {}.{}.{}".format(
        #     self._esp.firmware_version[0],self._esp.firmware_version[1],self._esp.firmware_version[2]))
        mac_string = "{:X}:{:X}:{:X}:{:X}:{:X}:{:X}".format(
            self._esp.MAC_address[5], self._esp.MAC_address[4], self._esp.MAC_address[3], self._esp.MAC_address[2],
            self._esp.MAC_address[1],
            self._esp.MAC_address[0], )
        self._logger.info("ESP32 MAC address: {}".format(mac_string))

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
        # Set the last will
        self._mqtt_client.will_set(topic=self._topics_outbound['connectivity']['topic'], payload='offline', retain=True)
        # Connect base callbacks.
        self._mqtt_client.on_connect = self._cb_connected
        self._mqtt_client.on_disconnect = self._cb_disconnected

    def _set_clock(self):
        try:
            esp_time = self._esp.get_time()
        except OSError:
            self._logger.warning("Failed to fetch time. Retry in 15s.")
            self._clock_set = False
            return
        else:
            rtc.RTC().datetime = datetime.fromtimestamp(esp_time[0]).timetuple()
            dt = rtc.RTC().datetime
            # (tm_year=2023, tm_mon=6, tm_mday=3, tm_hour=11, tm_min=34, tm_sec=55, tm_wday=5, tm_yday=154, tm_isdst=-1)
            self._logger.info("Updated time from network. New time: {}/{}/{} {}:{}:{}".
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
        self._logger.info("Connection callback called.")
        # Turn the indicator LED on.
        self._set_indicator("on")
        # Subscribe to the appropriate topics.
        # for control in self._topics_inbound:
        #     self._mqtt_client.subscribe(control['topic'])
        #     self._mqtt_client.add_topic_callback(control['topic'], control['callback'])
        # Send online message.
        self._publish('connectivity', 'online')
        # Publish all registered item statuses.
        # self._publish_outbound()

    # Callback to catch MQTT disconnections.
    # Used to log and set the flag for the main loop logic.
    def _cb_disconnected(self, client, userdata, rc):
        self._logger.warning("Disconnected from MQTT!")
        self._set_indicator("off")
        self._mqtt_connected = False

    # Catchall callback message.
    def _cb_message(self, client, topic, message):
        self._logger.debug("Received message on topic {0}: {1}".format(topic, message))

    def _publish_outbound(self):
        """
        Publish all outbound values for registered objects.
        :return:
        """
        # Publish current statuses.
        for outbound in self._topics_outbound:
            if 'obj' in self._topics_outbound[outbound] and 'value_attr' in self._topics_outbound[outbound]:
                # If we have an object and value attribute set, retrieve the value and send it.
                # Using getattr this way allows
                self._publish(
                    outbound,
                    getattr(self._topics_outbound[outbound]['obj'], self._topics_outbound[outbound]['value_attr']))

    def _publish(self, topic, message):
        self._logger.debug("Network: Publish request on topic '{}' - '{}'".
                           format(self._topics_outbound[topic]['topic'], message))
        # Check for value changes.
        publish = False
        # If repeat is False, check to see if the value has changed.
        if not self._topics_outbound[topic]['repeat']:
            if message != self._topics_outbound[topic]['previous_value']:
                publish = True
        else:
            publish = True
        if publish:
            # self._logger.debug("Network: Publishing...")
            # Roll over the value.
            self._topics_outbound[topic]['previous_value'] = message
            self._mqtt_client.publish(self._topics_outbound[topic]['topic'], message,
                                      self._topics_outbound[topic]['retain'])

    # Set up a new control or script
    def add_item(self, input_obj):
        self._logger.debug("Adding item to Network handler of type: {}".format(type(input_obj)))
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
            raise TypeError("Network handler cannot add object of type {}".format(type(input_obj)))
        # Add the topics which need to be listened to.
        for obj_topic in input_obj.topics:
            # For inbound topics, subscribe and add callback.
            if obj_topic['type'] == 'inbound':
                self._logger.debug("Adding callback for topic: {}".
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

