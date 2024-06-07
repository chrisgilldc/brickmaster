"""
BrickMaster2 CircuitPython Networking
"""

from brickmaster2.network.base import BM2Network
import brickmaster2.util
import brickmaster2.network.mqtt
#import psutil
#from paho.mqtt.client import Client
import adafruit_minimqtt.adafruit_minimqtt as af_mqtt
import time

class BM2NetworkCircuitPython(BM2Network):
    def connect(self):
        """
        Connect to WiFi, and then to MQTT if successful.
        :return:
        """
        try:
            self._wifi_obj.connect()
        except Exception as e:
            self._logger.critical("Network: Encountered unhandled exception when connecting to WiFi!")
            self._logger.critical(f"Network: {e}")
            raise
        else:
            super().connect()

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
            except Exception as e:
                raise

        # System's interface is up, run the base poll.

        # Call the base class poll.
        return super().poll()

    def _meminfo(self):
        """
        Linux-only method to fetch memory info.

        :return: list
        """
        #TODO: Rewrite for CircuitPython
        # Pull the virtual memory with PSUtil.
        # m = psutil.virtual_memory()
        # return_dict = {
        #     'topic': 'brickmaster2/' + self._short_name + '/meminfo',
        #     'message':
        #         {
        #             'mem_avail': m.available,
        #             'mem_total': m.total,
        #             'pct_used': m.percent,
        #             'pct_avail': 100 - m.percent
        #          }
        # }
        # return [return_dict]
        return []

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
        self._mini_client.connect(host=host, port=port)

    def _mc_loop(self):
        self._mini_client.loop(1)

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
        self._mini_client.publish(topic, message, retain, qos)

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
            payload=payload,
            qos=qos,
            retain=retain)

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
        self._mini_client.publish(topic="brickmaster2/" + self._short_name + "/connectivity",
                                  msg="online", retain=True)
    def _send_offline(self):
        """
        Publish an MQTT Offline message.
        :return:
        """
        self._mini_client.publish(topic="brickmaster2/" + self._short_name + "/connectivity", msg="offline",
                                  retain=True)

    def _setup_mqtt(self):
        """
        Create the MQTT object, connect standard callbacks.

        :return:
        """

        # Create the MQTT Client.
        self._mini_client = af_mqtt.MQTT(
            client_id=self._system_id,
            broker=self._mqtt_broker,
            port=self._mqtt_port,
            username=self._mqtt_username,
            password=self._mqtt_password,
            socket_pool=self._wifi_obj.socket_pool
            # socket_timeout=1 # Default is one, don't need to set.
        )

        # Connect callback.
        self._mini_client.on_connect = self._on_connect
        # Disconnect callback
        self._mini_client.on_disconnect = self._on_disconnect