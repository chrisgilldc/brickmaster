"""
Brickmaster NTP Client

This is the Adafruit NTP library with a few extra features, wrapped as a class.
"""

import adafruit_logging
import adafruit_ntp
import rtc
import time

class BMNTP:
    """
    Brickmaster NTP class. Only used on Circitpython. Rely on the system time service on a general-purpose OS.
    """
    def __init__(self, timeservers, tz, recheck, bmwifi, logger=None):
        """
        :param timeservers: List of timeservers to try. Will be tried in-order. Can be IPs or hostnames.
        :type timeservers: list
        :param tz: A timezone
        :type tz: int
        :param recheck: How often to recheck the time, in minutes.
        :type recheck: int
        :param bmwifi: The Brickmaster Wifi object.
        :type bmwifi: brickmaster.network.bmwifi.BMWiFi
        """

        self._active_timeserver = 0
        self._bmwifi = bmwifi
        self._ntp_client = None
        self._recheck = recheck * 60
        self._rtc = rtc.RTC()
        self._timeservers = timeservers
        self._timezone = tz
        self._update_timestamp = None

        self._logger = logger
        self._logger.info("Network (NTP): Configured NTP with timeservers '{}', timezone '{}', recheck every {}m".
                          format(self._timeservers, self._timezone, self._recheck))

    def poll(self):
        """
        Perform periodic polling actions. This will see if it's time recheck time with the NTP server.
        """
        if self._update_timestamp is None:
            self._logger.info("Network (NTP): Time not yet set, setting clock from network.")
            self.set_clock()
        elif time.monotonic() - self._update_timestamp >= self._recheck:
            self._logger.info("Network (NTP): Recheck time expired. Setting clock from network.")
            self.set_clock()

    def set_clock(self):
        """
        Set the RTC based on an NTP response.
        """
        try:
            self._rtc.datetime = self.get_datetime()
        except ValueError:
            self._logger.error("Network (NTP): Exhausted all configured timeservers while trying to set RTC.")
        except BaseException as be:
            self._logger.critical("Network (NTP): Encountered unexpected exception while trying to set RTC '{}'".
                                  format(be))
        else:
            self._update_timestamp = time.monotonic()
            self._logger.info("Network (NTP): Updated RTC time to '{}'".format(
                self._format_datetime(self._rtc.datetime)))


    def get_datetime(self):
        """
        Get the datetime from the active timeserver.
        """
        result = None

        i = 0
        while result is None:
            self._ntp_client = adafruit_ntp.NTP(self._bmwifi.socket_pool,
                                                server=self._timeservers[self._active_timeserver])
            try:
                result = self._ntp_client.datetime
            except OSError as oe:
                if oe.strerror == 'ETIMEDOUT':
                    self._logger.warning("Network (NTP): Timeserver '{}' timed out.".
                                         format(self._timeservers[self._active_timeserver]))
                    if self._active_timeserver > len(self._timeservers):
                        self._active_timeserver = 0
                    else:
                        self._active_timeserver += 1
                    i += 1
                    if i > len(self._timeservers):
                        self._logger.error("Time: All timeservers tried, none succeeded.")
                        raise ValueError
                else:
                    raise oe

        return result

    @staticmethod
    def _format_datetime(datetime):
        """
        Format datetime for output. Circuitpython doesn't have a native strftime.
        """
        return "{:02}/{:02}/{} {:02}:{:02}:{:02}".format(
            datetime.tm_mon,
            datetime.tm_mday,
            datetime.tm_year,
            datetime.tm_hour,
            datetime.tm_min,
            datetime.tm_sec
        )


    @property
    def timeserver_active(self):
        """
        Timeserver currently selected
        """
        return self._timeservers[self._active_timeserver]

    @property
    def timeservers(self):
        """
        Configured timeservers.
        """
        return self._timeservers