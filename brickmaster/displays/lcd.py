"""
Brickmaster LCD Display
"""

from .base import BM2Display
from adafruit_character_lcd.character_lcd_i2c import Character_LCD_I2C
from datetime import datetime

class BM2DisplayLCD(BM2Display):
    def __init__(self, config, i2c_bus):
        # Call the super class init.
        super().__init__(config, i2c_bus)

        # Import the charachter_lcd library
        # try:
        #     import adafruit_character_lcd.character_lcd_i2c
        # except ImportError as ie:
        #     raise ie

        # Create the display object.
        self._display_obj = self._create_object(cols=self._config['cols'], rows=self._config['rows'],
                                                address=self._config['address'])

    def show(self, the_input, clear=False):
        """
        Send text to the display. Any old output will be cleared.
        Be sure the new input is formatted for the display size, no automatic checking will be done.
        """
        # Should we clear the display first?
        if clear:
            self._display_obj.clear()
        # Display the new message.
        self._display_obj.message = the_input
        # Oddly, sending the message sometimes turns the backlight off. So make sure it's on.
        self._display_obj.backlight = True

    def show_idle(self):
        """
        Show the display's idle state.
        """
        # Known idle states!
        if self._config['idle']['show'] == 'time':
            time_string = datetime.strftime(datetime.now(), "%-I:%M:%S %p").center(self._display_obj.columns," ")
            self.show(time_string)
        elif self._config['idle']['show'] == 'date':
            date_string = datetime.strftime(datetime.now(), "%-m/%d/%y").center(self._display_obj.columns," ")
            self.show(date_string)
        elif self._config['idle']['show'] == 'datetime':
            date_string = datetime.strftime(datetime.now(), "%-m/%d/%y").center(self._display_obj.columns," ")
            time_string = datetime.strftime(datetime.now(), "%-I:%M:%S %p").center(self._display_obj.columns," ")
            self.show("{}\n{}".format(time_string, date_string))
        else:
            self.off()

    def clear(self):
        """
        Clear the display without turning off.
        """
        self._display_obj.clear()

    def off(self):
        """
        Turn off the display, clear all elements.
        """
        self._display_obj.clear()
        self._display_obj.backlight = False

    def _create_object(self, cols, rows, address):
        """
        Create a new LCD object.
        """
        self._logger.debug("Trying to setup display on i2c bus: {}".format(self._i2c_bus))
        self._logger.debug("Address: {} ({})".format(address, type(address)))
        self._logger.debug("Columns: {} ({})".format(cols, type(cols)))
        self._logger.debug("Rows: {} ({})".format(rows, type(rows)))
        obj = Character_LCD_I2C(
            i2c=self._i2c_bus,
            columns=cols,
            lines=rows,
            address=address)
        self._logger.debug("Returning object: {}".format(obj))
        return obj



