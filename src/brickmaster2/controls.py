"""
Brickmaster2 Control Object definitions
"""

import adafruit_logging
import board
import digitalio
import sys


# class Control:
#     """
#     Base control object.
#     """
#     def __init__(self, id, name, core, icon="mdi:toy-brick", publish_time=15, log_level=adafruit_logging.WARNING):
#         """
#         Base control initialization.
#
#         @param id: Short ID for the control. No spaces!
#         @type id: str
#         @param name: Long name for the control
#         @type name: str
#         @param core: Reference to the Brickmaster core object.
#         @type core: object
#         @param icon:
#         @type icon: str
#         @param publish_time:
#         @type publish_time: int
#         @param log_level: Logging level to use for the control. Technically an int, should be a valid adafruit_logging
#         constant.
#         @type log_level: int
#
#         """
#         # Save inputs.
#         # Set the ID.
#         self._id = id
#         # Set the Name.
#         self._control_name = name
#         # Save the reference back to the core.
#         self._core = core
#         self._icon = icon
#         self._publish_time = publish_time
#
#         # Initialize
#         self._topics = None
#         self._status = None
#
#         # Create a logger with the specified logger.
#         self._logger = adafruit_logging.getLogger('BrickMaster2')
#         self._logger.setLevel(log_level)
#
#
#     @property
#     def topics(self):
#         """
#         List of topics to subscribe to for this control. To be read by the Network object.
#         """
#         return self._topics
#
#     @property
#     def status(self):
#         """
#         Current status of the control.
#         """
#         raise NotImplemented("Status must be implemented in a control subclass")
#
#     def set(self, value):
#         """
#         Set the control to a given value. Usually "on" or "off" or "true" or "false"
#         """
#         raise NotImplemented("Set must be implemented in a control subclass")
#
#     @property
#     def name(self):
#         """
#         Long name of the control. Can be descriptive. Used naming entities in Home Assistant discovery.
#         """
#         return self._control_name
#
#     @property
#     def id(self):
#         """
#         ID of the control. Used internally and to create entity IDs in Home Assistant discovery.
#         """
#         return self._id
#
#     def callback(self, client, topic, message):
#         """
#         Callback the Network object will call when a subscribed topic gets a message.
#         """
#         raise NotImplemented("Control callbacks must be implemented in a control subclass.")
#
#     def _setup_pins(self, pindef, extio_id=None):
#         """
#         Set up a pin or set of pins.
#
#         @param pindef: Pin definition. See README for pin definition syntax.
#         @type pindef: list
#         @param extio_id: External board (AW9523) ID to use. If None, will use pins on the microcontroller.
#         @type extio_id: str
#         @return: list
#         """
#         # latching = {"on": "D21", "off": "D22"}
#         # flasher = ["D21", "D22", "D23"]
#         # single = "D21"
#
#         pins = []
#         for pin_pair in pindef:
#             # Initialize a dictionary for this pin pair.
#             pin_dict = {}
#             for key in ('on','off'):
#                 # if extio_id is None:
#                 # Get a pin from the controller.
#                 try:
#                     pin = digitalio.DigitalInOut(getattr(board, str(pin_pair[key])))
#                 except AttributeError as ae:
#                     self._logger.critical(f"Control: Control '{self.name}' references non-existent pin '{pin_pair[key]}'.")
#                     raise ae
#                 except ValueError as ve:
#                     # Using an in-use pin will return a ValueError.
#                     self._logger.critical(f"Control: Control '{self.name}' uses pin '{pin_pair[key]}' which is already in use!")
#                     raise ve
#                 # Set the pin to an output
#                 pin.direction = digitalio.Direction.OUTPUT
#                 # else:
#                 #     pass
#                 # Put the pin in the output dict.
#                 pin_dict[key] = pin
#             # Add the pin dict to the pins list.
#             pins.append(pin_dict)
#         self._logger.debug("Control: For control '{self.name}', assembled pins '{pins}'")
#         return pins


    # def _setup_pin_onboard(self, pin_id):
    #     """
    #     Creates a pin located directly on the controller.
    #
    #     :param pin_id: ID of the onboard pin to create
    #     :type pin_id: str
    #     :return: microcontroller.Pin
    #     """
    #     # Have the import. Now create the pin.
    #     try:
    #         pin = digitalio.DigitalInOut(getattr(board, str(pin_id)))
    #     except AttributeError as ae:
    #         self._logger.critical(f"Control: Control '{self.name}' references non-existent pin '{pin_id}'.")
    #         raise ae
    #     except ValueError as ve:
    #         # Using an in-use pin will return a ValueError.
    #         self._logger.critical("Control: Control '{self.name}' uses pin '{pin_id}' which is already in use!")
    #         raise ve
    #     # Set the pin to an output
    #     pin = digitalio.Direction.OUTPUT
    #     return pin

    # # Method to set up GPIO via an AW9523 on I2C.
    # def _setup_pin_aw9523(self, awboard, pin_id):
    #     """
    #     Set up a pin located on an I2C attached AW9523 expander.
    #
    #     :param awboard: AW9523 object.
    #     :type awboard: adafruit_aw9523.AW9523
    #     :param pin_id: ID of the AW9523 pin to create (0-15)
    #     :type pin_id: int
    #     :return: microcontroller.Pin
    #     """
    #     try:
    #         pin = awboard.get_pin(pin_id)
    #     except AssertionError as ae:
    #         self._logger.critical("Control: Control '{}' asserted pin '{}', not valid.".format(self.name, pin_id))
    #         raise ae
    #
    #     # Have a pin now, set it up.
    #     pin = digitalio.Direction.OUTPUT
    #     return pin

