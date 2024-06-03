"""
Brickmaster2
"""

# Controls
from . import controls
# Network
from . import network
# Scripts
from . import scripts
# # Utility methods.
from . import util

# Unitary Classes from files

from .core import BrickMaster2
from .config import BM2Config
from .display import Display
from .version import __version__

# Exception types
class BM2RecoverableError(Exception):
    """
    BrickMaster2 error that may be fixable by resetting the system.
    """
    pass

class BM2FatalError(Exception):
    """
    BrickMaster2 error that cannot be fixed by resetting the system.
    """
    pass

# Constants
# These mirror the errors from adafruit_minimqtt.

MQTT_ERROR_INCORRECT_PROTOCOL = 1
MQTT_ERROR_ID_REJECTED = 2
MQTT_ERROR_SERVER_UNAVAILABLE = 3
MQTT_ERROR_INCORECT_USERNAME_PASSWORD = 4
MQTT_ERROR_UNAUTHORIZED = 5

ERRORS={
    MQTT_ERROR_INCORRECT_PROTOCOL: "Connection Refused - Incorrect Protocol Version",
    MQTT_ERROR_ID_REJECTED: "Connection Refused - ID Rejected",
    MQTT_ERROR_SERVER_UNAVAILABLE: "Connection Refused - Server unavailable",
    MQTT_ERROR_INCORECT_USERNAME_PASSWORD: "Connection Refused - Incorrect username/password",
    MQTT_ERROR_UNAUTHORIZED: "Connection Refused - Unauthorized",
}