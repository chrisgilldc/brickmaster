"""
BrickMaster2 Linux Networking
"""

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
        # Set up the return data.
        return_data = {
            'online': brickmaster2.util.interface_status('wlan0'),  # Is the interface up.
            'mqtt_status': self._mqtt_connected,  # Are we connected to MQTT?
            'commands': {}
        }

        # If interface isn't up, not much to do, return immediately.
        if not brickmaster2.util.interface_status('wlan0'):
            return return_data

        # If interface is up but broker is not connected, retry every 30s.
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
            self._mc_loop()
        else:
            self._logger.critical("Network: MQTT has undetermined state. This should never happen!")
            raise ValueError("Network internal MQTT tracker has invalid value '{}".format(self._mqtt_connected))

        # Add the upward commands to the return data.
        return_data['commands'] = self._upward_commands
        # Remove the upward commands that are being forwarded.
        self._upward_commands = []
        return return_data

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
        self._paho_client.connect(host=host, port=port)

    def _mc_disconnect(self):
        raise NotImplemented("Must be defined in subclass!")

    def _mc_loop(self):
        self._paho_client.loop()

    def _mc_onmessage(self, callback):
        """
        General-purpose on_message callback.

        :param callback: Callback to hit when a message is received.
        :type callback: method
        :return:
        """
        self._paho_client.on_connect = callback
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
        self._paho_client.publish(topic, message, qos, retain)

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
        self._paho_client.publish("brickmaster2/" + self._short_name + "/connectivity",
                                  payload="online", retain=True)
    def _send_offline(self):
        """
        Publish an MQTT Offline message.
        :return:
        """
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
        # Connect MQTT Logger.
        # Uncomment this to get more detailed MQTT logging.
        # self._mqtt_client.enable_logger(self._logger)

        # Connect callback.
        self._paho_client.on_connect = self._on_connect
        # Disconnect callback
        self._paho_client.on_disconnect = self._on_disconnect