"""
Brickmaster Time
Provides an abstracted, platform-neutral interface for CPython and Circuitpython
"""
from adafruit_datetime import datetime, timedelta, timezone
import adafruit_logging
import sys

# # Conditional imports based on platform.
# if sys.implementation.name == 'circuitpython':
#     pass
# else:
#     # CPython libraries. Assume linux, since we don't officially support anytihng else.
#     import zoneinfo
#     from datetime import datetime, timedelta, timezone


class BMDateTime():
    """
    Brickmaster Time and Date handling class.
    """

    # Class variables.
    local_zone = 'UTC'  # Local timezone, defaults to UTC.
    UTC = timezone(timedelta(),"UTC") # Pre-baked UTC zone, since UTC is always the same.
    known_timezones = {
        'Etc/UTC': UTC,
        'UTC': UTC
    }  # Stores known timezones. Used for CircuitPython. Pre-loaded with UTC zones.

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
            now_time = datetime.now()
            # if sys.implementation.name == 'circuitpython':
            now_time = now_time.replace(tzinfo=BMDateTime.UTC)
        else:
            pass
        return now_time

    def tzconvert(self, datetime, tz):
        """
        Convert a given datetime into another timezone.
        """


    def setlocaltz(self, tz):
        """
        Set the local timezone for the system.

        :param tz: Any valid IANA Timezone.
        :type tz: str
        """
        if sys.implementation.name == "circuitpython":
            BMDateTime.local_zone = tz
        else:
            self._logger.warning("Time: Local time zone is derived from the system OS. Will not set.")

    def setknowntz(self, tz, offset):
        """
        Set a known timezone to a given offset.

        :param tz: Any valid IANA Timezone
        :type tz: str
        :param offset: Offset from UTC.
        :type offset: float
        """
        if sys.implementation.name == "circuitpython":
            BMDateTime.known_timezones[tz] = offset



    def _gettz(self, tz):
        """
        Get a tzinfo object
        """
        if sys.implementation.name == 'circuitpython':
            try:
                offset = BMDateTime.known_timezones[tz]
            except KeyError as ke:
                self._logger.error("Time: Requested timezone '{}' is not known.")
                raise ke
            return timezone(timedelta(hours=offset), tz)
        else:
            return None


