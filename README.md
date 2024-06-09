####
#
# BRICKMASTER2
#
####

## Summary

A (Circuit)Python application for controlling relays and devices. The most important of which are, of course, Legos.

### Project Goals
* Provide a common interface for a variety of devices
* Be able to do cool automations with connected devices (ie: Saturn 5 launch simulation)
* Teach myself some more python (and hardware, and MQTT)

## Latest Updates - V0.5
Having struggled with CircuitPython/Adafruit-MiniMQTT stability issues, I have refactored the whole network module and
split based on platform.
Brickmaster2 will now use the very robust [PAHO MQTT](https://eclipse.dev/paho/index.php?page=clients/python/index.php),
which I also use in my other project, [CobraBay](https://github.com/chrisgilldc/cobrabay).
This leads to some code bloat. Notes on how to deploy based on platform are below.

## Supported Platforms

* Raspberry Pi OS - Specifically on the Pi Zero W. Other Pis should work just fine, just aren't tested.
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

1. Download the package and put the contents of the "brickmaster2" directory into the board root directory.
2. Download and install the required libraries.
3. Copy the "code.py" file to the board root directory.
4. Create a config.json and copy that to the board root directory.
5. Note that depending on the board, you may need to increase the stack size. You can do this by adding the below to 
'settings.toml'. This example increases it to 2 Mb. Raise as needed.
    ```
    CIRCUITPY_PYSTACK_SIZE=2048
    ```
## Configuration file

The configuration file is a JSON text file, which unfortunately means it can't be commented.
Example configs are in the `examples` directory. 

### Main Options 
:white_check_mark: **means required**

| Name | Type | Since | Description |
| --- | --- | --- | --- |
| :white_check_mark: `system` | dict | v0.1 | System settings |
| :white_check_mark: `controls` | list | v0.1 | Devices to controls. May be empty if none present (but then what's the point!?) |
| :white_check_mark: `displays` | list | v0.1 | 7-segment displays. May be empty if none present. |
| :white_check_mark: `scripts` | dict | v0.1 | Pre-defined scripts that can be run |

### System Options

:white_check_mark: **means required**

| Name                   | Type   | Default    | Since  | Description                                                                                                         |
|------------------------|--------|------------|--------|---------------------------------------------------------------------------------------------------------------------|
| :white_check_mark: `name` | string | 'hostname' | v0.1   | Name of the system to be used in MQTT topics and elsewhere.                                                         |
| `log_level`            | string | 'warning'  | v0.1   | How verbose to be.                                                                                                  |
| `wifihw`               | string | None | v0.4   | Type of WiFi hardware. May be 'esp32' or 'esp32spi'. If not specified, will try to auto-detect, but not guaranteed. | 
| `i2c`                  | dict   | None       | v0.1   | Defines I2C bus to use. Only required if using displays.                                                            |
| `indicators`           | dict | None | v0.3.1 | Defines GPIO pins for indicators lights.                                                                            |
| `ha`                    | dict | None | v0.3.1 | Options for Home Assistant discovery. If excluded, will disable HA discovery.                                       |
| `time_mqtt` | bool | False | v0.4.3 | Time MQTT polls. Used for development, you almost certainly don't need this. |

#### I2C
Currently the only option for I2C is 'bus_id', which must be an integer. Should probably always be '1'.

#### Indicators

System status indicators. These must be GPIO pins on the main board, as they are used before any extension boards
(ie: AW9523s) are loaded. If you don't have indicators, you can exclude this.

| Name        | Type   | Default | Since  | Description                                                                                 |
|-------------|--------|---------|--------|---------------------------------------------------------------------------------------------|
| `system`     | string | None    | v0.3.1 | GPIO pin to indicate system is running.                                                     |
| `net_on` | string | None    | v0.3.1 | Set active when both Wifi and MQTT are connected. If defined, net_off must also be defined. |
| `net_off` | string | None | v0.3.1 | Set active when either MQTT or Wifi are disconnected. If defined, net_on must also be defined. |

Note in my hardware configuration, the net_on and net_off pins run to different legs of a bi-color LED. Nothing in the code
mandates that.

#### Home Assistant (ha)

| Name        | Type   | Default   | Since  | Description                                                                                                                                                                                                                                                                                                                             |
|-------------|--------|-----------|--------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `area`      | string | None      | v0.3.1 | Area to suggest for the device when performing discovery.                                                                                                                                                                                                                                                                               |
| `meminfo`    | string | 'unified' | v0.3.1 | How to set up system memory information.<li>'unified' creates one entities, showing percent of memory free. <li>'unified-used' creates one entitiy, showing percent of memory used. <li>'split-pct' creates seperate used and free percent entities.<li>'split-all' creates entities for free and used in both percent and total bytes. |

### Controls

Controls attached to the system. Main controls list must be defined, but may be empty if none are present.
Each control is defined as a dict with the following settings.

Currently two types are supported, the GPIO type for GPIO pins directly on the main circuitpython board, and the
aw9523 type, for pins via the AW9523 I2C extension board.

#### GPIO
:white_check_mark: **means required**

| Name                    | Type   | Default | Since  | Description                                                                                                                                                      |
|-------------------------|--------|---------|--------|------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| :white_check_mark: `name` | string | None    | v0.1   | Name of the control. This will be part of the topic name.                                                                                                        |
| :white_check_mark: `type` | string | 'gpio'  | v0.1   | Defines the control type. This is GPIO.                                                                                                                          | 
| :white_check_mark: `pin` | string | None    | v0.1   | GPIO control to map too. Must be a valid name from the Adafruit board library. For example, Pi pin 25 is "D25"                                                   |
| `invert`                | boolean | False | v0.3.1 | Invert the control so 'off' holds the pin high and 'on' sets it low. This is required for some relay boards.                                                     |
| `disable`                | boolean | False | v0.3.1 | If defined and true, ignore this control. This allows currently unused controls to remain defined in the config file but not be exposed for use or pushed to HA. |

### Displays

Displays attached to the system. Main displays list must be defined, but may be empty if none are present. Each display
is defined as a dict with the following definition.

:white_check_mark: **means required**

| Name                         | Type   | Default | Since | Description                                                                                                       |
|------------------------------|--------|---------|-------|-------------------------------------------------------------------------------------------------------------------|
| :white_check_mark: `name`    | string |         | v0.1  | Name of the display. Will be referenced elsewhere.                                                                |
| :white_check_mark: `type`    | string |         | v0.1  | Type of display.<br/>Valid values are `bigseg7x4`, `seg7x4`                                                       |
| :white_check_mark: `address` | string |         | v0.1  | Address of the display. Must be a string in format `0xDD`, will be hex converted.                                 |
| :white_check_mark: `idle`    | dict   |         | v0.1  | What the display should show when not otherwise running. May be empty.                                            |
| `idle` -> `show`             | string | 'blank' | v0.1  | What to show when idle. May be `blank` (turn off display), `time` (time in local timezone), `date` (current date) |
| `idle` -> `brightness`       | float  | 1       | v0.1  | Brightness of the display when idle. Can be between 0.25 and 1.                                                   |

### Scripts

:white_check_mark: **means required**

| Name                     | Type   | Default                               | Since | Description                                                                                                           |
|--------------------------|--------|---------------------------------------|-------|-----------------------------------------------------------------------------------------------------------------------|
| :white_check_mark: `dir` | string | 'scripts'                             | v0.1  | Directory for scripts.                                                                                                |
| `scan_dir`               | string | `False` on Circuitpython, else `True` | v0.1  | Should the script directory be scanned for script files? If so, any json file (*.json) will be processed as a script. |
| `files`                  | list   | None                                  | v0.1  | **Required** for Circuitpython as it can't scan files. List of file names to include explicitly.                      |

## MQTT

**Need to document.**