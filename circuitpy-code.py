#!/usr/bin/python3
# BrickMaster2 Executor for CircuitPython Boards

import brickmaster2
import microcontroller
import os
import time
import traceback
import sys

print("Brickmaster2 - {}".format(brickmaster2.__version__))

# Define a pin to use for System Status.
sysrun_pin = "D0"

if sysrun_pin is not None:
    try:
        sysrun_ctrl = brickmaster2.controls.CtrlSingle('sysrun', 'System Status', sysrun_pin, 15)
    except (KeyError, TypeError):
        print(f"No pin defined for status LED '{id}'. Will proceed without indicator.")
        sysrun_ctrl = brickmaster2.controls.CtrlNull('sysrun_null', 'System Status Null')
    except AttributeError:
        print(f"System Status LED pin '{sysrun_pin}' cannot be configured on board. Will proceed without indicator.")
        sysrun_ctrl = brickmaster2.controls.CtrlNull('sysrun_null', 'System Status Null')
    # Turn it on.
    sysrun_ctrl.set('on')

# Check for the WIFI HW environment setting.
try:
    wifihw = os.getenv("BRICKMASTER_WIFI_HW")
    print("Wireless hardware pre-defined as '{}'".format(wifihw))
except AttributeError:
    print("Wireless hardware not specified, auto-determining.")
    wifihw = brickmaster2.util.determine_wifi_hw()

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
config_json = brickmaster2.util.load_config('config.json')
print("Loaded data is:")
print(config_json)

print("Setting up wireless interface...")
# Create the WiFi Object
wifi_obj = brickmaster2.network.BM2WiFi(
    ssid=os.getenv("CIRCUITPY_WIFI_SSID"),
    password=os.getenv("CIRCUITPY_WIFI_PASSWORD"),
    wifihw=wifihw,
    hostname = hostname
)

# Create the BrickMaster2 Object.
bm2 = brickmaster2.BrickMaster2(config_json=config_json, mac_id=wifi_obj.wifi_mac, wifi_obj=wifi_obj,
                                sysrun=sysrun_ctrl)

try:
    # Run it.
    bm2.run()
except KeyboardInterrupt:
    print("Received keyboard interrupt. Cleaning up.")
    sysrun_ctrl.set('off')
    bm2.cleanup_and_exit(message="User requested exit from keyboard.")
except brickmaster2.exceptions.BM2FatalError as fe:
    traceback.print_exception(fe)
    sysrun_ctrl.set('off')
    print("Encountered fatal error. Will not restart.")
except Exception as e:
    sysrun_ctrl.set('off')
    print("Received unhandled exception - ")
    traceback.print_exception(e)
    print("Exception type: {}".format(type(e)))
    print("Waiting for 30s before.")
    time.sleep(30)
    microcontroller.reset()