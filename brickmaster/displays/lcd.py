"""
Brickmaster LCD Display
"""

from .BaseDisplay import BaseDisplay
from adafruit_character_lcd.character_lcd_i2c import Character_LCD_I2C
# from datetime import datetime
import json

class BMDisplayLCD(BaseDisplay):
    def __init__(self, disp_id, name, address, cols, rows, writable, i2c_bus, logger, icon=None):
        """
        Initilize an LCD character display.

        :param disp_id: Display ID.
        :type disp_id: str
        :param name: Name of the Display.
        :type name: str
        :param address: Address of the display on the I2C bus.
        :type name: number
        :param cols: Columns in the display.
        :type cols: int
        :param rows: Rows in the display.
        :type rows: int
        :param icon: Icon to use for discovery.
        :type icon: str
        :param writable: Is this display settable via MQTT?
        :type writable: bool
        :param logger: Logger to use.
        :type logger: adafruit_logging.Logger
        :param i2c_bus: I2C bus object, usually created by the core.
        :type i2c_bus: busio.I2C
        """
        # Call the super class init.
        super().__init__(disp_id=disp_id,
                         name=name,
                         address=address,
                         icon=icon,
                         writable=writable,
                         logger=logger,
                         i2c_bus=i2c_bus)

        # Save additional parameters
        self._cols = cols
        self._rows = rows

        # Import the charachter_lcd library
        # try:
        #     import adafruit_character_lcd.character_lcd_i2c
        # except ImportError as ie:
        #     raise ie

        # Create the display object.
        self._display_obj = self._create_object(cols=self._cols, rows=self._rows,
                                                address=self._address)
    def clear(self):
        """
        Clear the display without turning off.
        """
        self._display_obj.clear()

    def off(self):
        """
        Turn off the display, clear all elements.
        """
        self._logger.info("Display ({}): Turning off.".format(self._id))
        # self._display_obj.clear()
        self._display_obj.backlight = False

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
        """ LCDs don't show idle. Skip it."""
        pass

    @property
    def showing(self):
        """
        What is currently on the display.
        Note this will not take into account any text shifting that has been done.
        """
        return self._display_obj.message

    @property
    def status(self):
        """
        What is the current status of the display? We use the backlight as a proxy for this.
        """
        return self._display_obj.backlight

    # def show_idle(self):
    #     """
    #     Show the display's idle state.
    #     """
    #     # Known idle states!
    #     if self._idle_show == 'time':
    #         time_string = datetime.strftime(datetime.now(), "%-I:%M:%S %p").center(self._display_obj.columns," ")
    #         self.show(time_string)
    #     elif self._idle_show == 'date':
    #         date_string = datetime.strftime(datetime.now(), "%-m/%d/%y").center(self._display_obj.columns," ")
    #         self.show(date_string)
    #     elif self._idle_show == 'datetime':
    #         date_string = datetime.strftime(datetime.now(), "%-m/%d/%y").center(self._display_obj.columns," ")
    #         time_string = datetime.strftime(datetime.now(), "%-I:%M:%S %p").center(self._display_obj.columns," ")
    #         self.show("{}\n{}".format(time_string, date_string))
    #     else:
    #         self.off()


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
        # Explicitly set the backlight off.
        obj.backlight = False
        return obj

    def callback(self, client, topic, message):
        """
        Receive messages from the MQTT broker to set the display.
        """

        if isinstance(message, str):
            # MiniMQTT (Circuitpython) outputs a straight string.
            message_text = message
        else:
            # Paho MQTT (linux) delivers a message object from which we need to extract the payload.
            # Convert the message payload (which is binary) to a string.
            message_text = str(message.payload, 'utf-8')
        input = json.loads(message_text)
        self._logger.info("Display ({}): Received message '{}'".format(self.id, input))
        # Clear by default, or if
        if 'clear' in input:
            if input['clear']:
                self.clear()
        else:
            self.clear()
        if 'message' in input:
            self.show(input['message'])
        if 'backlight' in input:
            self._display_obj.backlight=input['backlight']