# class CtrlSingle(Control):
#     """
#     Control class for a single GPIO pin.
#     """
#     def __init__(self, id, name, core, pindef, publish_time, addr=None, invert=False,
#                  extio_obj=None, icon="mdi:toy-brick", log_level=adafruit_logging.WARNING, **kwargs):
#         super().__init__(id, name, core, icon, publish_time, log_level)
#         self._invert = invert
#
#         self._pins = self._setup_pins(pindef)
#
#         # try:
#         #     if awboard is not None:
#         #         self._pin = self._setup_pin_aw9523(awboard, pin)
#         #     else:
#         #         self._pin = self._setup_pin_onboard(pin)
#         # except (AssertionError, AttributeError, ValueError) as e:
#         #     raise e
#
#         # Set self to off.
#         self.set('off')
#
#
#     def set(self, value):
#         self._logger.info("Control: Setting control '{}' to '{}'".format(self.name, value))
#         if value.lower() == 'on':
#             if self._invert:
#                 self._logger.debug("Control: Control is inverted, 'On' state sets low.")
#                 self._pin.value = False
#             else:
#                 self._pin.value = True
#         elif value.lower() == 'off':
#             if self._invert:
#                 self._logger.debug("Control: Control is inverted, 'Off' state sets high.")
#                 self._pin.value = True
#             else:
#                 self._pin.value = False
#         else:
#             self._logger.warning(f"Control: ID '{self.name}' received unknown set value '{value}'")
#             print(f"Control: ID '{self.name}' received unknown set value '{value}'")
#
#     @property
#     def icon(self):
#         return self._icon
#
#     @property
#     def status(self):
#         if self._pin.value is True:
#             if self._invert:
#                 return 'OFF'
#             else:
#                 return 'ON'
#         elif self._pin.value is False:
#             if self._invert:
#                 return 'ON'
#             else:
#                 return 'OFF'
#         else:
#             return 'Unavailable'
#
#     def callback(self, client, topic, message):
#         """
#         Control Callback
#
#         :param client: Client instance for the callback.
#         :param topic: Topic the message was received on.
#         :param message: Message.
#         :return: None
#         """
#         print("Control: Incoming message is '{}' ({})".format(message, type(message)))
#         if isinstance(message, str):
#             # MiniMQTT (Circuitpython) outputs a straight string.
#             message_text = message.lower()
#         else:
#             # Paho MQTT (linux) delivers a message object from which we need to extract the payload.
#             # Convert the message payload (which is binary) to a string.
#             message_text = str(message.payload, 'utf-8').lower()
#         self._logger.debug("Control: Control '{}' ({}) received message '{}'".format(self.name, self.id,
#                                                                                      message_text))
#         valid_values = ['on', 'off']
#         # If it's not a valid option, just ignore it.
#         if message_text not in valid_values:
#             self._logger.info("Control: Control '{}' ({}) received invalid command '{}'. Ignoring.".
#                               format(self.name, self.id, message_text))
#         else:
#             self.set(message_text)

