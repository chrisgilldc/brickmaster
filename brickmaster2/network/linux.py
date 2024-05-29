"""
Brickmaster2 Network for Linux
"""

import adafruit_logging
from json import dumps as json_dumps
import time
from paho.mqtt.client import Client
import brickmaster2
import psutil


class BM2NetworkLinux:
    # # Import the Home Assistant methods.
    # from brickmaster2.network.ha import (_device_info, _ha_discovery, _ha_discovery_connectivity, _ha_discovery_display,
    #                                      _ha_discovery_gpio, _ha_discovery_meminfo)

    def __init__(self, core, system_id, short_name, long_name, broker, mqtt_username, mqtt_password, net_on=None,
                 net_off=None, port=1883, ha_discover=True, ha_base='homeassistant', ha_area=None,
                 ha_meminfo='unified', time_mqtt=False, log_level=None):
        """
        BrickMaster2 Network Class for Linux (and probably other POSIX systems too!)

        :param core: Reference to the main Brickmaster2 object.
        :type core: BrickMaster2
        :param id: ID of the system. Cannot include spaces!
        :type id: str
        :param name: Long name of the system. Used for Home Assistant discovery.
        :type name: str
        :param broker: IP or hostname of the MQTT broker
        :type  broker: str
        :param port: MQTT port to connect to. Defaults to 1883. SSL is *NOT* supported.
        :type port: int
        :param mqtt_username: MQTT Username
        :type mqtt_username: str
        :param mqtt_password: MQTT Password
        :type mqtt_password: str
        :param net_on:
        :param net_off:
        :param ha_discover: Should we send Home Assistant discovery messages?
        :type ha_discover: bool
        :param ha_base: When doing Home Assistant discovery, base topic name?
        :type ha_base: str
        :param ha_area: Area to suggest for entities.
        :type ha_area: str
        :param ha_meminfo: Memory topic format. Must be one of 'unified', 'unified-used', 'split-pct', 'split-all'
        :param time_mqtt: Should we log timings for MQTT polls. Mostly for testing.
        :type time_mqtt: bool
        """

        # Save parameters.
        self._core = core
        self._system_id = system_id
        self._short_name = short_name
        self._long_name = long_name
        self._mqtt_broker = broker
        self._mqtt_port = port
        self._mqtt_username = mqtt_username
        self._mqtt_password = mqtt_password
        # Dict for all the Home Assistant info.
        self._ha_info = {
            'discover': ha_discover,
            'override': False,
            'start': time.monotonic()
        }
        self._ha_discover = ha_discover
        self._ha_base = ha_base
        self._ha_meminfo = ha_meminfo
        self._ha_area = ha_area
        # Register to store objects.
        self._object_register = {
            'controls': {},
            'scripts': {},
            'displays': {}
        }
        #self._unit_system = unit_system
        #self._system_name = system_name
        #self._interface = interface
        # Default the logging level.
        if log_level is None:
            log_level = adafruit_logging.WARNING

        # Set up logger. Adafruit Logging doesn't support hierarchical logging.
        self._logger = adafruit_logging.getLogger('BrickMaster2')
        self._logger.setLevel(log_level)
        self._logger.info("Network System Name: {}".format(self._long_name))

        # Initialize variables
        self._reconnect_timestamp = None
        self._mqtt_connected = False

        # List for commands received and to be passed upward.
        self._upward_commands = []
        # History of payloads, to determine if we need to repeat.
        self._topic_history = {}

        # # Generate device info.
        # self._device_info = brickmaster2.network.ha._device_info(
        #     self._system_id, self._long_name, self._ha_area, brickmaster2.__version__
        # )

        self._logger.info("Defined Client ID: {}".format(self._system_id))

        # Create the MQTT Client.
        self._mqtt_client = Client(
            client_id=self._system_id
        )
        self._mqtt_client.username_pw_set(
            username=self._mqtt_username,
            password=self._mqtt_password
        )
        # Connect MQTT Logger.
        # Uncomment this to get more detailed MQTT logging.
        # self._mqtt_client.enable_logger(self._logger)

        # Connect callback.
        self._mqtt_client.on_connect = self._on_connect
        # Disconnect callback
        self._mqtt_client.on_disconnect = self._on_disconnect

        self._logger.info('Network: Initialization complete.')

    # Registration methods
    def _on_connect(self, userdata, flags, rc, properties=None):
        self._logger.info("Connected to MQTT Broker with result code: {}".format(rc))
        self._mqtt_connected = True

        #TODO: Make sure subscriptions reconnect.
        # Subscribe to the script set topic.
        self._mqtt_client.subscribe('brickmaster2/' + self._short_name + '/script/set')
        self._mqtt_client.message_callback_add('brickmaster2/' + self._short_name + '/script/set',
                                               self._core.callback_scr)
        # Subscribe to the Control topics.
        for control_id in self._object_register['controls']:
            # Subscribe to the topic.
            self._mqtt_client.subscribe('brickmaster2/' + self._short_name + '/controls/' +
                                        self._object_register['controls'][control_id].id + '/set')
            # Connect the callback.
            self._mqtt_client.message_callback_add(
                'brickmaster2/' + self._short_name + '/controls/' +
                self._object_register['controls'][control_id].id + '/set',
                self._object_register['controls'][control_id].callback)

        # Attach the fallback message trapper.
        self._mqtt_client.on_message = self._on_message
        # Send the online message.
        self._send_online()
        # Run Home Assistant Discovery, if enabled.
        if self._ha_discover:
            self._logger.debug("Network: On-Connect running Home Assistant discovery...")
            # Create and stash device info for convenience.
            device_info = brickmaster2.network.mqtt.ha_device_info(self._system_id, self._long_name, self._ha_area,
                                                                 brickmaster2.__version__)
            discovery_messages = brickmaster2.network.mqtt.ha_discovery(
                self._short_name, self._system_id, device_info, 'brickmaster2/', self._ha_base,
                self._ha_meminfo, self._object_register)

            self._logger.debug("Will send discovery messages: {}".format(discovery_messages))
            for discovery_message in discovery_messages:
                self._pub_message(**discovery_message)
            # Reset the topic history so any newly discovered entities get sent to.
            self._topic_history = {}
            # Set the override stamp. This makes sure force repeat is set to send out data after discovery.
            self._ha_info['override'] = True
            self._ha_info['start'] = time.monotonic()

    def _on_disconnect(self, client, userdata, rc):
        if rc != 0:
            self._logger.warning("Unexpected disconnect with code: {}".format(rc))
        self._reconnect_timer = time.monotonic()
        self._mqtt_connected = False

    # Catchall for MQTT messages. Don't act, just log.
    def _on_message(self, client, user, message):
        self._logger.debug("Received message on topic {} with payload {}. No other handler, no action.".format(
            message.topic, message.payload
        ))

    # Message publishing method
    def _pub_message(self, topic, message, force_repeat=False):
        self._logger.debug("Network: Processing message publication on topic '{}'".format(topic))
        # Set the send flag initially. If we've never seen the topic before or we're set to repeat, go ahead and send.
        # This skips some extra logic.
        if topic not in self._topic_history:
            self._logger.debug("Network: Topic not in history, sending...")
            send = True
        elif force_repeat:
            self._logger.debug("Network: Repeat explicitly enabled, sending...")
            send = True
        else:
            send = False

        # If we're not already sending, then we've seen the topic before and should check for changes.
        if send is False:
            previous_message = self._topic_history[topic]
            # Both strings, compare and send if different
            if (isinstance(message, str) and isinstance(previous_message, str)) or \
                    (isinstance(message, (int, float)) and isinstance(previous_message, (int, float))):
                if message != previous_message:
                    self._logger.debug("Message '{}' does not match previous message '{}'. Publishing.".format(message,
                                                                                                               previous_message))
                    send = True
                else:
                    self._logger.debug("Message has not changed, will not publish")
                    return
            # For dictionaries, compare individual elements. This doesn't handle nested dicts, but those aren't used.
            elif isinstance(message, dict) and isinstance(previous_message, dict):
                for item in message:
                    if item not in previous_message:
                        self._logger.debug("Message dict contains new key, publishing.")
                        send = True
                        break
                    if message[item] != previous_message[item]:
                        self._logger.debug("Message dict key '{}' has changed value, publishing.".format(item))
                        send = True
                        break
            # If type has changed, which is odd,  (and it shouldn't, usually), send it.
            elif type(message) != type(previous_message):
                self._logger.debug("Message type has changed from '{}' to '{}'. Unusual, but publishing anyway.".
                                   format(type(previous_message), type(message)))
                send = True

        # If we're sending do it.
        if send:
            self._logger.debug("Publishing message...")
            # New message becomes the previous message.
            self._topic_history[topic] = message
            # Convert the message to JSON if it's a dict, otherwise just send it.
            if isinstance(message, dict):
                outbound_message = json_dumps(message, default=str)
            else:
                outbound_message = message
            self._mqtt_client.publish(topic, outbound_message)

    # Method to be polled by the main run loop.


    # Public Methods
    def connect(self):
        """
        Connect! Since this is for a Linux (or probably any other POSIX) system, we don't need to do any
        underlying network work, just connect to MQTT.

        :return:
        """
        try:
            self._connect_mqtt()
        except Exception as e:
            raise
        return None

    def disconnect(self, message=None):
        self._logger.info('Planned disconnect with message "' + str(message) + '"')
        # If we have a disconnect message, send it to the device topic.
        # if message is not None:
        #     self._mqtt_client.publish(self._topics['system']['device_state']['topic'], message)
        # When disconnecting, mark the device and the bay as unavailable.
        self._send_offline()
        # Disconnect from broker
        self._mqtt_client.disconnect()
        # Set the internal tracker to disconnected.
        self._mqtt_connected = False

    def poll(self):
        """
        Send
        :return:
        """
        # Set up the return data.
        return_data = {
            'online': brickmaster2.util.interface_status('wlan0'),  # Is the interface up.
            'mqtt_status': self._mqtt_connected,  # Are we connected to MQTT.
            'commands': {}
        }

        # If interface isn't up, not much to do, return immediately.
        if not brickmaster2.util.interface_status('wlan0'):
            return return_data

        self._logger.debug("Network: MQTT connection status is \n\tInternal: {}\n\tClient Object: {}".format(
            self._mqtt_connected,self._mqtt_client.is_connected() ))

        # If interface is up but broker is not connected, retry every 30s. This doesn't wait so that we can return data
        # to the main loop and let other tasks get handled. Proper docking/undocking shouldn't depend on the network so
        # we don't want to block for it.
        if not self._mqtt_connected:
            try_reconnect = False
            # Has is been 30s since the previous attempt?
            try:
                if time.monotonic() - self._reconnect_timestamp > 30:
                    self._logger.info("30s since previous connection attempt. Retrying...")
                    try_reconnect = True
                    self._reconnect_timestamp = time.monotonic()
            except TypeError:
                try_reconnect = True
                self._reconnect_timestamp = time.monotonic()

            if try_reconnect:
                reconnect = self._connect_mqtt()
                # If we failed to reconnect, mark it as failure and return.
                if not reconnect:
                    self._logger.warning("Could not connect to MQTT server. Will retry in 30s.")
                    return return_data
        elif self._mqtt_connected:
            # Send all the messages outbound.
            # For the first 15s after HA discovery, send everything. This makes sure data arrives after HA has
            # established entities. Otherwise, you wind up with entities with unknown status.
            if self._ha_info['override']:
                if time.monotonic() - self._ha_info['start'] <= 15:
                    self._logger.debug(
                        "HA discovery {}s ago, sending all".format(time.monotonic() - self._ha_info['start']))
                    force_repeat = True
                else:
                    self._logger.info("Have sent all messages for 15s after HA discovery. Disabling.")
                    self._ha_info['override'] = False
                    force_repeat = False
            else:
                force_repeat = False
            # Collect messages.
            ## The platform-independent messages. These should always work.
            outbound_messages = brickmaster2.network.mqtt.messages(self._core, self._object_register, self._short_name,
                                                                   force_repeat=force_repeat)
            ## Extend with platform dependent messages.
            outbound_messages.extend(self._mqtt_messages_ps())
            for message in outbound_messages:
                self._logger.debug("Publishing MQTT message: {}".format(message))
                self._pub_message(**message)
            # Check for any incoming commands.
            self._mqtt_client.loop()
        else:
            self._logger.critical("Network: MQTT has undetermined state. This should never happen!")
            raise ValueError("Network internal MQTT tracker has invalid value '{}".format(self._mqtt_connected))

        # Add the upward commands to the return data.
        return_data['commands'] = self._upward_commands
        # Remove the upward commands that are being forwarded.
        self._upward_commands = []
        return return_data

    def register_object(self, action_object):
        """

        :param action_object: Object to add. Control or script
        :type action_object: BM2Script,  ControlGPIO
        :return: None
        """

        try:
            obj_topics = action_object.topics
        except AttributeError:
            self._logger.error("Network: Cannot add object (type: {}), does not have a 'topics' method.".
                               format(type(action_object)))
        else:
            # Save the object.
            if issubclass(type(action_object), brickmaster2.controls.Control):
                self._logger.debug("Registering control '{}'".format(action_object.id))
                self._object_register['controls'][action_object.id] = action_object
            elif issubclass(type(action_object), brickmaster2.scripts.BM2Script):
                self._logger.debug("Registering script '{}'".format(action_object.id))
                self._object_register['scripts'][action_object.id] = action_object
            else:
                self._logger.error("Cannot determine class of object '{}' (type: {}). Cannot register.".
                                   format(action_object.id, type(action_object)))

    def _connect_mqtt(self):
        """
        Connect to the MQTT broker. Run HA Discovery if set.

        :return:
        """
        # Set the last will prior to connecting.
        self._logger.info("Creating last will.")
        self._mqtt_client.will_set(
            "brickmaster2/" + self._short_name + "/connectivity",
            payload='offline', qos=0, retain=True)
        self._logger.debug("Attempting connection.")
        try:
            self._mqtt_client.connect(host=self._mqtt_broker, port=self._mqtt_port)
        except Exception as e:
            self._logger.warning("Could not connect to MQTT broker. Received exception '{}'".format(e))
            return False
        self._logger.debug("Connection attempt completed.")

        # Set the internal MQTT tracker to True. Surprisingly, the client doesn't have a way to track this itself!
        self._mqtt_connected = True
        return True

    def _meminfo(self):
        """
        Linux-only method to fetch memory info.

        :return: list
        """
        # Pull the virtual memory with PSUtil.
        m = psutil.virtual_memory()
        return_dict = {
            'topic': 'brickmaster2/' + self._short_name + '/meminfo',
            'message':
                {
                    'mem_avail': m.available,
                    'mem_total': m.total,
                    'pct_used': m.percent,
                    'pct_avail': 100 - m.percent
                 }
        }
        return [return_dict]

    def _mqtt_messages_ps(self):
        """
        Collect platform-specific MQTT messages.

        :return: list
        """
        messages_ps = []
        # Memory Info.
        messages_ps.extend(self._meminfo())
        return messages_ps

    def _send_online(self):
        """
        Publish an MQTT Online message.
        :return:
        """
        self._mqtt_client.publish("brickmaster2/" + self._short_name + "/connectivity",
                                  payload="online",
                                  retain=True)

    def _send_offline(self):
        """
        Publish an MQTT Offline message.
        :return:
        """
        self._mqtt_client.publish("brickmaster2/" + self._short_name + "/connectivity",
                                  payload="offline", retain=True)
