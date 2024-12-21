"""
Brickmaster Control - Single
"""

import adafruit_logging
from .BaseControl import BaseControl
from brickmaster2.gpio import EnhancedDigitalInOut
# import board
# import digitalio

class CtrlSingle(BaseControl):
    """
    Control class for a single GPIO pin.
    """
    def __init__(self, ctrl_id, name, core, pins, publish_time, active_low=False,
                 extio_obj=None, icon="mdi:toy-brick", log_level=adafruit_logging.WARNING):
        super().__init__(ctrl_id, name, core, icon, publish_time, log_level)

        self._active_low = active_low # Save our active low status.
        self._extio_obj = extio_obj # Save the external IO object, if any.

        if isinstance(pins, dict):
            try:
                self._gpio_obj = EnhancedDigitalInOut(on_pin=pins['on'], off_pin=pins['off'], extio_obj=self._extio_obj)
            except KeyError as ke:
                self._logger.critial("Control {}: Could not configure due to missing key.".format(self._ctrl_id))
                raise ke
        else:
            self._gpio_obj = EnhancedDigitalInOut(pins, extio_obj=self._extio_obj)
        #
        # else:
        #     raise TypeError("Control {}: pins type {} not allowed for CtrlSingle".format(self._id, type(pins)))


        # Old method of setting up the pins.
        # try:
        #     if awboard is not None:
        #         self._pin = self._setup_pin_aw9523(awboard, pin)
        #     else:
        #         self._pin = self._setup_pin_onboard(pin)
        # except (AssertionError, AttributeError, ValueError) as e:
        #     raise e

        # Set self to off.
        self.set('off')

    def set(self, value: str):
        """
        Set the control status.
        """
        self._logger.info("Control: Setting control '{}' to '{}'".format(self.name, value))
        if value.lower() == 'on':
            self._gpio_obj.value = True
        elif value.lower() == 'off':
            self._gpio_obj.value = False
        else:
            self._logger.warning(f"Control: ID '{self.name}' received unknown set value '{value}'")
            print(f"Control: ID '{self.name}' received unknown set value '{value}'")

    @property
    def status(self):
        """
        Current state of the control.
        """

        if self._gpio_obj.value:
            return "ON"
        else:
            return "OFF"

    def callback(self, client, topic, message):
        """
        Control Callback

        :param client: Client instance for the callback.
        :param topic: Topic the message was received on.
        :param message: Message.
        :return: None
        """
        print("Control: Incoming message is '{}' ({})".format(message, type(message)))
        if isinstance(message, str):
            # MiniMQTT (Circuitpython) outputs a straight string.
            message_text = message.lower()
        else:
            # Paho MQTT (linux) delivers a message object from which we need to extract the payload.
            # Convert the message payload (which is binary) to a string.
            message_text = str(message.payload, 'utf-8').lower()
        self._logger.debug("Control: Control '{}' ({}) received message '{}'".format(self.name, self.id,
                                                                                     message_text))
        valid_values = ['on', 'off']
        # If it's not a valid option, just ignore it.
        if message_text not in valid_values:
            self._logger.info("Control: Control '{}' ({}) received invalid command '{}'. Ignoring.".
                              format(self.name, self.id, message_text))
        else:
            self.set(message_text)