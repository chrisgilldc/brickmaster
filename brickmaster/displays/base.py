"""
Brickmaster Base Display Class
"""

import adafruit_logging as logger
# from .segment_format import number_7s, time_7s
# from adafruit_ht16k33.segments import Seg7x4, BigSeg7x4
import time

class BM2Display:
    """
    Brickmaster Base Display Class
    """
    def __init__(self, config, i2c_bus):
        """

        """

        # Create a logger
        self._logger = logger.getLogger('Brickmaster')
        # Save the config.
        self._config = config

        # Save the I2C bus object.
        self._i2c_bus = i2c_bus

        # Save our name for easy reference.
        self.name = self._config['name']

    def show(self, the_input):
        """
        Put a message on the screen.
        """
        raise NotImplemented("Show method must be implemented on a specific class.")


    def _create_object(self):
        """
        Create the underlying object.
        """
        raise NotImplemented("Display Object creation needs to be overridden by a specific class.")

    def _test(self):
        """
        Test the display, as appropriate.
        """
        raise NotImplemented("Display test should be overridden by a specific class.")
