# NTP methods.
# There are some support issues with this on the M4 Airlift I'm testing on, so stashing this away for now.

# def _setup_ntp(self):
#     # Only set up NTP if a server is defined, and we're not a general-purpose Linux system.
#     # If we're general-purpose linux, assume the OS is handling the clock.
#     self._ntp_updated = 0
#     if self._config['ntp_server'] is not None:
#         import rtc
#         import adafruit_ntp
#         from adafruit_datetime import datetime
#         from tzdb import timezone
#         import adafruit_esp32spi.adafruit_esp32spi_socket as socket
#
#         # Set the socket interface.
#         socket.set_interface(self._esp)
#
#         # Create the NTP instance. Use UTC.
#         self._ntp = adafruit_ntp.NTP(socket, server=self._config['ntp_server'], tz_offset=0)
#         testtime = self._ntp.datetime
#         self._logger.info("NTP test returned: {}".format(testtime))
#
# def _set_clock(self):
#     # Only reset the clock if:
#     # 1. An NTP server is set.
#     # 2. The system is  CircuitPython board, vs. a general-purpose OS.
#     # 3. six hours have passed since the previous update.
#     if self._config['ntp_server'] is not None \
#             and os.uname().sysname.lower() != 'linux'\
#             and time.monotonic() - self._ntp_updated >= 21600:
#         utc_now = datetime.fromtimestamp(self._ntp.datetime)
#         localtime = utc_now + timezone(self._config['tz']).utcoffset(utc_now)
#         self._logger.info("Setting local clock to: {}".format(localtime))
#         rtc.RTC().datetime = localtime
#         self._ntp_updated = time.monotonic()