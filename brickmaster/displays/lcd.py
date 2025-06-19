"""
Brickmaster LCD
"""
import brickmaster.effects
from .BaseDisplay import BaseDisplay
from adafruit_character_lcd.character_lcd_i2c import Character_LCD_I2C
import json

class BMDisplayLCD(BaseDisplay):
    def __init__(self, disp_id, name, address, cols, rows, writable, i2c_bus, logger, icon=None):
        """
        Initialize an LCD character display.

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
        :param writable: Is this display settable via MQTT?
        :type writable: bool
        :param i2c_bus: I2C bus object, usually created by the core.
        :type i2c_bus: busio.I2C
        :param logger: Logger to use. If one is not provided, a new one will be created at the DEBUG level.
        :type logger: adafruit_logging.Logger
        :param icon: Icon to use for discovery.
        :type icon: str
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

        # Initialize parameters
        self._original_message = None # Original message as submitted.
        self._full_message = [] # Full message as submitted.
        self._active_effects = [] # Any effects.
        self._showing = None # What is showing on the screen right now!

        # Import the character_lcd library
        # try:
        #     import adafruit_character_lcd.character_lcd_i2c
        # except ImportError as ie:
        #     raise ie

        # Create the display object.
        self._display_obj = self._create_object(cols=self._cols, rows=self._rows,
                                                address=self._address)
        self._display_obj.backlight = False

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
            message_text = str(message.payload.decode('utf-8'))
        self._logger.debug("Display ({}): Received payload - '{}'".format(self.id, message.payload))
        self._logger.debug("Display ({}): UTF-8 decoded payload - '{}' ".format(self.id, message_text))
        self._logger.debug("Display ({}): Type is {}".format(self.id, type(message_text)))
        try:
            self._received_payload = json.loads(message_text)
        except json.decoder.JSONDecodeError:
            self._logger.warning("Display ({}): JSON payload does not decode. Will ignore.".format(self._id))
        else:
            self._logger.debug("Display ({}): Received message '{}'".format(self.id, self._received_payload))
            self._logger.debug("Display ({}): Message type is - {}".format(self.id, type(self._received_payload)))
            for element in self._received_payload['message']:
                self._logger.info("Display ({}): Message element '{}' is type {}".format(self.id, element, type(element)))

            # Clear by default, or if
            if 'clear' in self._received_payload:
                if self._received_payload['clear']:
                    self.clear()
            else:
                self.clear()

            if 'backlight' in self._received_payload:
                self._display_obj.backlight=self._received_payload['backlight']

            if 'message' in self._received_payload:
                try:
                    self._process_display_instructions(self._received_payload)
                except BaseException:
                    self._logger.warning("Display ({}): Invalid command found. Ignoring.".format(self._id))
                else:
                    self.update()

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
        self._display_obj.clear()
        self._showing = ""
        self._display_obj.backlight = False

    def show(self, the_input, clear=True):
        """
        Send text to the display. Any old output will be cleared.
        Be sure the new input is formatted for the display size, no automatic checking will be done.
        """
        # Should we clear the display first?
        if clear:
            self._display_obj.clear()
        # Display the new message.
        if isinstance(the_input, list):
            the_input = "\n".join(the_input)
        self._display_obj.message = the_input
        # Oddly, sending the message sometimes turns the backlight off. So make sure it's on.
        self._display_obj.backlight = True

    def show_idle(self, dtinput=None):
        """ LCDs don't show idle. Skip it."""
        pass

    @property
    def showing(self):
        """
        What is currently on the display.
        Note this will not take into account any text shifting that has been done.
        """
        return self._showing

    @property
    def status(self):
        """
        What is the current status of the display? We use the backlight as a proxy for this.
        """
        return self._display_obj.backlight

    def update(self):
        """
        Update any automatic effects.
        """
        for effect in self._active_effects:
            effect.update()

        output_list = []
        # self._logger.info("Display ({}): Full message is type {}".format(self._id, type(self._full_message)))
        for row in self._full_message:
            if issubclass(type(row), brickmaster.effects.BaseEffect):
                output_list.append(self._lcd_format(row.showing))
            # if isinstance(row, brickmaster.effects.HorizontalScroll):
            #     output_list.append(str(row))
            else:
                output_list.append(self._lcd_format(row))

        output_text = "\n".join(output_list)

        if output_text != self._showing:
            self._showing = output_text
            self.show(output_text, clear=False)


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

    def _process_display_instructions(self, the_instructions):
        """
        Process LCD display instructions

        :param the_instructions: The instructions to process.
        :type the_instructions: dict
        :returns: Initial display message, effects tracking initialization
        :rtype: (str, dict)
        """

        if 'message' not in the_instructions:
            raise ValueError("Display instructions must have a message!")

        # Clear the existing effects.
        self._active_effects = []

        # Save the message.
        self._original_message = the_instructions['message']
        self._full_message = the_instructions['message']

        if 'effects' in the_instructions and isinstance(the_instructions['message'], list):
            if 'vertical-scroll' in the_instructions['effects']:
                # tracking_init['vs_timestamp'] = sync_timestamp
                self._logger.info("Display ({}): Would vertical scroll, but not implemented.".format(self._id))
            if 'horizontal-scroll' in the_instructions['effects']:
                for hsline in the_instructions['effects']['horizontal-scroll']:
                    if isinstance(hsline['target'], int):
                        # Create a Horizontal Scroll object.
                        if hsline['direction'] == 'right':
                            sr = True
                        else:
                            sr = False

                        hs = brickmaster.effects.HorizontalScroll(
                            text=the_instructions['message'][hsline['target']],
                            width=self._cols,
                            scroll_right=sr,
                            animate=hsline['speed']
                        )
                        self._active_effects.append(hs)
                        print("Full message has {} entries.".format(len(self._full_message)))
                        print("Full message: {}".format(self._full_message))
                        self._full_message[hsline['target']] = hs
                    elif isinstance(hsline['target'], list):
                        for target in hsline['target']:
                            if hsline['direction'] == 'right':
                                sr = True
                            else:
                                sr = False

                            hs = brickmaster.effects.HorizontalScroll(
                                text=the_instructions['message'][hsline['target']],
                                width=self._cols,
                                scroll_right=sr,
                                animate=hsline['speed']
                            )
                            self._active_effects.append(hs)
                            self._full_message[target] = hs
            if 'rotate' in the_instructions['effects']:

                    for rtline in the_instructions['effects']['rotate']:
                        if isinstance(rtline['target'], int):
                            try:
                                rt = brickmaster.effects.RotateText(
                                    text=the_instructions['message'][rtline['target']],
                                    animate=rtline['speed']
                                )
                                self._active_effects.append(rt)
                                self._full_message[rtline['target']] = rt
                            except IndexError as ie:
                                self._logger.warning(
                                    "Display ({}): Rotate references line ({}) that does not exist. Ignoring entire command.".format(
                                        self._id, rtline['target']))
                                raise ie
                        elif isinstance(rtline['target'], list):
                            for target in rtline['target']:
                                try:
                                    rt = brickmaster.effects.RotateText(
                                        text=the_instructions['message'][target],
                                        animate=rtline['speed']
                                    )
                                    self._active_effects.append(rt)
                                    self._full_message[target] = rt
                                except IndexError as ie:
                                    self._logger.warning(
                                        "Display ({}): Rotate references line ({}) that does not exist. Ignoring entire command.".format(
                                            self._id, target))
                                    raise ie

        # Save the message.
        # self._original_message = the_instructions['message']
        # self._full_message = the_instructions['message']

    def _lcd_format(self, input_line):
        """
        Follow display rules to format a single line. This is for 'standard' formatting, not dynamic 'effects'.

        :param input_line: Input list defining what to show on each row.
        :type input_line: str, int, float, list

        :returns: List of lines, formatted appropriately.
        :rtype: str
        """

        if isinstance(input_line, dict):
            if 'text' not in input_line:
                self._logger.warning("Display ({}): No text specified in payload.".format(self._id))
                text = "No text in line."
            # If alignment command is given.
            if 'align' in input_line:
                if input_line['align'] == 'left':
                    self._logger.debug("Display ({}): Left-aligning text.".format(self.id))
                    # substr = input_line['text'][:self._cols]
                    text = input_line['text'].ljust(self._cols)
                elif input_line['align'] == 'right':
                    self._logger.debug("Display ({}): Right-aligning text.".format(self.id))
                    substr = input_line['text'][self._cols * -1:]
                    text = substr.rjust(self._cols)
                elif input_line['align'] == 'center':
                    self._logger.debug("Display ({}): Centering text.".format(self.id))
                    if len(input_line['text']) > self._cols:
                        overhang = round(( len(input_line['text']) - self._cols ) / 2)
                        text = input_line['text'][overhang:overhang * -1]
                    else:
                        text = input_line['text'].center(self._cols)
                else: #Unknown alignment, ignore it.
                    self._logger.warning("Display ({}): Alignment '{}' not supported.".
                                         format(self._id, input_line['align']))
                    text = input_line['text']
            else:
                self._logger.debug("Display ({}): No alignment provided. Using text directly.".format(self.id))
                text = input_line['text']
        elif type(input_line) in (str, int, float):
            self._logger.debug("Display ({}): Line type is {}, sending directly.".format(self.id, type(input_line)))
            text = str(input_line)
        else:
            self._logger.warning("Display ({}): Can't format '{}' ({})".format(self._id,input_line, type(input_line)))
            text = "Unknown type"
        return text