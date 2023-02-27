# BrickMaster2 Display Control

import adafruit_logging as logger
from .segment_format import number_7s, time_7s
from adafruit_ht16k33.segments import BigSeg7x4, Seg7x4
import time
from datetime import datetime

class Display():
    def __init__(self, config, i2c_bus):
        # Create a logger
        self._logger = logger.getLogger('BrickMaster2')
        # Save the config.
        self._config = config

        # Save the I2C bus object.
        self._i2c_bus = i2c_bus

        # Save our name for easy reference.
        self.name = self._config['name']
        # Create a display object.
        self._display_obj = self._create_object(type=self._config['type'], address=self._config['address'])
        # test it!
        self._test()

    def show(self, input, dtelement='time', clkhr=12):
        if isinstance(input, float) or isinstance(input, int):
            # Integers and floats we can just display.
            self._display_obj.print(input)
        elif isinstance(input, datetime):
            if clkhr not in (12, 24):
                # Clock must be either 12 or 24 hours.
                raise ValueError("Clock hours must be either '12' or 24'. Instead got {}. Are you on Mars?".format(clkhr))
            if dtelement == 'date':
                self._display_obj.print(input.strftime('%m.%d'))
                # Make sure AM/PM is off, if we're a big segment.
                if isinstance(self._display_obj, BigSeg7x4):
                    self._display_obj.ampm = False
            else:
                # Default is time, so assume any other input wants it to be time.
                # Print the string.
                if clkhr == 24:
                    self._display_obj.print(input.strftime('%H:%M'))
                else:
                    self._display_obj.print(input.strftime('%I:%M'))
                # If we're a big display, we can set an AM/PM indicator.
                if isinstance(self._display_obj, BigSeg7x4):
                    if input.strftime('%p') == 'PM':
                        self._display_obj.ampm = True
                    else:
                        self._display_obj.ampm = False

        else:
            raise ValueError("Segment display input must get an integer, float or datetime object. Instead got {}"
                             .format(type(input)))

    # Method to show whatever the displays idle state is.
    def show_idle(self):
        # Known idle states!
        if self._config['when_idle'] == 'time':
            self.show(datetime.now())
        elif self._config['when_idle'] == 'date':
            self.show(datetime.now(), dtelement='date')
        else:
            # There's probably a more elegant way to do this that's faster. Look to optimize later.
            self.off()

    # Method to turn the display off. Clears all values and indicators.
    def off(self):
        self._display_obj.fill(0)
        if isinstance(self._display_obj, Seg7x4):
            self._display_obj.colon = False
        if isinstance(self._display_obj, BigSeg7x4):
            self._display_obj.ampm = False
            self._display_obj.top_left_dot = False
            self._display_obj.bottom_left_dot = False
            self._display_obj.colons[0] = False
            self._display_obj.colons[1] = False


    def _create_object(self, type, address):
        if type == 'bigseg7x4':
            display_class = BigSeg7x4
        elif type == 'seg7x4':
            display_class = Seg7x4
        else:
            raise ValueError("{} is not a valid display type.".format(type))

        # Create the object.
        display_obj = display_class(i2c=self._i2c_bus, address=address)
        return display_obj

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
        self._display_obj.fill(0)