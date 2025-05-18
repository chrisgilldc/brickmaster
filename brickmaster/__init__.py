"""
Brickmaster2
"""

# Controls
from . import controls
# GPIO
from . import gpio
# Network
from . import network
# Scripts
from . import scripts
# Sensors
from . import sensors
# # Utility methods.
from . import util

# Unitary Classes from files
from .core import Brickmaster
from .config import BM2Config
from .display import Display
from . import exceptions
from .version import __version__

# Constants
# These mirror the errors from adafruit_minimqtt.

# MQTT_ERROR_INCORRECT_PROTOCOL = 1
# MQTT_ERROR_ID_REJECTED = 2
# MQTT_ERROR_SERVER_UNAVAILABLE = 3
# MQTT_ERROR_INCORRECT_USERNAME_PASSWORD = 4
# MQTT_ERROR_UNAUTHORIZED = 5
#
# ERRORS={
#     MQTT_ERROR_INCORRECT_PROTOCOL: "Connection Refused - Incorrect Protocol Version",
#     MQTT_ERROR_ID_REJECTED: "Connection Refused - ID Rejected",
#     MQTT_ERROR_SERVER_UNAVAILABLE: "Connection Refused - Server unavailable",
#     MQTT_ERROR_INCORRECT_USERNAME_PASSWORD: "Connection Refused - Incorrect username/password",
#     MQTT_ERROR_UNAUTHORIZED: "Connection Refused - Unauthorized",
# }