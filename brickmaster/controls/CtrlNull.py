"""
Brickmaster Control - Null
"""

# import adafruit_logging
from .BaseControl import BaseControl
# import board
# import digitalio

class CtrlNull(BaseControl):
    """
    Null control class. When we need a control to exist but not do anything.
    """
    def __init__(self, ctrl_id, name, core, logger):
        """
        Null control. Goes Nowhere, Does Nothing.

        @param ctrl_id: Short ID for the control. No spaces!
        @type ctrl_id: str
        @param name: Long name for the control
        @type name: str
        @param core: Reference to the Brickmaster core object.
        @type core: object
        @param logger: Logger object.
        @type logger: adafruit_logging.Logger
        """
        super().__init__(ctrl_id, name, core, logger)

    def set(self, value):
        self._logger.debug(f"Null control set to '{value}'")

    def status(self):
        return 'Unavailable'

    def callback(self, client, topic, message):
        """
        Callback does nothing.
        """
        pass