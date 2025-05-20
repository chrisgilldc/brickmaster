####
#
# BRICKMASTER
#
####

## Summary

A (Circuit)Python application for controlling relays and devices. The most important of which are, of course, Legos.

* [Installation Instructions](INSTALL.md)
* [Configuration File Reference](CONFIG.md)

### Basic Features

* Allows control of outputs in two modes:
  * "Single", your bog-standard 'on' and 'off'
  * "Flasher", which alternates on and off as configured when turned on.
* Sends sensor status updates
  * Currently only supports the HTU31D temperature/humidity sensor. I'm using two as an add-on to an Octopi.
* Provides Home Assistant integration

### Project Goals
* Provide a common interface for a variety of devices
* Be able to do cool automations with connected devices (ie: Saturn 5 launch simulation)
* Teach myself some more Python (and hardware, and MQTT)

## Supported Platforms

* Raspberry Pi OS - Tested on the Pi Zero and Pi 4. Others should work fine.
* CircuitPython 9 - CircuitPython 8 is no longer being tested.
  * [Adafruit Metro M4 Airlift](https://www.adafruit.com/product/4000) - Default pystack size on this board is 1536, which should be raised to at least 4096. Given notable memory limitations of this board I may stop testing in the near 
future. Requires a pystack value of at least 4096, possibly more depending on your control configuration. The ESP32 line or possibly the Metro M7 Airlift would be recommended instead.
  * [Adafruit ESP32 Feather v2](https://www.adafruit.com/product/5400)

Feature set is intended to be 1:1 between CPython and CircuitPython. Documentation notes where this is not true due to
platform limitations.

## v0.7 Target Features - Target date: Someday!
- Load config from a remote site.
- Remote reload command to reset (and load new config!)
- Actual Sphinx documentation

## V0.6 Target Features
- ~~Option to load config from a remote site (ie: web directory)~~ - Nope, moving to v0.7
- Package for PyPi and Circup.
- Control options
  - ~~Multi-pin controls.~~ Done!
  - ~~Groups to wrap multiple controls together.~~ - Dropped. Probably better to group through Home Assistant.
  - ~~Flasher option.~~ Done!
  - ~~Multiple AW9523 expanders~~ Tested, works! Still can't mix pins across sources for a single control.




