####
#
# BRICKMASTER
#
####

## Summary

A (Circuit)Python application for controlling relays and devices. The most important of which are, of course, Legos.

* [Installation Instructions](INSTALL.md)
* [Configuration File Reference](CONFIG.md)

### Project Goals
* Provide a common interface for a variety of devices
* Be able to do cool automations with connected devices (ie: Saturn 5 launch simulation)
* Teach myself some more Python (and hardware, and MQTT)

## Supported Platforms

* Raspberry Pi OS (Bookworm) - Specifically on the Pi Zero W. Other Pis should work just fine, just aren't tested.
* CircuitPython 9 - CircuitPython 8 is no longer being tested.
  * [Adafruit Metro M4 Airlift](https://www.adafruit.com/product/4000) - Default pystack size on this board is 1536, which should be raised to at least 
  * 4096. Given notable memory limitations of this board I may stop testing in the near 
  future. Requires a pystack value of at least 4096, possibly more depending on your control configuration. The ESP32 line or possibly the Metro M7 Airlift would be recommended instead.
  * [Adafruit ESP32 Feather v2](https://www.adafruit.com/product/5400)

Feature set is intended to be 1:1 between CPython and CircuitPython. Documentation notes where this is not true due to
platform limitations.

## v0.7 Target Features
- Load config from a remote site.
- Remote reload command to reset (and load new config!)
- Actual Sphinx documentation

## V0.6 Target Features
- Option to load config from a remote site (ie: web directory) - Nope, moving to v0.7
- Package for PyPi and Circup.
- Control options
  - ~~Multi-pin controls.~~ Done!
  - ~~Groups to wrap multiple controls together.~~ - Dropped. Probably better to group through Home Assistant.
  - ~~Flasher option.~~ Done!
  - ~~Multiple AW9523 expanders~~ Tested, works! Note, still can't mix pins across sources for a single control.

## Latest Updates - V0.5.1
- Debugged issues with client reconnection when the broker goes away (ie: restarts)
- Discovery and Status messages are now retained, which allows devices/entities and their status to be maintained across
HA restarts. No more disappearing devices.
- Added new MQTT 'log' option to control logging of the base MQTT client. This is a deep debug option, should really
only be needed for debugging.
- Fixed indicator LEDs - those broke at some point - and rewrote them to use CtrlGPIO control objects for consistency.
- Included and tested example systemd units for Linux installs.
- Updated CircuitPython 'code.py' startup file to be smarter and behave as a parallel to the cli invoker on Linux.
- Reorganized with an eye towards packaging. Will learn how to do that at some point.
- Cleaned up some settings and updated documentation.
 
## Latest Updates - V0.5.0
Having struggled with CircuitPython/Adafruit-MiniMQTT stability issues, I have refactored the whole network module and
split based on platform.
Brickmaster2 on linux will now use the very robust [PAHO MQTT](https://eclipse.dev/paho/index.php?page=clients/python/index.php),
which I also use in my other project, [CobraBay](https://github.com/chrisgilldc/cobrabay).
This leads to some code bloat. Notes on how to deploy based on platform are below.




