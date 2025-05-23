"""
Brickmaster Display System
"""

import adafruit_logging as logger
# from .segment_format import number_7s, time_7s
from adafruit_ht16k33.segments import Seg7x4, BigSeg7x4
import time

class Display:
    """
    Brickmaster Display Class
    Create once per display.
    """
    def __init__(self, config, i2c_bus):

        # Import the ht16k33 library when required.
        try:
            from adafruit_ht16k33.segments import BigSeg7x4, Seg7x4
        except ImportError as ie:
            raise ie

        # Create a logger
        self._logger = logger.getLogger('Brickmaster')
        # Save the config.
        self._config = config

        # Save the I2C bus object.
        self._i2c_bus = i2c_bus

        # Save our name for easy reference.
        self.name = self._config['name']
        # Create a display object.
        self._display_obj = self._create_object(disptype=self._config['type'], address=self._config['address'])
        # test it!
        self._test()

    def show(self, the_input):
        """
        Send text to the display.
        """
        try:
            self._display_obj.print(the_input)
        except ValueError:
            self._logger.warning("Could not send input to display. Not a valid type.")

    def show_dt(self, dtelement='time', clkhr=12):
        """
        Send date or time to the display.

        :param dtelement: Should date or time be sent? 'time' or 'date', defaults to time.
        :type dtelement: str
        :param clkhr: Use either 12 or 24 hour time.
        :type clkhr: int
        """
        if dtelement == 'date':
            self._display_obj.print(self._format_dt(field='date'))
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
            self._display_obj.print(self._format_dt(field='time', clkhr=clkhr))
            # If we're a big display, we can set an AM/PM indicator.
            if isinstance(self._display_obj, BigSeg7x4):
                self._display_obj.ampm = self._format_dt('pm')

    # Method to show whatever the displays idle state is.
    def show_idle(self):
        """
        Show the display's idle state. Idle will be whatever is defined in the configuration.
        """
        # Known idle states!
        if self._config['idle']['show'] == 'time':
            self.show_dt()
            self._display_obj.brightness = self._config['idle']['brightness']
        elif self._config['idle']['show'] == 'date':
            self.show_dt(dtelement='date')
            self._display_obj.brightness = self._config['idle']['brightness']
        else:
            # There's probably a more elegant way to do this that's faster. Look to optimize later.
            self.off()

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
            # self._logger.debug("Display: Setting first colon off off.")
            self._display_obj.colons[0] = False
            # self._logger.debug("Display: Setting second colon off.")
            self._display_obj.colons[1] = False

    def _create_object(self, disptype, address):
        if disptype == 'bigseg7x4':
            display_class = BigSeg7x4
        elif disptype == 'seg7x4':
            display_class = Seg7x4
        else:
            raise ValueError("{} is not a valid display type.".format(disptype))

        # Create the object.
        display_obj = display_class(i2c=self._i2c_bus, address=address)
        return display_obj

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
            date_val = str(time.localtime().tm_mon).rjust(2) + "." + str(time.localtime().tm_mday).rjust(2)
            return date_val
        if field == 'time':
            hour = time.localtime().tm_hour
            if clkhr == 12 and hour > 12:
                hour -= 12
            time_val = str(hour).rjust(2) + ":" + str(time.localtime().tm_min).rjust(2, '0')
            return time_val
        if field == 'pm':
            if time.localtime().tm_hour >= 12:
                ampm_val = True
            else:
                ampm_val = False
            return ampm_val

    def _test(self, delay=0.1):
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
