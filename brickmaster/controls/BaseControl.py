"""
Brickmaster Base Control
"""
import adafruit_logging
# import board
# import digitalio
# from brickmaster.gpio import EnhancedDigitalInOut


class BaseControl:
    """
    Base control object.
    """
    def __init__(self, ctrl_id, name, core, icon="mdi:toy-brick", publish_time=15, log_level=adafruit_logging.WARNING):
        """
        Base control initialization.

        @param ctrl_id: Short ID for the control. No spaces!
        @type ctrl_id: str
        @param name: Long name for the control
        @type name: str
        @param core: Reference to the Brickmaster core object.
        @type core: object
        @param icon:
        @type icon: str
        @param publish_time:
        @type publish_time: int
        @param log_level: Logging level to use for the control. Technically an int, should be a valid adafruit_logging
        constant.
        @type log_level: int

        """
        # Save inputs.
        # Set the ID.
        self._ctrl_id = ctrl_id
        # Set the Name.
        self._control_name = name
        # Save the reference back to the core.
        self._core = core
        self._icon = icon
        self._publish_time = publish_time

        # Initialize
        self._topics = None
        self._status = None

        # Create a logger with the specified logger.
        self._logger = adafruit_logging.getLogger('Brickmaster')
        self._logger.setLevel(log_level)
        self._logger.debug("Control {}: Set icon to '{}'".format(self._ctrl_id, self._icon))

    @property
    def topics(self):
        """
        List of topics to subscribe to for this control. To be read by the Network object.
        """
        return self._topics

    @property
    def status(self):
        """
        Current status of the control. Should return ON or OFF.

        return str
        """
        raise NotImplemented("Status must be implemented in a control subclass.")

    def set(self, value: str):
        """
        Set the control to a boolean value.
        """
        raise NotImplemented("Control setting must be implemented in a subclass.")

    @property
    def name(self):
        """
        Long name of the control. Can be descriptive. Used naming entities in Home Assistant discovery.
        """
        return self._control_name

    @property
    def icon(self):
        """
        The defined icon for the control.
        """
        return self._icon

    @property
    def id(self):
        """
        ID of the control. Used internally and to create entity IDs in Home Assistant discovery.
        """
        return self._ctrl_id

    def callback(self, client, topic, message):
        """
        Callback the Network object will call when a subscribed topic gets a message.
        """
        raise NotImplemented("Control callbacks must be implemented in a control subclass.")
