"""
Brickmaster Segmented Displays
"""

import time
from adafruit_ht16k33.segments import BigSeg7x4, Seg7x4
from .BaseDisplay import BaseDisplay
from brickmaster.time import BMDateTime

class BMDisplaySeg(BaseDisplay):
    def __init__(self, disp_id, name, address, type, idle_show, idle_brightness, writable, i2c_bus, logger,
                 icon="mdi:clock-digital"):
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
        :param writable: Is this display settable via MQTT?
        :type writable: bool
        :param i2c_bus: I2C bus object, usually created by the core.
        :type i2c_bus: busio.I2C
        :param icon: Icon to use for discovery.
        :type icon: str
        :param loggger: Logger to use. If one is not provided, a new one will be created at the DEBUG level.
        :type logger: adafruit_logging.Logger
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
            self._display_obj.show()
        except ValueError:
            self._logger.warning("Could not send input to display. Not a valid type.")
        else:
            self._status=True
            self._showing=the_input

    def show_dt(self, dtinput, dtelement='time4', clkhr=12):
        """
        Send date or time to the display.

        :param dtinput: The datetime to display
        :type dtinput: datetime.datetime
        :param dtelement: Should date or time be sent? 'time' or 'date', defaults to time.
        :type dtelement: str
        :param clkhr: Use either 12 or 24 hour time.
        :type clkhr: int
        """
        if dtelement == 'date':
            self._showing = self._format_dt(dtinput, field='date')
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
            self._showing = self._format_dt(dtinput, field='time4', clkhr=clkhr)
            self._display_obj.print(self._showing)
            # If we're a big display, we can set an AM/PM indicator.
            if isinstance(self._display_obj, BigSeg7x4):
                self._display_obj.ampm = self._check_pm(dtinput)
        self._status = True

    # Method to show whatever the displays idle state is.
    def show_idle(self, dtinput=None):
        """
        Show the display's idle state. Idle will be whatever is defined in the configuration.

        :param dtinput: Datetime to be used when showing a date or time.
        :type dtinput: datetime.datetime
        """
        # Known idle states!
        if self._idle_show in ('time4', 'time6'):
            self.show_dt(dtinput)
            self._display_obj.brightness = self._idle_brightness
        elif self._idle_show == 'date':
            self.show_dt(dtinput, dtelement='date')
            self._display_obj.brightness = self._idle_brightness
        else:
            # There's probably a more elegant way to do this that's faster. Look to optimize later.
            self.off()
            self._showing=None
        self._display_obj.show()

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
        self._display_obj.show()
        self._showing = None
        self._status = False

    @staticmethod
    def _format_dt(dtinput, field=None, clkhr=12):
        """
        Format the date or time from a datetime for a segmented display.
        This is a simple implementation since Circuitpython doesn't support strftime.

        :param dtinput: The datetime to format. This is not Timezone aware, so make sure it's in the correct timezone already.
        :type dtinput: datetime.datetime
        :param field: The field to extract. May be 'date', 'time4' for hh:mm or 'time6' for hh:mm:ss.
        :type field: str
        :param clkhr: Type of clock to use, '12' hr or '24'hr.
        :type clkhr: int
        """
        if field not in ('date', 'time4', 'time6'):
            raise ValueError("{} not a valid formatting field.".format(field))
        if clkhr not in (12, 24):
            raise ValueError("Clock modes can only be 12 or 24 hours.")

        return_val = None
        if field == 'date':
            return_val = f"{dtinput.month:{0}>{2}}" + "." + f"{dtinput.day:{0}>{2}}"
        elif field in ('time4', 'time6'):
            # Common time actions
            hour = dtinput.hour
            if clkhr == 12 and dtinput.hour > 12:
                hour -= 12
            # 4-cell time, Hour-Minute.
            if field == 'time4':
                return_val = f"{hour:{0}>{2}}" + ":" + f"{dtinput.minute:{0}>{2}}"
            # 6-cell time, Hour-Minute-Seconds.
            elif field == 'time6':
                return_val = f"{hour:{0}>{2}}" + ":" + f"{dtinput.minute:{0}>{2}}" + ":" + f"{dtinput.second:{0}>{2}}"
        return return_val

    def _check_pm(self, dtinput):
        """
        Check if a Time is before or after noon to set AM/PM indicator.

        :param dtinput: The datetime to check.
        :type dtinput: adafruit_datetime.datetime
        """

        if dtinput.hour >= 12:
            pm = True
        else:
            pm = False

        return pm


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
        display_obj.auto_write = False
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