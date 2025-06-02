"""
Brickmaster Segmented Displays
"""

import time
from adafruit_ht16k33.segments import BigSeg7x4, Seg7x4
from .BaseDisplay import BaseDisplay

class BMDisplaySeg(BaseDisplay):
    def __init__(self, disp_id, name, address, type, idle_show, idle_brightness, writable, i2c_bus, logger, icon="mdi:clock-digital"):
        """
        Initilize an LED segmented display.

        :param disp_id: Display ID.
        :type disp_id: str
        :param name: Name of the Display.
        :type name: str
        :param address: Address of the display on the I2C bus.
        :type name: number
        :param type: Type of segmented display. May be 'bigseg7x4' or 'seg7x4'
        :type type: str
        :param idle_show: What to show when idle. May be "blank", "time" or "date".
        :type idle_show: str
        :param idle_brightness: How bright to be when idle. May be between 0.25 and 1.
        :type rows: float
        :param icon: Icon to use for discovery.
        :type icon: str
        :param i2c_bus: I2C bus object, usually created by the core.
        :type i2c_bus: busio.I2C
        :param writable: Is this display settable via MQTT?
        :type writable: bool
        """

        # Make sure display type is valid.
        if type.lower() not in ('bigseg7x4', 'seg7x4'):
            raise ValueError("Provided display type '{}' is not recognized.".format(type))

        # Call the super class init.
        super().__init__(disp_id=disp_id,
                         name=name,
                         address=address,
                         icon=icon,
                         writable=writable,
                         logger=logger,
                         i2c_bus=i2c_bus)

        # Save additional parameters
        self._idle_brightness = idle_brightness
        self._idle_show = idle_show
        self._showing = None
        self._type = type

        # Import the ht16k33 library
        # try:
        #     from adafruit_ht16k33.segments import BigSeg7x4, Seg7x4
        # except ImportError as ie:
        #     raise ie

        # Create the display object.
        self._display_obj = self._create_object(disptype=self._type, address=self._address)
        # Run a test.
        self._test()

    def show(self, the_input):
        """
        Send text to the display.
        """
        try:
            self._display_obj.print(the_input)
        except ValueError:
            self._logger.warning("Could not send input to display. Not a valid type.")
        else:
            self._status=True
            self._showing=the_input

    def show_dt(self, dtelement='time', clkhr=12):
        """
        Send date or time to the display.

        :param dtelement: Should date or time be sent? 'time' or 'date', defaults to time.
        :type dtelement: str
        :param clkhr: Use either 12 or 24 hour time.
        :type clkhr: int
        """
        if dtelement == 'date':
            self._showing = self._format_dt(field='date')
            self._display_obj.print(self._showing)
            # Make sure AM/PM is off, if we're a big segment.
            if isinstance(self._display_obj, BigSeg7x4):
                self._display_obj.ampm = False
        else:
            if clkhr not in (12, 24):
                # Clock must be either 12 or 24 hours.
                raise ValueError(
                    "Clock hours must be either '12' or 24'. Instead got {}. Are you on Mars?".format(clkhr))
            # Default is time, so assume any other input wants it to be time.
            # Print the string.
            self._showing = self._format_dt(field='time', clkhr=clkhr)
            self._display_obj.print(self._showing)
            # If we're a big display, we can set an AM/PM indicator.
            if isinstance(self._display_obj, BigSeg7x4):
                self._display_obj.ampm = self._format_dt('pm')
        self._status = True

    # Method to show whatever the displays idle state is.
    def show_idle(self):
        """
        Show the display's idle state. Idle will be whatever is defined in the configuration.
        """
        # Known idle states!
        if self._idle_show == 'time':
            self.show_dt()
            self._display_obj.brightness = self._idle_brightness
        elif self._idle_show == 'date':
            self.show_dt(dtelement='date')
            self._display_obj.brightness = self._idle_brightness
        else:
            # There's probably a more elegant way to do this that's faster. Look to optimize later.
            self.off()
            self._showing=None

    @property
    def showing(self):
        """
        What is currently showing on the display
        """
        return self._showing

    def off(self):
        """
        Turn off the display. Clears all elements.
        """
        self._display_obj.fill(False)
        if isinstance(self._display_obj, Seg7x4):
            # self._logger.debug("Display: Setting colon off.")
            self._display_obj.colon = False
        if isinstance(self._display_obj, BigSeg7x4):
            # self._logger.debug("Display: Setting am/pm off.")
            self._display_obj.ampm = False
            # self._logger.debug("Display: Setting top-left dot off.")
            self._display_obj.top_left_dot = False
            # self._logger.debug("Display: Setting bottom-left dot off.")
            self._display_obj.bottom_left_dot = False
            # self._logger.debug("Display: Setting first colon off.")
            self._display_obj.colons[0] = False
            # self._logger.debug("Display: Setting second colon off.")
            self._display_obj.colons[1] = False
        self._showing = None
        self._status = False

    # Create a formatted string to send to displays from localtime.
    # This is a simple implementation since CircuitPython doesn't support datetime with strftime.
    @staticmethod
    def _format_dt(field=None, clkhr=12):
        if field not in ('date', 'time', 'pm'):
            raise ValueError("{} not a valid formatting field.")
        if clkhr not in (12, 24):
            raise ValueError("Clock can only 12 or 24 hours.")

        # Return date in format "mm.dd"
        if field == 'date':
            date_val = f"{time.localtime().tm_mon:{0}>{2}}" + "." + f"{time.localtime().tm_mday:{0}>{2}}"
            return date_val
        if field == 'time':
            hour = time.localtime().tm_hour
            if clkhr == 12 and hour > 12:
                hour -= 12
            time_val = f"{hour:{0}>{2}}" + ":" + f"{time.localtime().tm_min:{0}>{2}}"
            return time_val
        if field == 'pm':
            if time.localtime().tm_hour >= 12:
                ampm_val = True
            else:
                ampm_val = False
            return ampm_val

    def _create_object(self, disptype, address):
        """
        Create the underlying object.
        """
        if disptype == 'bigseg7x4':
            display_class = BigSeg7x4
        elif disptype == 'seg7x4':
            display_class = Seg7x4
        else:
            raise ValueError("{} is not a valid display type.".format(disptype))

        # Create the object.
        display_obj = display_class(i2c=self._i2c_bus, address=address)
        return display_obj

    def _test(self, delay=0.1):
        """
        Test the display.
        """
        for x in range(10):
            self._display_obj.print(str(x) * 4)
            # Flash the dots on even numbers.
            if x % 2 == 0:
                extra_state = True
            else:
                extra_state = False
            if isinstance(self._display_obj, BigSeg7x4):
                self._display_obj.ampm = extra_state
                self._display_obj.bottom_left_dot = extra_state
                self._display_obj.top_left_dot = extra_state
                self._display_obj.colons[0] = extra_state
                self._display_obj.colons[1] = extra_state
            elif isinstance(self._display_obj, Seg7x4):
                self._display_obj.colon = extra_state
            else:
                self._logger.critical("Display has unknown type {}. This should never happen!".
                                      format(type(self._display_obj)))
            time.sleep(delay)
        self._display_obj.fill(False)