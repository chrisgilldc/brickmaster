####
#
# BRICKMASTER
#
####

## Summary

A (Circuit)Python application for controlling relays and devices. The most important of which are, of course, Legos.

### Project Goals
* Provide a common interface for a variety of devices
* Be able to do cool automations with connected devices (ie: Saturn 5 launch simulation)
* Teach myself some more python (and hardware, and MQTT)

## V0.6 Target Features
- Option to load config from a remote site (ie: web directory)
- Control options
  - ~~Multi-pin controls.~~ Done!
  - Groups to wrap multiple controls together.
  - ~~Flasher option.~~ Done!
  - Multiple AW9523 expanders

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

## Supported Platforms

* Raspberry Pi OS (Bookworm) - Specifically on the Pi Zero W. Other Pis should work just fine, just aren't tested.
* CircuitPython 9 - CircuitPython 8 is no longer being tested.
  * [Adafruit Metro M4 Airlift](https://www.adafruit.com/product/4000) - Default pystack size on this board is 1536, which should be raised to at least 
  * 4096. Given notable memory limitations of this board I may stop testing in the near 
  future. Requires a pystack value of at least 4096, possibly more depending on your control configuration. The ESP32 line or possibly the Metro M7 Airlift would be recommended instead.
  * [Adafruit ESP32 Feather v2](https://www.adafruit.com/product/5400)

Feature set is intended to be 1:1 between CPython and CircuitPython. Documentation notes where this is not true due to
platform limitations.

## Installation

### Linux

Assumes Raspberry Pi OS/Rasbian on a Pi.

_Probably works for other Linux versions, but not tested, adapt as appropriate._

1. Download the code from github: 


     `wget https://github.com/chrisgilldc/brickmaster/archive/refs/heads/main.zip`
2. Extract the file. This will put code into `~/brickmaster-main`:


     `unzip main.zip`
3. Create a venv for brickmaster.


     `python3 -m venv ~/.env_bm2`
4. Enter the python venv.


     `source ~/.env_bm2/bin/activate`
5. Install all the python requirements.


     `pip3 install -r ~/brickmaster-main/requirements.txt`
6. Create a config file. You can do this from scratch or copy a file from `~/brickmaster-main/hwconfigs/`, which has 
starting configs for [Brickmaster Hardware](hardware.md). By default, the systemd unit will try to load `~/config.json`.
6. Create a scripts directory separate from the distribution. This will make sure any custom scripts don't get 
overwritten in future updates.


     `mkdir ~/scripts`

     `cp -R ~/brickmaster-main/scripts/* ~/scripts`
7. Make a user systemd directory. This isn't created by default on a freshly installed system.


     `mkdir -p ~/.config/systemd/user`
8. Copy the example systemd unit to ~/.config/systemd/user.


     `cp ~/brickmaster-main/examples/brickmaster.service ~/.config/systemd/user`
9. If your config file is somewhere other than `~/config.json`, update the unit file to point to that file. Edit the 
`ExecStart` line with the full path of the config file.
10. Have systemd reload the user units so brickmaster is available.


     `systemctl --user daemon-reload`
11. Start brickmaster.


     `systemctl --user start brickmaster.service`
12. Check the status of the unit. Be sure the active line says `active (running)`.


     `systemctl --user status brickmaster.service`

13. If it started successfully, enable the unit.


     `systemctl --user enable brickmaster.service`
14. Enable linger for the user. This will start the user's systemd instance on system boot and in turn start
brickmaster.

    
     `sudo loginctl enable-linger pi`

### CircuitPython

#### Requirements
* CircuitPython 9. Tested on 9.2.0. Later versions should work fine.
  * If your board is not on CP9, update it. Updates can be found [here](https://circuitpython.org/downloads).
* The current [CircuitPython 9 Library Bundle](https://github.com/adafruit/Adafruit_CircuitPython_Bundle/releases/download/20240625/adafruit-circuitpython-bundle-9.x-mpy-20240625.zip). Use libraries from here unless otherwise specified.
* Adafruit MiniMQTT at least [7.9.0](https://github.com/adafruit/Adafruit_CircuitPython_MiniMQTT/releases/tag/7.9.0).
* If you're using an ESP32 SPI board (ie: Metro M4/M7), use at least Adafruit ESP32SPI at least [8.4.0](https://github.com/adafruit/Adafruit_CircuitPython_ESP32SPI/releases/tag/8.4.0).
* Set up the Web Workflow, instructions [here](https://learn.adafruit.com/circuitpython-with-esp32-quick-start/setting-up-web-workflow).

#### Install Process
1. Download the package from github.


     `wget https://github.com/chrisgilldc/brickmaster/archive/refs/heads/main.zip`
2. Extract the package. The package location will be referred to here as "brickmaster-main" (wherever you have it).
3. Copy "brickmaster-main/src/brickmaster" to your circuitpython board's `lib` directory.
4. Copy the following libraries from the bundle into the board's `lib` directory. If using the web workflow, the bolded 
libraries are directories and need to use the directory upload option. 
   * adafruit_aw9523.mpy
   * adafruit_connection_manager.mpy
   * **adafruit_esp32spi** - Only for ESP32SPI boards like the Metro M4/M7
   * **adafruit_ht16k33**
   * adafruit_logging.mpy
   * **adafruit_minimqtt**
   * **adafruit_register**
   * adafruit_ticks.mpy
5. Create a config file. You can do this from scratch or copy a file from `brickmaster-main/hwconfigs/`, which has 
starting configs for [Brickmaster Hardware](hardware.md). Place the config file in the board's root directory.
6. Create a `settings.toml` file. You can start with `brickmaster-main/examples/settings.toml`.
   * Fill in all the required parameters with your SSID and Password.
   * An increased, 4Mb PYSTACK size is set by default in the example. This is tested as good on the Metro M4 Airlift.
7. Copy "brickmaster-main/circuitpy-code.py" to your circuitpython board's root directory as `code.py`.
8. Connect to the serial console (via USB or Web Workflow, depending) and monitor startup.

