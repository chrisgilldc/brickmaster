"""
Brickmaster Base Display Class
"""

import adafruit_logging
# from .segment_format import number_7s, time_7s
# from adafruit_ht16k33.segments import Seg7x4, BigSeg7x4
import time

# from brickmaster.time import BMDateTime

class BaseDisplay:
    """
    Brickmaster Base Display Class
    """
    def __init__(self, disp_id, name, address, icon, i2c_bus, writable, tz=None, logger=None):
        """
        Base initialization for a Display.

        :param disp_id: Display ID.
        :type disp_id: str
        :param name: Name of the Display.
        :type name: str
        :param address: Address of the display on the I2C bus.
        :type name: number
        :param icon: Icon to use for discovery
        :type icon: str
        :param i2c_bus: I2C bus object, usually created by the core.
        :type i2c_bus: busio.I2C
        :param writable: Is this display settable via MQTT?
        :type writable: bool
        :param tz: When showing time and date, timezone to use. Name should be a valid IANA timezone.
        :param tz: str
        :param loggger: Logger to use. If one is not provided, a new one will be created at the DEBUG level.
        :type logger: adafruit_logging.Logger
        """

        self._logger = logger

        # Save the configuration parameters.
        self._address = address
        self._icon = icon
        self._id = disp_id
        self._name = name
        self._status = False
        self._tz = tz
        self._writable = writable
        # Save the I2C bus object.
        self._i2c_bus = i2c_bus
        # Initialize values.
        # self._bmdt = BMDateTime()
        self._topics = None

    def callback(self, client, topic, message):
        """
        Callback the Network object will call when a subscribed topic gets a message.
        """
        raise NotImplemented("Control callbacks must be implemented in a control subclass.")

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
        return self._id

    @property
    def name(self):
        """
        Long name of the control. Can be descriptive. Used naming entities in Home Assistant discovery.
        """
        return self._name

    def show(self, the_input):
        """
        Put a message on the screen.
        """
        raise NotImplemented("Show method must be implemented on a specific class.")

    @property
    def showing(self):
        """
        What the display is currently showing.
        """
        raise NotImplemented("Showing method must be implemented on a specific class.")

    @property
    def status(self):
        """
        Return the status of the display. This is just if it's on or off.
        """
        return self._status

    @property
    def topics(self):
        """
        List of topics to subscribe to for this control. To be read by the Network object.
        """
        return self._topics

    #@property
    #def tz(self):
    #    """
    #    Timezone for showing time and date.
    #    """
    #    if self._tz is None:
    #        return str(BMDateTime.local_zone)
    #    else:
    #        return self._tz

    def update(self):
        """
        Perform any necessary updates.
        """
        raise NotImplemented("Update method must be implemented by specific class.")

    @property
    def writable(self):
        """
        Should this display be settable via MQTT.
        """
        return self._writable

    def _create_object(self):
        """
        Create the underlying object.
        """
        raise NotImplemented("Display Object creation needs to be overridden by a specific class.")

    def _test(self):
        """
        Test the display, as appropriate.
        """
        raise NotImplemented("Display test should be overridden by a specific class.")