# class CtrlLatching(Control):
#     """
#     Control for when on and off are separate pins, as in a latching relay.
#     """
#     def __init__(self, id, name, core, pindef, publish_time, invert=False,
#                  extio_obj=None, icon="mdi:toy-brick", log_level=adafruit_logging.WARNING, **kwargs):
#         super().__init__(id, name, core, icon, publish_time, log_level)

# class CtrlFlasher(Control):
#     """
#     Control to handle flashing across multiple pins.
#     """
#     def __init__(self, id, name, core, pindef, publish_time, addr=None, invert=False,
#                  extio_obj=None, icon="mdi:toy-brick", log_level=adafruit_logging.WARNING, **kwargs):
#         super().__init__(id, name, core, icon, publish_time, log_level)


# class CtrlNull(Control):
#     """
#     Null control class. When we need a control to exist but not do anything.
#     """
#     def __init__(self, id, name, core):
#         super().__init__(id, name, core)
#
#     def set(self, value):
#         self._logger.debug(f"Null control set to '{value}'")
#
#     def icon(self):
#         return self._icon
#
#     def status(self):
#         return 'Unavailable'
#
#     def callback(self, client, topic, message):
#         """
#         Callback does nothing.
#         """
#         pass


# class CtrlSingleOld(Control):
#     """
#     Control class for a single GPIO pin.
#     """
#     def __init__(self, id, name, core, pindef, publish_time, addr=None, invert=False,
#                  extio_obj=None, icon="mdi:toy-brick", log_level=adafruit_logging.WARNING, **kwargs):
#         super().__init__(id, name, core, icon, publish_time, log_level)
#         self._invert = invert
#
#         self._pins = self._setup_pins(pindef)
#
#         # try:
#         #     if awboard is not None:
#         #         self._pin = self._setup_pin_aw9523(awboard, pin)
#         #     else:
#         #         self._pin = self._setup_pin_onboard(pin)
#         # except (AssertionError, AttributeError, ValueError) as e:
#         #     raise e
#
#         # Set self to off.
#         self.set('off')
#
#
#     def set(self, value):
#         self._logger.info("Control: Setting control '{}' to '{}'".format(self.name, value))
#         if value.lower() == 'on':
#             if self._invert:
#                 self._logger.debug("Control: Control is inverted, 'On' state sets low.")
#                 self._pin.value = False
#             else:
#                 self._pin.value = True
#         elif value.lower() == 'off':
#             if self._invert:
#                 self._logger.debug("Control: Control is inverted, 'Off' state sets high.")
#                 self._pin.value = True
#             else:
#                 self._pin.value = False
#         else:
#             self._logger.warning(f"Control: ID '{self.name}' received unknown set value '{value}'")
#             print(f"Control: ID '{self.name}' received unknown set value '{value}'")
#
#     @property
#     def icon(self):
#         return self._icon
#
#     @property
#     def status(self):
#         if self._pin.value is True:
#             if self._invert:
#                 return 'OFF'
#             else:
#                 return 'ON'
#         elif self._pin.value is False:
#             if self._invert:
#                 return 'ON'
#             else:
#                 return 'OFF'
#         else:
#             return 'Unavailable'
#
#     def callback(self, client, topic, message):
#         """
#         Control Callback
#
#         :param client: Client instance for the callback.
#         :param topic: Topic the message was received on.
#         :param message: Message.
#         :return: None
#         """
#         print("Control: Incoming message is '{}' ({})".format(message, type(message)))
#         if isinstance(message, str):
#             # MiniMQTT (Circuitpython) outputs a straight string.
#             message_text = message.lower()
#         else:
#             # Paho MQTT (linux) delivers a message object from which we need to extract the payload.
#             # Convert the message payload (which is binary) to a string.
#             message_text = str(message.payload, 'utf-8').lower()
#         self._logger.debug("Control: Control '{}' ({}) received message '{}'".format(self.name, self.id,
#                                                                                      message_text))
#         valid_values = ['on', 'off']
#         # If it's not a valid option, just ignore it.
#         if message_text not in valid_values:
#             self._logger.info("Control: Control '{}' ({}) received invalid command '{}'. Ignoring.".
#                               format(self.name, self.id, message_text))
#         else:
#             self.set(message_text)

