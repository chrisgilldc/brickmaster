"""
Brickmaster Control - Single
"""

import adafruit_logging
from .BaseControl import BaseControl
from brickmaster.gpio import EnhancedDigitalInOut
# import board
# import digitalio

class CtrlSingle(BaseControl):
    """
    Control class for a single GPIO pin.
    """
    def __init__(self, ctrl_id, name, core, pins, publish_time, active_low=False,
                 extio_obj=None, icon="mdi:toy-brick", logger=None):
        """
        @param ctrl_id: Short ID for the control. No spaces!
        @type ctrl_id: str
        @param name: Long name for the control
        @type name: str
        @param core: Reference to the Brickmaster core object.
        @type core: object
        @param pinlist: List of pins to use for the flasher. Must contain either strings (single pins) or dicts with
        'on' and 'off' keys.
        @type pinlist: list
        @param publish_time: How long after startup to publish this control for to Home Assistant, in seconds.
        @type publish_time: int
        @param active_low: Should the pin set voltage low when active, high when inactive? This "inverts" the usual behavior.
        @type active_low: bool
        @param extio_obj: External IO object to use for the device.
        @param icon: Icon name to send to Home Assistant.
        @type icon: str
        @param logger: Logger to use. If one is not provided, a new one will be created at the DEBUG level.
        @type logger: adafruit_logger.Logger
        """
        super().__init__(ctrl_id, name, core, icon, publish_time, logger=logger)

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