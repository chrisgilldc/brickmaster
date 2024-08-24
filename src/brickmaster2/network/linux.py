"""
BrickMaster2 Linux Networking
"""

import adafruit_logging
from brickmaster2.network.base import BM2Network
import brickmaster2.util
import brickmaster2.network.mqtt
import psutil
from paho.mqtt.client import Client
import time

class BM2NetworkLinux(BM2Network):

    def poll(self):
        """
        Send
        :return:
        """

        # Is the system's interface up? If not, we can't do anything else.
        if not brickmaster2.util.interface_status(self._net_interface):
            return { 'online': False, 'mqtt_status': False, 'commands': {} }

        # System's interface is up, run the base poll.
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
        self._paho_client.message_callback_add(topic, callback)

    def _mc_connect(self, host, port):
        """
        Call the MQTT Client's connect method.

        :param host: Host to connect to. Hostname or IP.
        :type host: str
        :param port: Port to connect to
        :type port: int
        :return: None
        """
        # Connect
        try:
            self._paho_client.connect(host=host, port=port)
        except ConnectionRefusedError as e:
            # These are the exceptions can happen. Wrap this as BM2RecoverableError.
            raise brickmaster2.exceptions.BM2RecoverableError from e
        else:
            # Start the background thread.
            self._paho_client.loop_start()
            return True

    def _mc_disconnect(self):
        """
        Disconnect from the client.
        :return:
        """
        # Stop the loop thread.
        self._paho_client.loop_stop()
        # Disconnect.
        self._paho_client.disconnect()

    def _mc_loop(self):
        """
        Call the looping methods.
        :return:
        """
        # Looping not required since PAHO is running in a background thread.
        pass

    def _mc_onmessage(self, callback):
        """
        General-purpose on_message callback.

        :param callback: Callback to hit when a message is received.
        :type callback: method
        :return:
        """
        self._paho_client.on_connect = callback

    def _mc_platform_messages(self):
        """
        Linux platform specific messages.

        :return: list
        """
        messages_ps = []
        # Pull the virtual memory with PSUtil.
        m = psutil.virtual_memory()
        messages_ps.append({
            'topic': 'brickmaster2/' + self._short_name + '/meminfo',
            'message':
                {
                    'mem_avail': m.available,
                    'mem_total': m.total,
                    'pct_used': m.percent,
                    'pct_avail': 100 - m.percent
                }
        })
        return messages_ps

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
            self._paho_client.publish(topic, message, qos, retain)
        except TypeError as te:
            self._logger.error("Network: Could not publish message, wrong type. '{}' ({})".
                               format(message, type(message)))
            raise te

    def _mc_subscribe(self, topic):
        """
        Subscribe the MQTT client to a given topic

        :param topic: The topic to subscribe to.
        :type topic: str
        :return:
        """
        self._paho_client.subscribe(topic)

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
        self._paho_client.will_set(
            topic=topic,
            payload=payload,
            qos=qos,
            retain=retain)


    def _send_online(self):
        """
        Publish an MQTT Online message.
        :return:
        """
        self._logger.debug("Network: Sending online status.")
        self._paho_client.publish("brickmaster2/" + self._short_name + "/connectivity",
                                  payload="online", retain=True)
    def _send_offline(self):
        """
        Publish an MQTT Offline message.
        :return:
        """
        self._logger.debug("Network: Sending offline status.")
        self._paho_client.publish("brickmaster2/" + self._short_name + "/connectivity",
                                  payload="offline", retain=True)

    def _setup_mqtt(self):
        """
        Create the MQTT object, connect standard callbacks.

        :return:
        """

        # Create the MQTT Client.
        self._paho_client = Client(
            client_id=self._system_id
        )
        self._paho_client.username_pw_set(
            username=self._mqtt_username,
            password=self._mqtt_password
        )

        # If MQTT Logging is requested and the logger's effective level is debug, log the client.
        if self._mqtt_log and self._logger.getEffectiveLevel() == adafruit_logging.DEBUG:
            self._paho_client.enable_logger(self._logger)

        # Connect callback.
        self._paho_client.on_connect = self._on_connect
        # Disconnect callback
        self._paho_client.on_disconnect = self._on_disconnect