"""
Brickmaster Base Sensor
"""
import adafruit_logging

class BaseSensor:
    """
    Base Sensor object.
    """
    def __init__(self, sensor_id, name, core, icon="mdi:toy-brick", publish_time=15, logger=None):
        """
        Base Sensor initialization.

        @param sensor_id: Short ID for the control. No spaces!
        @type sensor_id: str
        @param name: Long name for the control
        @type name: str
        @param core: Reference to the Brickmaster core object.
        @type core: object
        @param icon:
        @type icon: str
        @param publish_time:
        @type publish_time: int
        @param logger: Logger to use. If one is not provided, a new one will be created at the DEBUG level.
        @type logger: adafruit_logging.Logger

        """
        # Save inputs.
        # Set the ID.
        self._sensor_id = sensor_id
        # Set the Name.
        self._sensor_name = name
        # Save the reference back to the core.
        self._core = core
        self._icon = icon
        self._publish_time = publish_time

        # Initialize
        self._topics = None
        self._status = None

        # Create a logger with the specified logger.
        if logger is None:
            self._logger = adafruit_logging.getLogger('Brickmaster')
            self._logger.setLevel(adafruit_logging.DEBUG)
        else:
            self._logger = logger

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

    @property
    def name(self):
        """
        Long name of the control. Can be descriptive. Used naming entities in Home Assistant discovery.
        """
        return self._sensor_name

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
        return self._sensor_id
