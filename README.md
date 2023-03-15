####
#
# BRICKMASTER2
#
####

## Summary

A (Circuit)Python application for controlling relays and devices.

Project Goals
* Provide a common interface for a variety of devices
* Be able to do cool automations with connected devices (ie: Saturn 5 launch simulation)
* Teach myself some more python

## Platform Support

### Supported Platforms
This system is *intended* to support both CircuitPython boards and general-purpose Linux SBCs (ie: the Pi). Testing is
performed directly on a Raspberry Pi Zero W and Adafruit Metro M4 Airlift. Not all features are tested on both boards.

## Installation

### Linux

Assumes Raspberry Pi OS/Rasbian on a Pi.

_Probably works for other Linux versions, but not tested, adapt as appropriate._

1. Fetch the package to an appropriate directory. Assumed here you're using /home/pi/brickmaster2
2. Install all required python packages
   `pip3 install -r requirements.txt`
3. Copy the example systemd unit to ~/.config/systemd/user.
4. Edit the systemd unit if necessary, ie: if you're using an alternate path.
5. Ask systemd to reload user units - `systemctl --user daemon-reload`
6. Test the unit - `systemctl --user start brickmaster2.service`
7. If it starts cleanly, now enable the unit - `systemctl --user enable brickmaster2.service`
8. Make sure linger is enabled for the user - `sudo loginctl enable-linger pi`

### CircuitPython

<Instructions go here>

## Configuration file

The configuration file is a JSON text file, which unfortunately means it can't be commented.
Example configs are in the `examples` directory. 

### Main Options 
:white_check_mark: **means required**

| Name | Type | Default | Since | Description |
| ---- | :--: | :-----: | :---: | ----------- |
| :white_check_mark: `system` | dict | v0.1 | System settings |
| :white_check_mark: `controls` | dict | v0.1 | Devices to controls. Can be an empty dict if none present (but then what's the point!?) |
| :white_check_mark: `displays` | dict | v0.1 | 7-segment displays. Can be an empty dict if none present. |
| :white_check_mark: `scripts` | dict | v0.1 | Pre-defined scripts that can be run |


Good to go!

## Future development

A number of system level and general features I still want to build in here. 

* System
  * Support reload of config without restarting
  * Home Assistant discovery for entities
  * Allow query of complete system status. This allows an external system (ie: HA) to find out system state without 
  having to make all MQTT messages be preserved.
* Control
  * Lego Power Functions
  * Lego Powered Up
