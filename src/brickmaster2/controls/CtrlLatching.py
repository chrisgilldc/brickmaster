"""
Brickmaster Control - Latching
"""
import adafruit_logging
from .BaseControl import BaseControl
import board
import digitalio

class CtrlLatching(BaseControl):
    """
    Control for when on and off are separate pins, as in a latching relay.
    """
    def __init__(self, id, name, core, pindef, publish_time, invert=False,
                 extio_obj=None, icon="mdi:toy-brick", log_level=adafruit_logging.WARNING, **kwargs):
        super().__init__(id, name, core, icon, publish_time, log_level)

        # Set up the pins!
        self._pins = self._setup_pins(pindef)
        if len(self._pins) > 1:
            raise ValueError("Control: CtrlLatching may not have more than one pin-pair defined!")

        # Set self to off. Always start off when initialized.
        self.set('off')

