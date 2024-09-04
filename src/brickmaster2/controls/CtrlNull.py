"""
Brickmaster Control - Null
"""

import adafruit_logging
import brickmaster2.controls.BaseControl as BaseControl
import board
import digitalio

class CtrlNull(BaseControl):
    """
    Null control class. When we need a control to exist but not do anything.
    """
    def __init__(self, id, name, core):
        super().__init__(id, name, core)

    def set(self, value):
        self._logger.debug(f"Null control set to '{value}'")

    def icon(self):
        return self._icon

    def status(self):
        return 'Unavailable'

    def callback(self, client, topic, message):
        """
        Callback does nothing.
        """
        pass