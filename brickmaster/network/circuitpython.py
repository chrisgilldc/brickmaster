"""
Brickmaster CircuitPython Networking
"""

import adafruit_logging

import brickmaster.exceptions
from brickmaster.network.base import BM2Network
# import brickmaster.util
# import brickmaster.network.mqtt
import gc
import adafruit_minimqtt.adafruit_minimqtt as af_mqtt

class BM2NetworkCircuitPython(BM2Network):
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
            self._logger.debug("Network: Calling base class connect method for MQTT.")
            try:
                return super().connect()
            except BaseException:
                raise

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

        # System's interface is up, run the base poll.

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
        except ConnectionError:
            # If the broker has gone away ping will fail and in turn MiniMQTT will throw a ConnectionError.
            # We'll catch that and set ourselves as disconnected. This should let us recover gracefully.
            self._mqtt_connected = False

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
        try:
            self._logger.debug("Network (MiniMQTT): Publishing to '{}'\n\t"
                               "Payload - '{}'.".format(topic, message))
            self._mini_client.publish(topic, message, retain, qos)
            self._logger.debug("Network (MiniMQTT): Publish complete.")
        except BrokenPipeError:
            self._logger.error("Network (MiniMQTT): Disconnection while publishing! Marking broker as not connected, will retry.")
            self._mqtt_connected = False
        except ConnectionError as e:
            self._logger.error("Network (MiniMQTT): Connection failed, raised error '{}'".format(e.args[0]))
            self._mqtt_connected = False
        except OSError as e:
            if e.args[0] == 104:
                self._logger.error("Network (MiniMQTT): Tried to publish while not connected! Marking broker as not connected, "
                                   "will retry.")
                self._mqtt_connected = False
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