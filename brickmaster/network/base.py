"""
Brickmaster Network Base Class
"""


import adafruit_logging
from json import dumps as json_dumps
import time
# Import only the parts of Brickmaster2 we need, to prevent circular imports.
from . import mqtt
import brickmaster.const as const
import brickmaster.util
import brickmaster.version
import brickmaster.exceptions
from ..exceptions import BMRecoverableError


class BM2Network:
    """
    Brickmaster Networking class for Linux
    """
    def __init__(self, core, system_id, short_name, long_name, broker, mqtt_username, mqtt_password, mqtt_timeout=1,
                 mqtt_log=False, net_interface='wlan0', neton=None, netoff=None, port=1883, ha_discover=True,
                 ha_base='homeassistant', ha_area=None, ha_meminfo='unified', wifi_obj=None, log_level=None):
        """
        Brickmaster Network Class

        :param core: Reference to the main Brickmaster2 object.
        :type core: Brickmaster
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
        :param mqtt_log: Enable logging of the base MQTT client. Disabled by default. Will only be logged at the Debug level.
        :type mqtt_log: bool
        :param mqtt_timeout: Timeout for MQTT polling in seconds.
        :type mqtt_timeout: int
        :param net_interface: Linux network interface to use. Defaults to 'wlan0'.
        :type net_interface: str
        :param neton: Control for the Network-Connected LED
        :type neton: brickmaster.control.Control
        :param netoff: Control for the Network Disconnected LED.
        :type netoff: brickmaster.control.Control
        :param ha_discover: Should we send Home Assistant discovery messages?
        :type ha_discover: bool
        :param ha_base: When doing Home Assistant discovery, base topic name?
        :type ha_base: str
        :param ha_area: Area to suggest for entities.
        :type ha_area: str
        :param ha_meminfo: Memory topic format. Must be one of 'unified', 'unified-used', 'split-pct', 'split-all'
        :param wifi_obj: Wifi Object for CircuitPython systems.
        :type wifi_obj: brickmaster.network.BMWiFi
        :param log_level: Level to log at.
        """
        # Set our status to initialization.
        self._status = (0, time.monotonic())

        # Save parameters.
        self._core = core
        self._system_id = system_id
        self._short_name = short_name
        self._long_name = long_name
        self._mqtt_broker = broker
        self._mqtt_log = mqtt_log
        self._mqtt_port = port
        self._mqtt_username = mqtt_username
        self._mqtt_password = mqtt_password
        self._mqtt_timeout = mqtt_timeout
        self._net_interface = net_interface
        # All the HA variables start with _ha, you know, obviously.
        self._ha_override = False
        self._ha_start = time.monotonic()
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

        # Default the logging level.
        if log_level is None:
            log_level = adafruit_logging.WARNING

        # Set up logger. Adafruit Logging doesn't support hierarchical logging.
        self._logger = adafruit_logging.getLogger('Brickmaster')
        self._logger.setLevel(log_level)
        self._logger.info(f"Network: System Name is '{self._long_name}'")
        self._logger.info("Network: Home Assistant discovery (ha discover) is {}".format(self._ha_discover))

        # Set up the network status LEDs, if defined.
        # Net On
        self._logger.debug("Network: Connection status LED object - {}".format(neton))
        if neton is None:
            self._logger.info("Network: Connection status LED not defined.")
            self._neton = brickmaster.controls.CtrlNull("neton_null","Net On Null", self)
        elif not isinstance(neton, brickmaster.controls.BaseControl):
            self._logger.info("Network: Connection status LED is not a valid control.")
            self._neton = brickmaster.controls.CtrlNull("neton_null", "Net On Null", self)
        else:
            self._neton = neton
        # Net Off
        self._logger.debug("Network: Disconnection status LED object - {}".format(netoff))
        if netoff is None:
            self._logger.info("Network: Disconnection status LED not defined.")
            self._netoff = brickmaster.controls.CtrlNull("netoff_null", "Net Off Null", self)
        elif not isinstance(neton, brickmaster.controls.BaseControl):
            self._logger.info("Network: Disconnection status LED is not a valid control.")
            self._netoff = brickmaster.controls.CtrlNull("netoff_null", "Net Off Null", self)
        else:
            self._netoff = netoff

        # Set the status LEDs to initial state.
        self._neton.set('off')
        self._netoff.set('on')

        # Initialize variables
        self._reconnect_timestamp = time.monotonic()
        self._total_failures = 0
        self._retry_time = 0

        # List for commands received and to be passed upward.
        self._upward_commands = []
        # History of payloads, to determine if we need to repeat.
        self._topic_history = {}

        # # Generate device info.
        # self._device_info = brickmaster.network.ha._device_info(
        #     self._system_id, self._long_name, self._ha_area, brickmaster.__version__
        # )

        self._logger.info("Defined Client ID: {}".format(self._system_id))

        self._setup_mqtt() # Create the MQTT Object, connect basic callbacks
        # Set up the last will prior to connecting.
        self._logger.info("Creating last will.")
        self._mc_will_set(topic="brickmaster/" + self._short_name + "/connectivity",
            payload='offline') # Defaults are QOS 0 and Retain True, don't need to respecify.

        self._logger.info('Network: Initialization complete.')

    # Public Methods
    def connect(self):
        """
        Base connect method which is just to connect to MQTT and assume the network is up.
        Wrap this if network checking is needed.

        :return:
        """
        self._logger.debug("Network: Starting MQTT connection...")
        try:
            # Call the connection method. This gets overridden by a subclass if needed.
            self._mc_connect(host=self._mqtt_broker, port=self._mqtt_port)
        except brickmaster.exceptions.BMRecoverableError as e:
            # Update our failure tracker.
            self._total_failures += 1
            if self._retry_time < 120:
                self._retry_time += 5
            self._logger.warning("Network: Could not connect to MQTT broker. Received exception '{}'".format(e.__cause__))
            self._logger.warning("Network: {} failures. Will retry in {}s.".
                                 format(self._total_failures, self._retry_time))
            self._logger.debug("Network: Exception is type '{}', args is '{}'".format(type(e.__cause__), e.__cause__))
            return False
        except brickmaster.exceptions.BMFatalError as e:
            self._logger.critical("Network: Fatal exception while attempting to connect to MQTT Broker ''".
                                  format(e.__cause__))
            self._logger.critical("Network: Made {} attempts before fatal error.".format(self._total_failures))
            raise
        else:
            # Reset the trackers
            self._total_failures = 0
            self._retry_time = 5
            if self.status[0] == const.NET_STATUS_CONNECTED:
                # If we already got a CONNACK from the broker during the connect call, don't set us back.
                self._logger.info("Network: MQTT connection completed.")
            else:
                # Otherwise, set us to CONNECTING and await CONNACK.
                self.status = const.NET_STATUS_CONNECTING
                self._logger.info("Network: MQTT connection attempt completed. Awaiting acknowledgement...")
            return True


        # Old connect code....
        # self._logger.debug("Network: Attempting MQTT connection.")
        # try:
        #     # Call the connection method. This gets overridden by a subclass if needed.
        #     self._mc_connect(host=self._mqtt_broker, port=self._mqtt_port)
        # except brickmaster.exceptions.BMRecoverableError as e:
        #     # Update our failure tracker.
        #     self._total_failures += 1
        #     if self._retry_time < 120:
        #         self._retry_time += 5
        #     self._logger.warning("Network: Could not connect to MQTT broker. Received exception '{}'".format(e.__cause__))
        #     self._logger.warning("Network: {} failures. Will retry in {}s.".
        #                          format(self._total_failures, self._retry_time))
        #     self._logger.debug("Network: Exception is type '{}', args is '{}'".format(type(e.__cause__), e.__cause__))
        #     return False
        # except brickmaster.exceptions.BMFatalError as e:
        #     self._logger.critical("Network: Fatal exception while attempting to connect to MQTT Broker ''".
        #                           format(e.__cause__))
        #     self._logger.critical("Network: Made {} attempts before fatal error.".format(self._total_failures))
        #     raise
        # else:
        #     # Reset the trackers
        #     self._total_failures = 0
        #     self._retry_time = 5
        #     if self.status == const.NET_STATUS_CONNECTED:
        #         # If we already got a CONNACK from the broker during the connect call, don't set us back.
        #         self._logger.info("Network: MQTT connection completed.")
        #     else:
        #         # Otherwise, set us to CONNECTING and await CONNACK.
        #         self.status = const.NET_STATUS_CONNECTING
        #         self._logger.info("Network: MQTT connection attempt completed. Awaiting acknowledgement...")
        #     return True

    def disconnect(self):
        """
        Base disconnect method.
        """
        # When disconnecting, mark the device as unavailable. The will should also do this, but let's try to be neat.
        self._send_offline()
        # Disconnect from broker
        self._mc_disconnect()
        # Set Status Indicators
        self._netoff.set('on')
        self._neton.set('off')
        self.status = const.NET_STATUS_DISCONNECT_PLANNED

    def poll(self):
        """
        Poll the MQTT broker, send outbound messages and receive inbound messages.
        This method should only get called once the network is confirmed to be up.

        :return: dict
        """

        # Set up the return dict.
        return_data = {
            'online': True,
            'mqtt_data': self.status[0],
            'commands': {}
        }
        self._logger.debug("Network: At poll, MQTT has has status - '{}'".format(self._status))

        # If interface is up but broker is not connected, retry every 30s.
        if self.status[0] == const.NET_STATUS_CONNECTED:
            # Send all the messages outbound.
            # For the first 15s after HA discovery, send everything. This makes sure data arrives after HA has
            # established entities. Otherwise, you wind up with entities with unknown status.
            if self._ha_override:
                if time.monotonic() - self._ha_start <= 15:
                    self._logger.debug(
                        "Network: HA discovery {}s ago, sending all".format(time.monotonic() - self._ha_start))
                    force_repeat = True
                else:
                    self._logger.info("Network: Have sent all messages for 15s after HA discovery. Disabling.")
                    self._ha_override = False
                    force_repeat = False
            else:
                force_repeat = False
            # Collect messages.
            ## The platform-independent messages. These should always work.
            self._logger.debug("Network: Collecting outbound MQTT messages.")
            outbound_messages = brickmaster.network.mqtt.messages(self._core, self._object_register, self._short_name,
                                                                   self._logger, force_repeat=force_repeat)
            ## Extend with platform dependent messages.
            outbound_messages.extend(self._mc_platform_messages())
            self._logger.debug("Network: Publishing MQTT messages in queue ({} messages)".format(len(outbound_messages)))
            for message in outbound_messages:
                self._logger.debug("Network: Publishing MQTT message - {}".format(message))
                self._pub_message(**message)
            # Poll the MQTT broker.
            self._logger.debug("Network: Polling MQTT")
            try:
                self._mc_loop()
            except brickmaster.exceptions.BMRecoverableError:
                self._logger.warning("Network (MQTT): Received exception while polling MQTT. Marking as disconnected.")
                self.status = const.NET_STATUS_DISCONNECTED
            else:
                self._logger.debug("Network: Poll complete.")
                # Add the upward commands to the return data.
                return_data['commands'] = self._upward_commands
                # Remove the upward commands that are being forwarded.
                self._upward_commands = []
        elif self.status[0] == const.NET_STATUS_CONNECTING:
            self._logger.debug("Network: Awaiting broker acknowledgement.")
            # Make sure we still poll the broker to try to get its acknowledgement of our connection. We can't *assume*
            # we're connected after a successful connect call, that just means the request was made successfully, not
            # that the broker acknowledged it.
            self._mc_loop()
        elif self.status[0] == const.NET_STATUS_DISCONNECTED:
            if self._total_failures == 0:
                # If we're disconnected and haven't failed before, try to connect immediately.
                self._logger.debug("Network: Disconnected, trying to connect to MQTT broker.")
                self.connect()
            elif self._total_failures > 0 and time.monotonic() - self._reconnect_timestamp > self._retry_time:
                # If retry time has expired, try to connect.
                self._logger.info("Network: Retry time of {}s has expired. Retrying MQTT connection...".
                                  format(self._retry_time))
                self.connect()

            # self._logger.debug("Network: Not connected. Will attempt connection if retry time has expired.")
            # try_reconnect = False # Flag to trigger the connection attempt.
            # # Has the retry time expired?
            # try:
            #     if time.monotonic() - self._reconnect_timestamp > self._retry_time:
            #         self._logger.info(f"Network: {self._retry_time}s since previous MQTT connection attempt. Retrying...")
            #         try_reconnect = True
            #         self._reconnect_timestamp = time.monotonic()
            # except TypeError:
            #     try_reconnect = True
            #     self._reconnect_timestamp = time.monotonic()
            #
            # if try_reconnect:
            #     reconnect = self.connect()
            #     self._logger.debug("Network: MQTT connect call returned '{}'".format(reconnect))
            #     # If we failed to reconnect, mark it as failure and return.
            #     if reconnect:
            #         self._logger.debug("Network: Pre-existing connection status was '{}'".format(self.status[0]))
            #         # If the status isn't already connected, set us to connecting. Doing this check prevents setting us
            #         # back to connected if we received an acknowledgement from the broker during the connect call.
            #         if self.status[0] != const.NET_STATUS_CONNECTED:
            #             self.status = const.NET_STATUS_CONNECTING
            #     else:
            #         self._logger.warning(f"Network: Could not connect to MQTT broker. Will retry in {self._retry_time}s.")
            #         return return_data
        elif self.status[0] == const.NET_STATUS_DISCONNECT_PLANNED:
            self._logger.debug("Network: Disconnected by request. Will not attempt connection.")
        else:
            self._logger.debug(f"Network: Unknown network status {self.status}")
        return return_data

    def register_object(self, action_object):
        """
        Register a control or script for management.

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
            if issubclass(type(action_object), brickmaster.controls.BaseControl):
                self._logger.debug("Registering control '{}' to topics '{}'".format(action_object.id, obj_topics))
                self._object_register['controls'][action_object.id] = action_object
            elif issubclass(type(action_object), brickmaster.scripts.BM2Script):
                self._logger.debug("Registering script '{}' to topics '{}'".format(action_object.id, obj_topics))
                self._object_register['scripts'][action_object.id] = action_object
            else:
                self._logger.error("Cannot determine class of object '{}' (type: {}). Cannot register.".
                                   format(action_object.id, type(action_object)))

    @property
    def status(self):
        """ Status of the network. """
        # self._logger.debug(f"Network: Returning status '{self._status}'")
        return self._status

    @status.setter
    def status(self, new_status):
        """
        Update the network status and wrap a timestamp in it.
        """
        self._status = (new_status, time.monotonic())
        self._logger.debug("Network: MQTT status now '{}' at timestamp '{}'".format(self._status[0],self._status[1]))

    # Private methods
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
            device_info = mqtt.ha_device_info(self._system_id, self._long_name, self._ha_area, brickmaster.__version__)
            discovery_messages = mqtt.ha_discovery(
                self._short_name, self._system_id, device_info, 'brickmaster/', self._ha_base,
                self._ha_meminfo, self._object_register)

            self._logger.debug("Network: Will send discovery messages: {}".format(discovery_messages))
            for discovery_message in discovery_messages:
                self._pub_message(**discovery_message, force_repeat=True, retain=True)
            # Reset the topic history so any newly discovered entities get sent to.
            self._topic_history = {}
            # Set the override stamp. This makes sure force repeat is set to send out data after discovery.
            self._logger.debug("Network: Setting message override.")
            self._ha_override = True
            self._ha_start = time.monotonic()
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
        self._logger.info(f"Network: On Connect callback invoked from result code '{rc}'")
        self._logger.debug("Network:\n\tuserdata - '{}'\n\tflags - '{}'\n\tproperties - '{}'".
                           format(userdata, flags,properties))
        self._logger.debug("Network: Setting status to 'connected'")
        self.status = const.NET_STATUS_CONNECTED

        #TODO: Add monitoring of the homeassistant/status online/offline status to do logic. What logic? Not sure.

        # Subscribe to the script set topic.
        self._logger.debug("Network: Subscribing to script topics.")
        self._mc_subscribe('brickmaster/' + self._short_name + '/script/set')
        self._mc_callback_add('brickmaster/' + self._short_name + '/script/set',
                              self._core.callback_scr)
        # Subscribe to the Control topics.
        for control_id in self._object_register['controls']:
            # Subscribe to the topic.
            self._logger.debug(f"Network: Subscribing to control topic for '{self._object_register['controls'][control_id].id}'")
            self._mc_subscribe('brickmaster/' + self._short_name + '/controls/' +
                               self._object_register['controls'][control_id].id + '/set')
            # Connect the callback.f
            self._mc_callback_add(
                'brickmaster/' + self._short_name + '/controls/' +
                self._object_register['controls'][control_id].id + '/set',
                self._object_register['controls'][control_id].callback)

        # Send the online message.
        self._send_online()

        # Do Home Assistant Discovery.
        self._logger.debug("Network: On Connect invoking HA Discovery.")
        self._run_ha_discovery()

        # Send the one-time messages, which reports system information.
        initial_messages = brickmaster.network.mqtt.initial_messages(self._short_name)
        self._logger.debug(f"Network: Have initial messages '{initial_messages}'")
        for message in initial_messages:
            self._logger.info(f"Network: Sending initial message - {message}")
            self._pub_message(**message)


    def _on_disconnect(self, client, userdata, rc):
        """
        MQTT Client disconnect callback.

        :param client:
        :param userdata:
        :param rc:
        :return:
        """
        self._logger.info("Network: Received on_disconnect")
        self._logger.debug("Network:\n\tclient - '{}'\n\tuserdata - '{}'".format(client, userdata))
        if rc != 0:
            #TODO: Add some logic here or in the platform class to actually handle the result codes and back off when
            # a specific error type is unrecoverable.
            self._logger.warning("Network: Unexpected disconnect with code: {}".format(rc))
        self._reconnect_timer = time.monotonic()
        self._logger.debug("Network: Setting internal MQTT tracker False in '_on_disconnect' callback.")
        self.status = const.NET_STATUS_DISCONNECTED

    def _on_message(self, client, userdata, message):
        """
        Callback when a message is received.
        This isn't expected to ever be used, but will catch cases where we're subscribed but don't have a callback.

        :param client:
        :param userdata:
        :param message:
        :return: None
        """
        self._logger.info("Network: Received on_connect")
        self._logger.debug("Network:\n\tclient - '{}'\n\tuserdata - '{}'".format(client, userdata))

        self._logger.warning(
            "Network: Received message on topic {} with payload {}. No other handler, no action.".format(
                message.topic, message.payload
            ))

    def _pub_message(self, topic, message, force_repeat=False, retain=False):
        """
        Publish a message to the MQTT broker. By default, will not publish a message if that message has previously been
        sent to that topic. This makes it safe to dump the same data in repeatedly without spamming the broker.

        :param topic: Topic to publish to.
        :type topic: str
        :param message: Message to publish
        :type message: str
        :param force_repeat: Should the message be sent even if it was also the previous message sent.
        :type force_repeat: bool
        :param retain: Should the message be retained by the broker?
        :type retain: bool
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
            elif isinstance(message, list):
                outbound_message = str(message)
            else:
                outbound_message = message
            # Make the client-specific call!
            if self.status[0] == const.NET_STATUS_CONNECTED:
                try:
                    self._mc_publish(topic, outbound_message, retain=retain)
                except BMRecoverableError:
                    self._logger.warning("Network: Received recoverable error while publishing. Marking MQTT disconnected for retry.")
                    self.status = const.NET_STATUS_DISCONNECTED
                except BaseException:
                    self._logger.error("Network: Unhandled exception received while publishing!")
                    raise
            else:
                self._logger.debug("Network: Won't publish because MQTT isn't connected.")

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

