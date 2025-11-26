"""
Brickmaster CircuitPython Networking
"""

import adafruit_logging

import brickmaster.exceptions
from brickmaster.network.base import BMNetwork
# from brickmaster.network.ntp_client import BMNTP
# import brickmaster.util
# import brickmaster.network.mqtt
import gc
import adafruit_minimqtt.adafruit_minimqtt as af_mqtt

class BMNetworkCircuitPython(BMNetwork):
    def __init__(self, core, system_id, short_name, long_name, broker, mqtt_username, mqtt_password, mqtt_timeout=1,
                 mqtt_log=False, net_interface='wlan0', net_indicator=None, port=1883, ha_discover=True,
                 ha_base='homeassistant', ha_area=None, ha_meminfo='unified', timeservers=None, tz="UTC",
                 recheck=60, wifi_obj=None, logger=None):
        """
        Brickmaster Network Class

        :param core: Reference to the main Brickmaster object.
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
        :param net_indicator: Indicator for network status, if configured.
        :type net_indicator: brickmaster.control.Control
        :param ha_discover: Should we send Home Assistant discovery messages?
        :type ha_discover: bool
        :param ha_base: When doing Home Assistant discovery, base topic name?
        :type ha_base: str
        :param ha_area: Area to suggest for entities.
        :type ha_area: str
        :param ha_meminfo: Memory topic format. Must be one of 'unified', 'unified-used', 'split-pct', 'split-all'
        :param wifi_obj: Wifi Object for CircuitPython systems.
        :type wifi_obj: brickmaster.network.BMWiFi
        :param timeservers: List of timeservers to try. Will be tried in-order. Can be IPs or hostnames.
        :type timeservers: list
        :param tz: A timezone
        :type tz: int
        :param recheck: How often to recheck the time, in minutes.
        :type recheck: int
        :param loggger: Logger to use. If one is not provided, a new one will be created at the DEBUG level.
        :type logger: adafruit_logging.Logger
        """
        super().__init__(core, system_id, short_name, long_name, broker, mqtt_username, mqtt_password, mqtt_timeout,
                         mqtt_log, net_interface, net_indicator, port, ha_discover, ha_base, ha_area, ha_meminfo,
                         wifi_obj, logger)

        if timeservers is None:
            timeservers = ["pool.ntp.org"]
        # Create a BMNTP object.
        # self._ntp = BMNTP(timeservers, tz, recheck, wifi_obj, logger)

    def connect(self):
        """
        Connect to WiFi, and then to MQTT if successful.
        :return:
        """
        try:
            self._logger.debug("Network: Trying WiFi connect...")
            self._wifi_obj.connect()
        except Exception as e:
            self._logger.critical("Network: Encountered unhandled exception when connecting to WiFi!")
            self._logger.critical(f"Network: {e}")
            raise
        else:
            # self._logger.debug("Network: Calling NTP poll.")
            # self._ntp.poll()
            self._logger.debug("Network: Calling base class connect method for MQTT.")
            try:
                return super().connect()
            except BaseException:
                raise

    @property
    def ip(self):
        """
        IP of the wireless interface.

        :return: str
        """

        return self._wifi_obj.ip

    def poll(self):
        """
        Poll the MQTT broker, send outbound messages and receive inbound messages.
        Wraps the superclass to check to see if WiFi is connected and connect if need be.

        :return:
        """

        # Is WiFi up?
        if not self._wifi_obj.is_connected:
            self._logger.debug("Network: WiFi not connected! Will attempt connection.")
            try:
                self.connect()
            except BaseException:
                raise

        # System's interface is up. Poll the NTP object to see if it's time to resync time.
        # self._ntp.poll()

        # Call the base class poll.
        return super().poll()

    def _mc_callback_add(self, topic, callback):
        """
        Add a callback for a given topic.

        :param topic: Topic to attach to.
        :type topic: str
        :param callback: The method to call when a message is received.
        :type callback: method
        :return: None
        """
        self._mini_client.add_topic_callback(topic, callback)

    def _mc_connect(self, host, port):
        """
        Call the MQTT Client's connect method.

        :param host: Host to connect to. Hostname or IP.
        :type host: str
        :param port: Port to connect to
        :type port: int
        :return: None
        """
        try:
            self._mini_client.connect(host=host, port=port)
        except af_mqtt.MMQTTException as e:
            self._logger.warning("MiniMQTT: Generated exception '{}' from cause '{}".
                                 format(e.args[0],e.__cause__))
            raise brickmaster.exceptions.BMRecoverableError from e
        else:
            return True

    def _mc_loop(self):
        try:
            self._mini_client.loop(self._mqtt_timeout)
        except ConnectionError as e:
            # Pass the exception upward and let the invoker handle it.
            raise brickmaster.exceptions.BMRecoverableError from e

    def _mc_platform_messages(self):
        """
        Platform-specific MQTT messages.
        :return: list
        """
        # On Linux we use PSUtil for this. Here we use the CircuitPython garbage collector (gc), which doesn't have
        # all the same convenience methods psutil does, so we have to do some math.
        return_dict = {
            'topic': 'brickmaster/' + self._short_name + '/meminfo',
            'message': { 'mem_avail': 'Unknown', 'mem_total': 'Unknown', 'pct_used': 'Unknown',
                    'pct_avail': 'Unknown'  }
        }

        # If gc can't determine the amount of free memory, it will return -1 and we can't math it out.
        if gc.mem_free() < 0:
            return [return_dict]
        else:
            alloc = gc.mem_alloc()
            free = gc.mem_free()

            return_dict['message']['mem_avail'] = free
            return_dict['message']['mem_total'] = free + alloc # Free + allocated = Total? We hope!
            return_dict['message']['pct_avail'] = round(
                (return_dict['message']['mem_avail']/return_dict['message']['mem_total'])*100,2)
            return_dict['message']['pct_used'] = round(
                (alloc/return_dict['message']['mem_total'])*100,2)
            # Return it!
            return [return_dict]

    def _mc_publish(self, topic, message, qos=0, retain=False, force=False):
        """
        Publish via the client object.

        :param topic: Topic to publish on.
        :param message: Message to publish
        :param qos: QOS to use.
        :type qos: int
        :param retain: Should the message be retained by the broker?
        :type retain: bool
        :param force: Should the message be sent even if the message hasn't changed?
        :type force: bool
        :return: None
        """

        # Assume we don't send.
        send = False

        if topic not in self._mqtt_messages_log:
            # If this topic hasn't been seen before, send it.
            send = True
        elif self._mqtt_messages_log[topic] != message:
            # If the new messages is different, send it.
            send = True

        if send:
            try:
                self._logger.debug("Network (MiniMQTT): Publishing to '{}'\n\t"
                                   "Payload - '{}'.".format(topic, message))
                # Do type conversion where necessary.
                if isinstance(message, bool):
                    # Convert booleans to a "True" or "False" string.
                    if message:
                        message = "True"
                    else:
                        message = "False"

                try:
                    self._mini_client.publish(topic, message, retain, qos)
                except ValueError as ve:
                    self._logger.error("Network (MiniMQTT): Payload '{}' ({}) is not a valid value.".
                                       format(message, type(message)))
                    raise ve
                self._logger.debug("Network (MiniMQTT): Publish complete.")
            except BrokenPipeError as e:
                self._logger.error("Network (MiniMQTT): Disconnection while publishing!")
                raise brickmaster.exceptions.BMRecoverableError from e
            except ConnectionError as e:
                self._logger.error("Network (MiniMQTT): Connection failed, raised error '{}'".format(e.args[0]))
                raise brickmaster.exceptions.BMRecoverableError from e
            except OSError as e:
                if e.args[0] == 104:
                    self._logger.error("Network (MiniMQTT): Tried to publish while not connected! Marking broker as not connected, "
                                       "will retry.")
                    raise brickmaster.exceptions.BMRecoverableError from e
                else:
                    raise e

    def _mc_subscribe(self, topic):
        """
        Subscribe the MQTT client to a given topic

        :param topic: The topic to subscribe to.
        :type topic: str
        :return:
        """
        self._mini_client.subscribe(topic)

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
        self._mini_client.will_set(
            topic=topic,
            msg=payload,
            qos=qos,
            retain=retain)

    def _send_online(self):
        """
        Publish an MQTT Online message.
        :return:
        """
        self._logger.debug("Network: Sending online status.")
        self._mini_client.publish(topic="brickmaster/" + self._short_name + "/connectivity",
                                  msg="online", retain=True)

    def _send_offline(self):
        """
        Publish an MQTT Offline message.
        :return:
        """
        self._logger.debug("Network: Sending offline status.")
        self._mini_client.publish(topic="brickmaster/" + self._short_name + "/connectivity", msg="offline",
                                  retain=True)

    def _setup_mqtt(self):
        """
        Create the MQTT object, connect standard callbacks.

        :return:
        """
        self._logger.debug("Network: Circuitpython MQTT setup start.")
        self._logger.debug("Network: Wifi Object can present socket pool: {}".format(type(self._wifi_obj.socket_pool)))
        self._logger.debug(f"Network: Setting socket timeout to '{self._mqtt_timeout}'s. This will also be the loop timeout.")

        # Create the MQTT Client.
        self._mini_client = af_mqtt.MQTT(
            client_id=self._system_id,
            broker=self._mqtt_broker,
            port=self._mqtt_port,
            username=self._mqtt_username,
            password=self._mqtt_password,
            socket_pool=self._wifi_obj.socket_pool,
            socket_timeout=self._mqtt_timeout
        )

        # If MQTT Logging is requested and the logger's effective level is debug, log the client.
        if self._mqtt_log and self._logger.getEffectiveLevel() == adafruit_logging.DEBUG:
            self._logger.debug("Network: Debug enabled, enabling logging on MQTT client as well.")
            self._mini_client.enable_logger(adafruit_logging, adafruit_logging.DEBUG, 'Brickmaster')

        # Connect callback.
        self._mini_client.on_connect = self._on_connect
        # Disconnect callback
        self._mini_client.on_disconnect = self._on_disconnect