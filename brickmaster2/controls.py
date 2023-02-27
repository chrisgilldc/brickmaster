# Brickmaster2 Controls
import adafruit_logging as logger
import sys

class Control:
    def __init__(self, config):
        # Create a logger.
        self._logger = logger.getLogger('BrickMaster2')
        # Save the config. This will have already been validated!
        self._config = config
        # We access the name a lot, so make it easy to access.
        self.name = self._config['name']
        self._topics = None
        self._status = None
        # Create topics for the control. This must be implemented per subclass.
        self._create_topics()

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
        return self._name

    @name.setter
    def name(self, name):
        self._name = name

    # Create topics. Each subclass should create its own control topics appropriate to its operating method.
    def _create_topics(self):
        raise NotImplemented("Create Topics must be implemented in a control subclass")

    # Callback the network will access to get messages to this control.
    def callback(self, client, topic, message):
        raise NotImplemented("Control callbacks must be implemented in a control subclass.")

# Control class for GPIO
class CtrlGPIO(Control):
    def __init__(self, config):
        super().__init__(config)
        # Import the Adafruit Board module
        try:
            import board
            from digitalio import DigitalInOut, Direction
        except ImportError:
            self._logger.critical("Cannot import modules for GPIO control. Exiting!")
            sys.exit(1)
        # Have the import. Now create the pin.
        try:
            self._pin = DigitalInOut(getattr(board, str(self._config['pin'])))
        except AttributeError:
            self._logger.critical("Control '{}' references pin '{}', does not exist. Existing!".
                                  format(self.name, self._config['pin']))
            sys.exit(1)
        # Set the pin to an output
        self._pin.direction = Direction.OUTPUT
        # Set the pin to off, to be sure.
        self._pin.value = False

    def set(self, value):
        self._logger.debug("Setting control '{}' to '{}'".format(self.name, value))
        if value == 'on':
            self._pin.value = True
        elif value == 'off':
            self._pin.value = False

    @property
    def status(self):
        if self._pin.value is True:
            return 'On'
        elif self._pin.value is False:
            return 'Off'
        else:
            return 'Unavailable'

    def callback(self, client, topic, message):
        # Convert the message payload (which is binary) to a string.
        self._logger.debug("Control '{}' received message '{}'".format(self.name, message))
        valid_values = ['on', 'off']
        # If it's not a valid option, just ignore it.
        if message.lower() not in valid_values:
            self._logger.info("Control '{}' received invalid command '{}'. Ignoring.".
                              format(self.name, message))
        else:
            self.set(message)

    # GPIO topic creation.
    def _create_topics(self):
        self._topics = [
            {
                'topic': self.name + '/set',
                'type': 'inbound',
                'values': ['on', 'off']  # Values an inbound topic will consider valid.
            },
            {
                'topic': self.name + '/status',
                'type': 'outbound',
                'retain': False,  # Should this be retained? False is almost always the right choice.
                'repeat': False,  # Should this be sent, even if the value doesn't change?
                'obj': self,  # Object to reference to get value. Should really always be 'self' to pass a reference to this object.
                'value_attr': 'status'  # What attribute to try to get?
            }
        ]

    # Topics property.
    @property
    def topics(self):
        return self._topics

# Control class for Lego Power Functions (IR)
class CtrlPowerFunctions(Control):
    def __init__(self, config):
        super().__init__(config)
        raise NotImplemented("Power Functions is not yet implemented")


# Control class for Lego Powered Up (Bluetooth)
class CtrlPoweredUp(Control):
    def __init__(self, config):
        super().__init__(config)
        raise NotImplemented("Powered Up is not yet implemented")
