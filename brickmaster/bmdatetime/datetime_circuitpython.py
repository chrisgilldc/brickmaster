"""
Brickmaster Time management for Circuitpython
"""

import adafruit_datetime
import adafruit_logging
import sys

class BMDateTimeCircuitpython():
    """
    Brickmaster Date and Time class for Circuitpython
    """

    # Class variables.
    known_timezones = {}  # Stores known timezones. Used for CircuitPython
    local_zone = 'Etc/UTC'  # Local timezone, defaults to UTC.

    def __init__(self, logger=None):
        """
        Create the time object.
        :param logger: Logger to use. Will create one if not passed.
        :type logger: adafruit_logging.Logger
        """

        if logger is None:
            self._logger = adafruit_logging.getLogger("Brickmaster")
            self._logger.setLevel(adafruit_logging.DEBUG)
        else:
            self._logger = logger

    def now(self, tz='local'):
        """
        Get the current datetime in the local timezone.
        """
        if tz == 'local':
            pass
        else:
            pass

    def tzconvert(self, datetime, tz):
        """
        Convert a given datetime into another timezone.
        """
        raise NotImplemented("Must be implemented in a specific class.")

    def setlocaltz(self, tz):
        """
        Set the local timezone for the system.

        :param tz: Any valid IANA Timezone.
        :type tz: str
        """
        raise NotImplemented("Must be implemented in a specific class.")

    def setknowntz(self, tz, offset):
        """
        Set a known timezone to a given offset.

        :param tz: Any valid IANA Timezone
        :type tz: str
        :param offset: Offset from UTC.
        :type offset: float
        """

