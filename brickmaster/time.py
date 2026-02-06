"""
Brickmaster Time
Provides an abstracted, platform-neutral interface for CPython and Circuitpython
"""
import adafruit_logging
import sys

# # Conditional imports based on platform.
if sys.implementation.name == 'circuitpython':
    import adafruit_datetime
else:
     # CPython libraries. Assume linux, since we don't officially support anything else.
     import zoneinfo
     import datetime

class BMDateTime():
    """
    Brickmaster Time and Date handling class.
    """

    # Class Method
    @staticmethod
    def _get_system_tz():
        """
        Read the system timezone by checking the /etc/localtime symlink.

        :returns: Zoneinfo object of the system local timezone.
        :rtype: zoneinfo.ZoneInfo
        """
        import os
        # Easy way is to read /etc/timezone, but not every Linux implementation has that.
        #tzfile = open("/etc/timezone","r")
        #tz = tzfile.read().rstrip()
        tz = os.readlink("/etc/localtime").removeprefix('/usr/share/zoneinfo/')
        zone = zoneinfo.ZoneInfo(tz)
        return zone

    # Class variables.
    # If circuitpython, set class variables.
    if sys.implementation.name ==  'circuitpython':
        local_zone = 'UTC'  # Local timezone, defaults to UTC.
        UTC = adafruit_datetime.timezone(adafruit_datetime.timedelta(hours=0),"UTC") # Pre-baked UTC zone, since UTC is always the same.
        known_timezones = {
            'UTC': UTC
        }  # Stores known timezones. Used for CircuitPython. Pre-loaded with UTC zones.
    else:
       local_zone = _get_system_tz()

    def __init__(self, local_tz=None, logger=None):
        """
        Create the time object.

        :param local_tz: Timezone to be considered as 'local'. This is the default zone to return if one isn't specified.
        :type local_tz: str
        :param logger: Logger to use. Will create one if not passed.
        :type logger: adafruit_logging.Logger
        """

        self._logger = logger

        if local_tz is not None:
            self.setlocaltz(local_tz)

    def now(self, tz='local'):
        """
        Get the current datetime in the local timezone.

        :returns: Datetime of now, in the requested timezone.
        :rtype: datetime.datetime or adafruit_datetime.datetime
        """
        now_time = None
        if tz == 'local':
            if sys.implementation.name == 'circuitpython':
                pass
            else:
                now_time = datetime.datetime.now(BMDateTime.local_zone)
            # now_time = datetime.now()
            # if sys.implementation.name == 'circuitpython':
            # now_time = now_time.replace(tzinfo=BMDateTime.UTC)
        elif tz == 'UTC':
            now_time = datetime.datetime.now(datetime.timezone.utc)
        else:
            now_time = datetime.datetime.now(self.gettz(tz))
        return now_time

    def tzconvert(self, dtinput, tz):
        """
        Convert a given datetime into another timezone.

        :param dtinput: The datetime to convert.
        :type dtinput: datetime.datetime or adafruit_datetime.datetime
        :returns: The datetime converted into the requested timezone. None if the timezone isn't valid.
        :rtype dtinput: datetime.datetime, adafruit_datetime.datetime or None
        """
        if sys.implementation.name == 'circuitpython':
            pass
        else:
            try:
                converted = dtinput.astimezone(self.gettz(tz))
            except zoneinfo.ZoneInfoNotFoundError:
                return dtinput
            else:
                return converted

    def setlocaltz(self, localtz):
        """
        Set the local timezone for the system.

        :param localtz: Any valid IANA Timezone.
        :type localtz: str
        """
        if localtz == 'system':
            if sys.implementation.name == 'circuitpython':
                # Circuitpython should always keep the RTC in UTC.
                self._logger.info("Time: Setting global local timezone to UTC.")
                BMDateTime.local_zone = BMDateTime.UTC
            else:
                # On Linux, use the Class method to grab the system local zone.
                self._logger.info("Time: Setting global local timezone to system timezone.")
                BMDateTime.local_zone = BMDateTime._get_system_tz()
        else:
            self._logger.info("Time: Setting global local timezone to '{}'".format(localtz))
            BMDateTime.local_zone = self.gettz(localtz)

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

    def gettz(self, tz):
        """
        Get a tzinfo object
        """
        self._logger.debug("Time: Get TZ '{}'".format(tz))
        if sys.implementation.name == 'circuitpython':
            try:
                offset = BMDateTime.known_timezones[tz]
                self._logger.debug("Time: Retrieved offset '{}' for TZ '{}'".format(offset, tz))
                return offset
            except KeyError as ke:
                self._logger.error("Time: Requested timezone '{}' is not known.")
                raise ke
        else:
            # On CPython (presuambly Linux), get the zone from Zoneinfo
            try:
                zone = zoneinfo.ZoneInfo(tz)
            except zoneinfo.ZoneInfoNotFoundError as zinf:
                self._logger.error("Time: Requested Timezone '{}' not found.".format(tz))
                raise zinf
            else:
                return zone


