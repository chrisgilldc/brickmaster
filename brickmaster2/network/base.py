"""
BrickMaster2 Network Base Class
"""


import adafruit_logging
from json import dumps as json_dumps
import time
# Import only the parts of Brickmaster2 we need, to prevent circular imports.
from . import mqtt
import brickmaster2.util
import brickmaster2.version

class BM2Network:
    """
    BrickMaster2 Networking class for Linux
    """
    def __init__(self, core, system_id, short_name, long_name, broker, mqtt_username, mqtt_password, net_on=None,
                 net_off=None, port=1883, ha_discover=True, ha_base='homeassistant', ha_area=None,
                 ha_meminfo='unified', wifi_obj=None, log_level=None):
        """
        BrickMaster2 Network Class

        :param core: Reference to the main Brickmaster2 object.
        :type core: BrickMaster2
        :param system_id: ID of the system. Cannot include spaces!
        :type system_id: str
        :param long_name: Long name of the system. Used for Home Assistant discovery.
        :type long_name: str
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
        :param wifi_obj: Wifi Object for CircuitPython systems.
        :type wifi_obj: brickmaster.network.BM2WiFi
        :param log_level: Level to log at.
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
            'discover_drone': False,
            'override': False,
            'start': time.monotonic()
        }
        self._ha_discover = ha_discover
        self._ha_base = ha_base
        self._ha_meminfo = ha_meminfo
        self._ha_area = ha_area
        self._wifi_obj = wifi_obj
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
        self._logger.info(f"Network: System Name is '{self._long_name}'")

        # Initialize variables
        self._reconnect_timestamp = None
        self._logger.debug("Network: Setting internal MQTT tracker False at startup.")
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

        self._setup_mqtt() # Create the MQTT Object, connect basic callbacks

        self._logger.info('Network: Initialization complete.')

    # Public Methods
    def connect(self):
        """
        Base connect method which is just to connect to MQTT and assume the network is up.
        Wrap this if network checking is needed.

        :return:
        """
        try:
            self._connect_mqtt()
        except Exception as e:
            raise
        # else:
        #     # Our own flag will set True by the _on_connect callback.
        # self._logger.debug(f"Network: MQTT status is '{self._mqtt_connected}'")
        # if self._mqtt_connected:
        #     self._logger.debug("Network: Running HA discovery.")
        # self._logger.debug("Network: Doing HA discovery now!")
        # self._run_ha_discovery()
        return None

    def disconnect(self):
        """
        Base disconnect method.
        """
        # When disconnecting, mark the device and the bay as unavailable.
        self._send_offline()
        # Disconnect from broker
        self._mc_disconnect()
        # Set the internal tracker to disconnected.

    def poll(self):
        """
        Poll the MQTT broker, send outbound messages and receive inbound messages.
        This method should only get called once the network is confirmed to be up.

        :return: dict
        """

        # Set up the return dict.
        return_data = {
            'online': True,
            'mqtt_data': self._mqtt_connected,
            'commands': {}
        }

        # If interface is up but broker is not connected, retry every 30s.
        self._logger.debug(f"Network: MQTT connection status from BM2 Tracker is '{self._mqtt_connected}'")
        if not self._mqtt_connected:
            try_reconnect = False
            # Has is been 30s since the previous attempt?
            try:
                if time.monotonic() - self._reconnect_timestamp > 30:
                    self._logger.info("Network: 30s since previous MQTT connection attempt. Retrying...")
                    try_reconnect = True
                    self._reconnect_timestamp = time.monotonic()
                else:
                    self._logger.debug("Network: Too soon to retry MQTT connection")
            except TypeError:
                try_reconnect = True
                self._reconnect_timestamp = time.monotonic()

            if try_reconnect:
                reconnect = self._connect_mqtt()
                # If we failed to reconnect, mark it as failure and return.
                if not reconnect:
                    self._logger.warning("Network: Could not connect to MQTT server. Will retry in 30s.")
                    return return_data
                else:
                    self._logger.debug("Network: MQTT reconnect successful.")
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
            outbound_messages.extend(self._mc_platform_messages())
            for message in outbound_messages:
                self._logger.debug("Network: Publishing MQTT message - {}".format(message))
                self._pub_message(**message)
            # Check for any incoming commands.
            self._mc_loop()
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

    # Private methods
    def _connect_mqtt(self):
        """
        Connect to the MQTT broker.

        :return:
        """
        # Set the last will prior to connecting.
        self._logger.info("Creating last will.")
        self._mc_will_set(topic="brickmaster2/" + self._short_name + "/connectivity",
            payload='offline', qos=0, retain=True)
        self._logger.debug("Network: Attempting MQTT connection.")
        try:
            # Call the connection method. This gets overridden by a subclass if needed.
            self._mc_connect(host=self._mqtt_broker, port=self._mqtt_port)
        except Exception as e:
            self._logger.warning("Could not connect to MQTT broker. Received exception '{}'".format(e))
            return False
        # self._logger.debug("Network: MQTT connection attempt completed.")

        # Set the internal MQTT tracker to True. Surprisingly, the client doesn't have a way to track this itself!
        # self._logger.debug("Network: Setting internal MQTT tracker True in '_connect_mqtt' call.")
        # self._mqtt_connected = True
        return True

    def _connect_wifi(self):
        """
        Connect to the network.

        :return: None
        """
        raise NotImplemented("Network: WiFi Connection handling should be dealt with by a subclass!")

    def _run_ha_discovery(self):
        """
        Do Home Assistant discovery

        :return: None
        """
        # Run Home Assistant Discovery, if enabled.
        # This had been part of the _on_connect callback, which was great, but for some reason MiniMQTT doesn't like it,
        # although Paho does. As a general solution, making it a separate method and calling it directly from
        # connect now.
        if self._ha_discover:
            self._logger.info("Network: Running Home Assistant discovery...")
            # Create and stash device info for convenience.
            device_info = mqtt.ha_device_info(self._system_id, self._long_name, self._ha_area,
                                              brickmaster2.__version__)
            discovery_messages = mqtt.ha_discovery(
                self._short_name, self._system_id, device_info, 'brickmaster2/', self._ha_base,
                self._ha_meminfo, self._object_register)

            self._logger.debug("Network: Will send discovery messages: {}".format(discovery_messages))
            for discovery_message in discovery_messages:
                self._pub_message(**discovery_message)
            # Reset the topic history so any newly discovered entities get sent to.
            self._topic_history = {}
            # Set the override stamp. This makes sure force repeat is set to send out data after discovery.
            self._ha_info['override'] = True
            self._ha_info['start'] = time.monotonic()
        else:
            self._logger.warning("Network: Home Assistant discovery disabled. Will not run.")

    def _on_connect(self, userdata, flags, rc, properties=None):
        """
        MQTT Client connection callback.

        :param userdata:
        :param flags:
        :param rc:
        :param properties:
        :return:
        """
        self._logger.info("Network: Connected to MQTT Broker with result code: {}".format(rc))
        self._logger.debug("Network: Setting internal MQTT tracker True in '_on_connect' callback.")
        self._mqtt_connected = True

        # TODO: Make sure subscriptions reconnect.
        # Subscribe to the script set topic.
        self._mc_subscribe('brickmaster2/' + self._short_name + '/script/set')
        self._mc_callback_add('brickmaster2/' + self._short_name + '/script/set',
                              self._core.callback_scr)
        # Subscribe to the Control topics.
        for control_id in self._object_register['controls']:
            # Subscribe to the topic.
            self._mc_subscribe('brickmaster2/' + self._short_name + '/controls/' +
                               self._object_register['controls'][control_id].id + '/set')
            # Connect the callback.
            self._mc_callback_add(
                'brickmaster2/' + self._short_name + '/controls/' +
                self._object_register['controls'][control_id].id + '/set',
                self._object_register['controls'][control_id].callback)

        # Send the online message.
        self._send_online()
        # Do Home Assistant Discovery.
        self._run_ha_discovery()


    def _on_disconnect(self, client, userdata, rc):
        """
        MQTT Client disconnect callback.

        :param client:
        :param userdata:
        :param rc:
        :return:
        """
        if rc != 0:
            self._logger.warning("Network: Unexpected disconnect with code: {}".format(rc))
        self._reconnect_timer = time.monotonic()
        self._logger.debug("Network: Setting internal MQTT tracker False in '_on_disconnect' callback.")
        self._mqtt_connected = False

    def _on_message(self, client, user, message):
        """
        Callback when a message is received.
        This isn't expected to ever be used, but will catch cases where we're subscribed but don't have a callback.

        :param client:
        :param user:
        :param message:
        :return: None
        """
        self._logger.warning(
            "Network: Received message on topic {} with payload {}. No other handler, no action.".format(
                message.topic, message.payload
            ))

    def _pub_message(self, topic, message, force_repeat=False):
        """
        Publish a message to the MQTT broker. By default, will not publish a message if that message has previously been
        sent to that topic. This makes it safe to dump the same data in repeatedly without spamming the broker.

        :param topic: Topic to publish to.
        :type topic: str
        :param message: Message to publish
        :type message: str
        :param force_repeat: Should the message be sent even if it was also the previous message sent.
        :type force_repeat: bool
        :return:
        """
        self._logger.debug("Network: Processing message publication on topic '{}'".format(topic))
        # Set the send flag initially. If we've never seen the topic before or if we're set to repeat, go ahead and send.
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
                    self._logger.debug("Network: Message '{}' does not match previous message '{}'. Publishing.".
                                       format(message, previous_message))
                    send = True
                else:
                    self._logger.debug("Network: Message has not changed, will not publish")
                    return
            # For dictionaries, compare individual elements. This doesn't handle nested dicts, but those aren't used.
            elif isinstance(message, dict) and isinstance(previous_message, dict):
                for item in message:
                    if item not in previous_message:
                        self._logger.debug("Network: Message dict contains new key, publishing.")
                        send = True
                        break
                    if message[item] != previous_message[item]:
                        self._logger.debug("Network: Message dict key '{}' has changed value, publishing.".format(item))
                        send = True
                        break
            # If type has changed, which is odd,  (and it shouldn't, usually), send it.
            elif type(message) != type(previous_message):
                self._logger.debug("Network: Message type has changed from '{}' to '{}'. Unusual, but publishing anyway.".
                                   format(type(previous_message), type(message)))
                send = True

        # If we're sending do it.
        if send:
            self._logger.debug("Network: Publishing message...")
            # New message becomes the previous message.
            self._topic_history[topic] = message
            # Convert the message to JSON if it's a dict, otherwise just send it.
            if isinstance(message, dict):
                outbound_message = json_dumps(message)
            else:
                outbound_message = message
            # Make the client-specific call!

            self._mc_publish(topic, outbound_message)

    # Method studs to be overridden.
    def _mc_callback_add(self, topic, callback):
        """
        Connect the MQTT Client's topic to a callback.

        :param topic: Topic to watch
        :type topic: str
        :param callback: Callback to call when messages are received.
        :type callback: method
        :return: None
        """
        raise NotImplemented("Must be defined in subclass!")

    def _mc_connect(self, host, port):
        """
        Call the MQTT Client's connect method.

        :param host: Host to connect to. Hostname or IP.
        :type host: str
        :param port: Port to connect to
        :type port: int
        :return: None
        """
        raise NotImplemented("Must be defined in subclass!")

    def _mc_disconnect(self):
        raise NotImplemented("Must be defined in subclass!")

    def _mc_publish(self, topic, message, qos=0, retain=False):
        """
        Publish via the client object.

        :param topic: Topic to publish on.
        :param message: Message to publish
        :param qos: QOS to use.
        :type qos: int
        :param retain: Should the message be retained by the broker?
        :type retain: bool
        :return: None
        """
        raise NotImplemented("Must be defined in subclass!")

    def _mc_loop(self):
        """
        Call the MQTT Client's looping/polling method.

        :return: None
        """
        raise NotImplemented("Must be defined in subclass!")

    def _mc_onmessage(self, callback):
        """
        General-purpose on-message callback

        :param callback: Callback to call.
        :return: None
        """
        raise NotImplemented("Must be defined in subclass!")

    def _mc_platform_messages(self):
        """
        Generate platform_specific MQTT messages. Most message generation is done in the mqtt.* methods, which are
        common.
        :return: list
        """
        raise NotImplemented("Must be defined in subclass!")

    def _mc_subscribe(self, topic):
        """
        Subscribe the MQTT client to a given topic

        :param topic: The topic to subscribe to.
        :type topic: str
        :return:
        """
        raise NotImplemented("Must be defined in subclass!")

    def _mc_will_set(self, topic, payload, qos=0, retain=True):
        """
        Set the MQTT client's will.

        :param topic: Topic for the will
        :type topic: str
        :param payload: What to send on unexpected disconnect
        :type payload: str
        :param qos: Quality of Service level.
        :type qos: int
        :param retain: Should the message be retained?
        :type retain: bool
        :return: None
        """
        raise NotImplemented("Must be defined in subclass!")

    def _send_offline(self):
        """
        Publish an MQTT Offline message.
        :return:
        """
        raise NotImplemented("Must be defined in subclass!")

    def _send_online(self):
        """
        Publish an MQTT Online message.
        :return:
        """
        raise NotImplemented("Must be defined in subclass!")

    def _setup_mqtt(self):
        """
        Method to create the MQTT client object.
        :return:
        """
        raise NotImplemented("Must be defined in subclass!")

