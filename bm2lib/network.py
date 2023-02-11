# Brickmaster2 Network handling module

import time
import os
import sys
import board
import busio
from digitalio import DigitalInOut
import adafruit_logging as logger
import adafruit_minimqtt.adafruit_minimqtt as MQTT
from adafruit_esp32spi import adafruit_esp32spi
import adafruit_esp32spi.adafruit_esp32spi_socket as socket


class BM2Network:
    def __init__(self, config):
        # Save the config.
        self._config = config
        self._logger = logger.getLogger('BrickMaster2')
        self._logger.debug("Initializing network...")
        self._topic_prefix = "brickmaster2/" + self._config['name']

        # If not on a general-purpose system, set up WIFI.
        if os.uname().sysname.lower() != 'linux':
            # Connect to the network
            self._setup_wifi()
            # Set up NTP. The method checks to see if inernal NTP client is needed.
            # self._setup_ntp()
        # Initialize MQTT topic variables.
        # Inbound starts empty and will be expanded as controls are added.
        self._topics_inbound = []
        # Outbound we start with only the general connectivity topic.
        self._topics_outbound = {
            'connectivity': {
                'topic': self._topic_prefix + '/connectivity',
                'retain': True
            }
        }
        self._setup_mqtt()

    # Main polling loop. This gets called by the main system run loop when it's time to poll the network.
    def poll(self):
        # Do an NTP update.
        # self._set_clock()
        self._logger.debug("Polling MQTT")
        self._mqtt.loop(timeout=1)
        self._logger.debug("Poll complete.")

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

        # Try to do the connection
        i = 0
        while not self._esp.is_connected:
            try:
                self._esp.connect_AP(self._config['SSID'], self._config['password'])
            except OSError as e:
                if i == 4:
                    self._logger.critical("Could not connect to network after five attempts! Halting!")
                    sys.exit(1)
                else:
                    self._logger.warning("Could not connect to network. Retrying in 30s.")
                    i += 1
                    time.sleep(30)
                    continue

    def _setup_mqtt(self):
        # Set the socket.
        MQTT.set_socket(socket, self._esp)
        # Create the MQTT object.
        self._mqtt = MQTT.MQTT(
            broker=self._config['broker'],
            port=self._config['port'],
            username=self._config['mqtt_username'],
            password=self._config['mqtt_password']
        )
        self._mqtt.enable_logger(logger, logger.DEBUG)

        # Link to the callbacks.
        self._mqtt.on_connect = self._cb_connected
        self._mqtt.on_disconnect = self._cb_disconnected
        self._mqtt.on_message = self._cb_message
        # Assemble topics.

        # Set last will, which is an offline message to the connectivity topic. This must be done prior to connecting.
        self._mqtt.will_set(topic=self._topics_outbound['connectivity']['topic'], payload='offline', retain=True)
        # Connect!
        self._logger.info("Connecting to broker...")
        self._mqtt.connect()

    def _cb_connected(self, client, userdata, flags, rc):
        # Subscribe to the appropriate topics.
        for control in self._topics_inbound:
            self._mqtt.add_topic_callback(control['topic'], control['callback'])
        # Send online message.
        self._publish('connectivity', 'online')

    def _cb_disconnected(self, client, userdata, rc):
        # May add reconnection logic here for cases where the system gets disconnected.
        # For now, do nothing.
        pass

    # Catchall callback message.
    def _cb_message(self, client, topic, message):
        self._logger.debug("Received message on topic {0}: {1}".format(topic, message))

    def _publish(self, topic, message):
        self._logger.debug("Publishing to '{}': '{}'".format(self._topics_outbound[topic]['topic'], message))
        self._mqtt.publish(self._topics_outbound[topic]['topic'], message, self._topics_outbound[topic]['retain'])

    # Set up a new control.
    def add_control(self, control_obj):
        # Add the topics which need to be listened to.
        for control_topic in control_obj.topics:
            if control_topic['type'] == 'inbound':
                self._logger.debug("Adding callback for topic: {}".
                                   format(self._topic_prefix + '/' + control_topic['topic']))
                self._topics_inbound.append(
                    {'topic': self._topic_prefix + '/' + control_topic['topic'], 'callback': control_obj.callback} )
                # Subscribe to this new topic, specifically.
                self._mqtt.add_topic_callback(self._topic_prefix + '/' + control_topic['topic'], control_obj.callback)


