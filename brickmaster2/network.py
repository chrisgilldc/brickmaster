# Brickmaster2 Network handling module

import time
import os
import sys
import board
import busio
import time
from digitalio import DigitalInOut
import adafruit_logging as logger
# import adafruit_minimqtt.adafruit_minimqtt as MQTT
from paho.mqtt.client import Client

import brickmaster2.scripts
import brickmaster2.controls


class BM2Network:
    def __init__(self, core, config):
        # Save the config.
        self._config = config
        # Save a reference to the core. This allows callbacks to the core.
        self._core = core
        self._logger = logger.getLogger('BrickMaster2')
        # self._logger.debug("Initializing network...")
        self._topic_prefix = "brickmaster2/" + self._config['name']

        # If not on a general-purpose system, set up WIFI.
        if os.uname().sysname.lower() != 'linux':
            # Conditionally import to global.
            global adafruit_esp32spi
            global socket
            from adafruit_esp32spi import adafruit_esp32spi
            import adafruit_esp32spi.adafruit_esp32spi_socket as socket
            # Connect to the network
            self._setup_wifi()
            # Set up NTP. The method checks to see if inernal NTP client is needed.
            # self._setup_ntp()
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
        self._reconnect_timestamp = time.monotonic()
        self._setup_mqtt()
        # MQTT is set up, now connect.
        self._connect_mqtt()

    # Main polling loop. This gets called by the main system run loop when it's time to poll the network.
    def poll(self):
        # Do an NTP update.
        # self._set_clock()
        self._mqtt_client.loop(timeout=1)

        # Check to see if the MQTT client is connected. Oddly, Paho doesn't keep its own connection status!
        if not self._mqtt_connected:
            try_reconnect = False
            # Has is been 30s since the previous attempt?
            if time.monotonic() - self._reconnect_timestamp > 30:
                self._reconnect_timestamp = time.monotonic()
                # If MQTT isn't connected, nothing else to do.
                if not self._connect_mqtt():
                    return

        # Publish current statuses.
        for outbound in self._topics_outbound:
            if 'obj' in self._topics_outbound[outbound] and 'value_attr' in self._topics_outbound[outbound]:
                # If we have an object and value attribute set, retrieve the value and send it.
                # Using getattr this way allows
                self._publish(
                    outbound,
                    getattr(self._topics_outbound[outbound]['obj'], self._topics_outbound[outbound]['value_attr']))

    # Connect to the MQTT broker.
    def _connect_mqtt(self):
        # Set the last will prior to connecting.
        self._logger.info("Network: Creating last will.")
        self._mqtt_client.will_set(topic=self._topics_outbound['connectivity']['topic'], payload='offline', retain=True)
        try:
            self._mqtt_client.connect(host=self._config['broker'], port=self._config['port'])
        except Exception as e:
            self._logger.warning('Network: Could not connect to MQTT broker.')
            self._logger.warning('Network: ' + str(e))
            self._mqtt_connected = False
            return False

        # Send a discovery message and an online notification.
        # if self._settings['homeassistant']:
        #     self._ha_discovery()
        # Send the online notification.
        self._publish('connectivity', 'online')
        # Set the internal MQTT tracker to True. Surprisingly, the client doesn't have a way to track this itself!
        self._mqtt_connected = True
        return True

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
        # Create the client.
        # Client ID will be the same as the name. This is *simple* but could be trouble. May need to change to MAC in
        # the future.
        self._mqtt_client = Client(client_id=self._config['name'])
        # Set Username and Password
        self._mqtt_client.username_pw_set(
            username=self._config['mqtt_username'],
            password=self._config['mqtt_password']
        )

        # Link to the callbacks.
        self._mqtt_client.on_connect = self._cb_connected
        self._mqtt_client.on_disconnect = self._cb_disconnected
        self._mqtt_client.on_message = self._cb_message

        # This is the setup for MiniMQTT, not using it now.
        # # Set the socket.
        # MQTT.set_socket(socket, self._esp)
        # # Create the MQTT object.
        # self._mqtt = MQTT.MQTT(
        #     broker=self._config['broker'],
        #     port=self._config['port'],
        #     username=self._config['mqtt_username'],
        #     password=self._config['mqtt_password']
        # )
        # self._mqtt.enable_logger(logger, logger.DEBUG)

    def _cb_connected(self, client, userdata, flags, rc):
        # Subscribe to the appropriate topics.
        for control in self._topics_inbound:
            self._mqtt_client.subscribe(control['topic'])
            self._mqtt_client.message_callback_add(control['topic'], control['callback'])
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
        #self._logger.debug("Network: Publish request on topic '{}' - '{}'".
        #                   format(self._topics_outbound[topic]['topic'], message))
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
        # self._logger.debug("Adding item to Network handler of type: {}".format(type(input_obj)))
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
                # self._logger.debug("Adding callback for topic: {}".
                #                    format(prefix + '/' + obj_topic['topic']))
                # self._logger.debug("Using callback: {}".format(callback))
                self._topics_inbound.append(
                    {'topic': prefix + '/' + obj_topic['topic'], 'callback': callback})
                # Subscribe to this new topic, specifically.
                self._mqtt_client.subscribe(prefix + '/' + obj_topic['topic'])
                self._mqtt_client.message_callback_add(prefix + '/' + obj_topic['topic'], callback)
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
    # Set up a new control.
    # def add_control(self, control_obj):
    #     # Add the topics which need to be listened to.
    #     for control_topic in control_obj.topics:
    #         # For inbound topics, subscribe and add callback.
    #         if control_topic['type'] == 'inbound':
    #             self._logger.debug("Adding callback for topic: {}".
    #                                format(self._topic_prefix + '/' + control_topic['topic']))
    #             self._logger.debug("Using callback: {}".format(control_obj.callback))
    #             self._topics_inbound.append(
    #                 {'topic': self._topic_prefix + '/' + control_topic['topic'], 'callback': control_obj.callback})
    #             # Subscribe to this new topic, specifically.
    #             self._mqtt_client.subscribe(self._topic_prefix + '/' + control_topic['topic'])
    #             self._mqtt_client.message_callback_add(self._topic_prefix + '/' + control_topic['topic'],
    #                                                    control_obj.callback)
    #         # For outbound topics, add it so status is collected.
    #         if control_topic['type'] == 'outbound':
    #             self._topics_outbound[control_obj.name] = {
    #                 'topic': self._topic_prefix + '/' + control_topic['topic'],
    #                 'retain': control_topic['retain'],
    #                 'repeat': control_topic['repeat'],
    #                 'status_obj': control_obj.status,
    #                 'previous_value': None
    #            }
