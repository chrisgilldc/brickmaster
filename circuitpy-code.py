"""
Brickmaster Startup for Circuitpython boards
"""

import brickmaster
import microcontroller
import os
import time
import traceback
# import sys

print("Brickmaster2 - {}".format(brickmaster.__version__))

# Define a pin to use for System Status.
sysrun_pin = "D0"

if sysrun_pin is not None:
    try:
        sysrun_ctrl = brickmaster.controls.CtrlSingle('sysrun', 'System Status', None, sysrun_pin, 15)
    except (KeyError, TypeError):
        print(f"No pin defined for status LED '{id}'. Will proceed without indicator.")
        sysrun_ctrl = brickmaster.controls.CtrlNull('sysrun_null', 'System Status Null', None)
    except AttributeError:
        print(f"System Status LED pin '{sysrun_pin}' cannot be configured on board. Will proceed without indicator.")
        sysrun_ctrl = brickmaster.controls.CtrlNull('sysrun_null', 'System Status Null', None)
    # Turn it on.
    sysrun_ctrl.set('on')
else:
    sysrun_ctrl = None

# Check for the WIFI HW environment setting.
try:
    wifihw = os.getenv("BRICKMASTER_WIFI_HW")
    print("Wireless hardware pre-defined as '{}'".format(wifihw))
except AttributeError:
    print("Wireless hardware not specified, auto-determining.")
    wifihw = brickmaster.util.determine_wifi_hw()

# Check for a hostname
try:
    hostname = os.getenv("CIRCUITPY_WEB_INSTANCE_NAME")
    print("Hostname/Instance name set to: {}".format(hostname))
except AttributeError:
    print("Hostname not available. Set with 'CIRCUITPY_WEB_INSTANCE_NAME' in 'settings.toml'.")
    hostname = None

# Open the config file.
#TODO: Replace this with fancier config open logic.
print("Loading 'config.json'")
config_json = brickmaster.util.load_config('config.json')
print("Loaded data is:")
print(config_json)

print("Setting up wireless interface...")
# Create the WiFi Object
wifi_obj = brickmaster.network.BMWiFi(
    ssid=os.getenv("CIRCUITPY_WIFI_SSID"),
    password=os.getenv("CIRCUITPY_WIFI_PASSWORD"),
    wifihw=wifihw,
    hostname = hostname
)

# Create the Brickmaster Object.
bm2 = brickmaster.Brickmaster(config_json=config_json, mac_id=wifi_obj.wifi_mac, wifi_obj=wifi_obj,
                                sysrun=sysrun_ctrl)

try:
    # Run it.
    bm2.run()
except KeyboardInterrupt:
    print("Received keyboard interrupt. Cleaning up.")
    sysrun_ctrl.set('off')
    bm2.cleanup_and_exit(message="User requested exit from keyboard.")
except brickmaster.exceptions.BMFatalError as fe:
    traceback.print_exception(fe)
    sysrun_ctrl.set('off')
    print("Encountered fatal error. Will not restart.")
except BaseException as e:
    # Reset the board on any exception not handled lower down. This is a wonky hack but prevents the system from hanging
    # forever.
    sysrun_ctrl.set('off')
    print("Received unhandled exception - ")
    traceback.print_exception(e)
    print("Exception type: {}".format(type(e)))
    print("Waiting for 30s before.")
    time.sleep(30)
    microcontroller.reset()