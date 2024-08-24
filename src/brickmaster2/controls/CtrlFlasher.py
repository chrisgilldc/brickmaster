"""
Brickmaster Control - Flasher
"""
import adafruit_logging
import brickmaster2.controls.BaseControl as BaseControl
from brickmaster2.gpio import EnhancedDigitalInOut
import board
import digitalio
from time import monotonic_ns

class CtrlFlasher(BaseControl):
    """
    Control to handle flashing across multiple pins.
    """
    def __init__(self, id, name, core, pinlist, publish_time, loiter_time=1, switch_time=0, active_low=False,
                 extio_obj=None, icon="mdi:toy-brick", log_level=adafruit_logging.WARNING):

        """
        @param id: Short ID for the control. No spaces!
        @type id: str
        @param name: Long name for the control
        @type name: str
        @param core: Reference to the Brickmaster core object.
        @type core: object
        @param pinlist: List of pins to use for the flasher. Must contain either strings (single pins) or dicts with
        'on' and 'off' keys.
        @type pinlist: list
        @param icon: Icon name to send to Home Assistant.
        @type icon: str
        @param publish_time:
        @type publish_time: int
        @param loiter_time: How long to keep each item on before moving to the next, in milliseconds.
        @type loiter_time: int
        @param switch_time: How long to keep everything off between items, in milliseconds. Defaults to 0.
        @type switch_time: int
        @param log_level: Logging level to use for the control. Technically an int, should be a valid adafruit_logging
        constant.
        @type log_level: int

        """
        super().__init__(id, name, core, icon, publish_time, adafruit_logging.DEBUG)
                         #log_level)

        self._active_low = active_low # Save the active low status.
        self._extio_obj = extio_obj # Save the external IO object, if any.
        # Conver these times to nanoseconds for easy comparison with monotonic_ns
        self._loiter_time = loiter_time * 1000000
        self._switch_time = switch_time * 1000000
        self._position = 0
        self._running = False
        self._updatets = 0
        self._pinlist = pinlist # Save the pinlist config

        # Define a list to keep the pin objects in.
        self._gpio_objects = []
        # Iterate the pin list, create objects for them all.
        for pin_item in pinlist:
            if isinstance(pin_item, str):
                pin_obj = EnhancedDigitalInOut(pin_item, extio_obj=self._extio_obj)
                self._gpio_objects.append(pin_obj)
            elif isinstance(pin_item, dict):
                try:
                    self._gpio_obj = EnhancedDigitalInOut(on_pin=pin_item['on'], off_pin=pin_item['off'],
                                                          extio_obj=self._extio_obj)
                except KeyError as ke:
                    self._logger.critial("Control {}: Could not configure due to missing key.".format(self._id))
                    raise ke
            else:
                raise TypeError("Control {}: Pin list contains invalid definition.".format(self._id))

    @property
    def status(self):
        """
        Report the control status.
        """
        return self._running

    @property
    def seq_pos(self):
        """
        Item of the list currently on.
        """
        return self._position

    def set(self, value: str):
        """
        Set the control status.
        """
        if value.lower() == 'on':
            # Set ourself to running.
            self._running = True
            # Reset the position
            self._position = 0
            # Turn on the gpio at position 0.
            self._gpio_objects[self._position].value = True
            # Set a timestamp.
            self._update_ts = monotonic_ns()
        elif value.lower() == 'off':
            self._running = False
            # Turn everything off.
            for gpio in self._gpio_objects:
                gpio.value = False
        else:
            self._logger.warning(f"Control: ID '{self.name}' received unknown set value '{value}'")

    def update(self):
        """
        Called by the Core run loop to update status.
        """

        if self._running:
            self._logger.debug("Control {}: Updating...".format(self._id))
            # If we've loitered too long, time to turn this off.
            if monotonic_ns() - self._updatets > self._loiter_time:
                self._gpio_objects[self._position].value = False
            # If we've both loitered and used the switch time, move on to the next.
            if monotonic_ns() - self._updatets > (self._loiter_time + self._switch_time):
                self._position += 1
                # Reset if we're at the end.
                if self._position >= len(self._gpio_objects):
                    self._position = 0
                # Turn on the next item.
                self._gpio_objects[self._position].value=True

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
