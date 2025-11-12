"""
Brickmaster Startup for Circuitpython boards
"""

import adafruit_logging
import brickmaster
import microcontroller
import os
import time
import traceback
# import sys

print("Brickmaster2 - {}".format(brickmaster.__version__))

# Define a pin to use for System Status.
sysrun_pin = "D32"

# Set up logger
logger = adafruit_logging.getLogger('Brickmaster')
print_handler = adafruit_logging.StreamHandler()
logger.addHandler(print_handler)
# Start out at the DEBUG level. The Config module will load the log level
# From the config file and adjust appropriately.
logger.setLevel(adafruit_logging.DEBUG)

if sysrun_pin is not None:
    # try:
    sysrun_ctrl = brickmaster.controls.CtrlSingle('sysrun', 'System Status', None, sysrun_pin, 15, logger=logger)
    # except (KeyError, TypeError):
    #     print(f"No pin defined for status LED '{id}'. Will proceed without indicator.")
    #     sysrun_ctrl = brickmaster.controls.CtrlNull('sysrun_null', 'System Status Null', None, None)
    # except AttributeError:
    #     print("System Status LED pin '{}' cannot be configured on board. Will proceed without indicator.".
    #           format(sysrun_pin))
    #     sysrun_ctrl = brickmaster.controls.CtrlNull('sysrun_null', 'System Status Null', None, None)
    # Turn it on.
    sysrun_ctrl.set('on')
else:
    # If no sysrun pin, create a null control.
    sysrun_ctrl = brickmaster.controls.CtrlNull('sysrun_null', 'System Status Null', None, None)

# Check for the WIFI HW environment setting.
try:
    wifihw = os.getenv("BRICKMASTER_WIFI_HW")
    logger.info("Wireless hardware pre-defined as '{}'".format(wifihw))
except AttributeError:
    logger.warning("Wireless hardware not specified, auto-determining.")
    wifihw = brickmaster.util.determine_wifi_hw()

# Check for a hostname
try:
    hostname = os.getenv("CIRCUITPY_WEB_INSTANCE_NAME")
    logger.info("Hostname/Instance name set to: {}".format(hostname))
except AttributeError:
    logger.warning("Hostname not available. Set with 'CIRCUITPY_WEB_INSTANCE_NAME' in 'settings.toml'.")
    hostname = None

# Open the config file.
#TODO: Replace this with fancier config open logic.
logger.info("Loading 'config.json'")
config_json = brickmaster.util.load_config('config.json')
logger.debug("Loaded data is:")
logger.debug(config_json)

print("Setting up wireless interface...")
# Create the WiFi Object
wifi_obj = brickmaster.network.BMWiFi(
    ssid=os.getenv("CIRCUITPY_WIFI_SSID"),
    password=os.getenv("CIRCUITPY_WIFI_PASSWORD"),
    wifihw=wifihw,
    hostname = hostname,
    logger=logger
)

# Create the Brickmaster Object.
bm = brickmaster.Brickmaster(config_json=config_json, mac_id=wifi_obj.wifi_mac, wifi_obj=wifi_obj,
                                sysrun=sysrun_ctrl, logger=logger)

try:
    # Run it.
    bm.run()
except KeyboardInterrupt:
    logger.warning("Received keyboard interrupt. Cleaning up.")
    sysrun_ctrl.set('off')
    bm.cleanup_and_exit(message="User requested exit from keyboard.")
except ReloadException:
    logger.warning("File updated on board. Restarting...")
    sysrun_ctrl.set('off')
    bm.cleanup_and_exit(message="File updated on board.")
except brickmaster.exceptions.BMFatalError as fe:
    traceback.print_exception(fe)
    sysrun_ctrl.set('off')
    logger.critical("Encountered fatal error. Will not restart.")
except BaseException as e:
    # Reset the board on any exception not handled lower down. This is a wonky hack but prevents the system from hanging
    # forever.
    sysrun_ctrl.set('off')
    logger.critical("Received unhandled exception - ")
    traceback.print_exception(e)
    logger.info("Exception type: {}".format(type(e)))
    logger.info("Waiting for 30s before resetting.")
    time.sleep(30)
    microcontroller.reset()