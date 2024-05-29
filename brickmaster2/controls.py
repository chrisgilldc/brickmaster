# Brickmaster2 Controls
import adafruit_logging as logger
import board
import digitalio
import sys


class Control:
    def __init__(self, id, name, icon="mdi:toy-brick", publish_time=15):
        # Create a logger.
        self._logger = logger.getLogger('BrickMaster2')
        # Set the ID.
        self._control_id = id
        # Set the Name.
        self._control_name = name
        self._topics = None
        self._status = None
        self._icon = icon
        self._publish_time = publish_time
        # Create topics for the control. This must be implemented per subclass.

    # This method creates a list of topics to subscribe to for this control.
    # Usually this will be 'name'/'set' and 'name'/'state'. Separating the two allows for controls
    # that have a time lag.
    @property
    def topics(self):
        return self._topics

    # Status of the control. Some types of controls will be able to directly test the state (ie: GPIO), while others
    # will have to track based on past settings and return a presumptive state (ie: PowerFunctions)
    @property
    def status(self):
        raise NotImplemented("Status must be implemented in a control subclass")

    # Set the control to a value. Simple controls will take 'on' and 'off'. *All* controls must take 'off' as an option.
    def set(self, value):
        raise NotImplemented("Set must be implemented in a control subclass")

    @property
    def name(self):
        return self._control_name

    @property
    def id(self):
        return self._control_id

    # Callback the network will access to get messages to this control.
    def callback(self, client, topic, message):
        raise NotImplemented("Control callbacks must be implemented in a control subclass.")


# Control class for GPIO
class CtrlGPIO(Control):
    def __init__(self, id, name, pin, publish_time, addr=None, invert=False,
                 awboard=None, icon="mdi:toy-brick", **kwargs):
        super().__init__(id, name, icon, publish_time)
        self._invert = invert

        if awboard is not None:
            self._setup_pin_aw9523(awboard, pin)
        else:
            self._setup_pin_onboard(pin)

        # Set self to off.
        self.set('off')

    # Method to set up an onboard GPIO pin.
    def _setup_pin_onboard(self, pin):
        # Have the import. Now create the pin.
        try:
            self._pin = digitalio.DigitalInOut(getattr(board, str(pin)))
        except AttributeError:
            self._logger.critical("Control: Control '{}' references pin '{}', does not exist. Exiting!".
                                  format(self.name, pin))
            sys.exit(1)
        except ValueError as ve:
            # Using an in-use pin will return a ValueError.
            self._logger.critical("Control: Control '{}' uses pin '{}' which is already in use!".
                                  format(self.name, pin))
            raise
        # Set the pin to an output
        self._pin.direction = digitalio.Direction.OUTPUT

    # Method to set up GPIO via an AW9523 on I2C.
    def _setup_pin_aw9523(self, awboard, pin):
        try:
            self._pin = awboard.get_pin(pin)
        except AssertionError:
            self._logger.critical("Control: Control '{}' asserted pin '{}', not valid.".format(self.name, pin))
            raise
        # Have a pin now, set it up.
        self._pin.direction = digitalio.Direction.OUTPUT

    def set(self, value):
        self._logger.info("Control: Setting control '{}' to '{}'".format(self.name, value))
        if value.lower() == 'on':
            if self._invert:
                self._logger.debug("Control: Control is inverted, 'On' state sets low.")
                self._pin.value = False
            else:
                self._pin.value = True
        elif value.lower() == 'off':
            if self._invert:
                self._logger.debug("Control: Control is inverted, 'Off' state sets high.")
                self._pin.value = True
            else:
                self._pin.value = False

    @property
    def icon(self):
        return self._icon

    @property
    def status(self):
        if self._pin.value is True:
            if self._invert:
                return 'OFF'
            else:
                return 'ON'
        elif self._pin.value is False:
            if self._invert:
                return 'ON'
            else:
                return 'OFF'
        else:
            return 'Unavailable'

    def callback(self, client, topic, message):
        # Convert the message payload (which is binary) to a string.
        message_text = str(message.payload, 'utf-8').lower()
        self._logger.debug("Control: Control '{}' ({}) received message '{}'".format(self.name, self.id,
                                                                                     message_text))
        valid_values = ['on', 'off']
        # If it's not a valid option, just ignore it.
        if message_text.lower() not in valid_values:
            self._logger.info("Control: Control '{}' ({}) received invalid command '{}'. Ignoring.".
                              format(self.name, self.id, message_text))
        else:
            self.set(message_text.lower())