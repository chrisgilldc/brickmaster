#!/usr/bin/python3
# BrickMaster2 Executor for CircuitPython Boards

import brickmaster2
import microcontroller
import os
import time
import traceback

print("Brickmaster2 - {}".format(brickmaster2.__version__))

# Check for the WIFI HW environment setting.
try:
    wifihw = os.getenv("WIFI_HW")
    print("Wireless hardware pre-defined as '{}'".format(wifihw))
except AttributeError:
    wifihw = brickmaster2.util.determine_wifi_hw()

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
    wifihw=wifihw
)

# Create the BrickMaster2 Object.
bm2 = brickmaster2.BrickMaster2(config_json=config_json, mac_id=wifi_obj.wifi_mac, wifi_obj=wifi_obj)

try:
    # Run it.
    bm2.run()
except KeyboardInterrupt:
    print("Received keyboard interrupt. Cleaning up.")
    bm2.cleanup_and_exit(message="User requested exit from keyboard.")
except brickmaster2.exceptions.BM2FatalError as fe:
    traceback.print_exception(fe)
    print("Encountered fatal error. Will not restart.")
except Exception as e:
    print("Received unhandled exception - ")
    traceback.print_exception(e)
    print("Waiting for 30s before.")
    time.sleep(30)
    microcontroller.reset()