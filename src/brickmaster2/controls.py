# Brickmaster2 Controls
import adafruit_logging
import board
import digitalio
import sys


class Control:
    def __init__(self, id, name, icon="mdi:toy-brick", publish_time=15, log_level=adafruit_logging.WARNING):
        # Create a logger.
        self._logger = adafruit_logging.getLogger('BrickMaster2')
        self._logger.setLevel(log_level)
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

    def _setup_pin_onboard(self, pin_id):
        """
        Creates a pin located directly on the controller.

        :param pin_id: ID of the onboard pin to create.
        :type pin_id: str
        :return: microcontroller.Pin
        """
        # Have the import. Now create the pin.
        try:
            pin = digitalio.DigitalInOut(getattr(board, str(pin_id)))
        except AttributeError as ae:
            self._logger.critical(f"Control: Control '{self.name}' references non-existent pin '{pin_id}'.")
            raise ae
        except ValueError as ve:
            # Using an in-use pin will return a ValueError.
            self._logger.critical("Control: Control '{self.name}' uses pin '{pin_id}' which is already in use!")
            raise ve
        # Set the pin to an output
        pin = digitalio.Direction.OUTPUT
        return pin

    # Method to set up GPIO via an AW9523 on I2C.
    def _setup_pin_aw9523(self, awboard, pin_id):
        """
        Set up a pin located on an I2C attached AW9523 expander.

        :param awboard: AW9523 object.
        :type awboard: adafruit_aw9523.AW9523
        :param pin_id: ID of the AW9523 pin to create (0-15)
        :type pin_id: int
        :return: microcontroller.Pin
        """
        try:
            pin = awboard.get_pin(pin_id)
        except AssertionError as ae:
            self._logger.critical("Control: Control '{}' asserted pin '{}', not valid.".format(self.name, pin_id))
            raise ae

        # Have a pin now, set it up.
        pin = digitalio.Direction.OUTPUT
        return pin

class CtrlSingle(Control):
    """
    Control class for a single GPIO pin.
    """
    def __init__(self, id, name, pin, publish_time, addr=None, invert=False,
                 awboard=None, icon="mdi:toy-brick", log_level=adafruit_logging.WARNING, **kwargs):
        super().__init__(id, name, icon, publish_time, log_level)
        self._invert = invert

        try:
            if awboard is not None:
                self._pin = self._setup_pin_aw9523(awboard, pin)
            else:
                self._pin = self._setup_pin_onboard(pin)
        except (AssertionError, AttributeError, ValueError) as e:
            raise e

        # Set self to off.
        self.set('off')



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
        else:
            self._logger.warning(f"Control: ID '{self.name}' received unknown set value '{value}'")
            print(f"Control: ID '{self.name}' received unknown set value '{value}'")

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

class CtrlNull(Control):
    """
    Null control class. When we need a control to exist but not do anything.
    """
    def __init__(self, id, name):
        super().__init__(id, name)

    def set(self, value):
        self._logger.debug(f"Null control set to '{value}'")

    def icon(self):
        return self._icon

    def status(self):
        return 'Unavailable'

    def callback(self, client, topic, message):
        """
        Callback does nothing.
        """
        pass
