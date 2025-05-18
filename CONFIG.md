# Brickmaster
## Configuration file

The configuration file is a JSON text file, which unfortunately means it can't be commented.

On non-Linux installs, the file must be "config.json" in the root of the board's filesystem.

### Main Options 
:white_check_mark: **means required**

| Name | Type | Description |
| --- | --- | --- |
| :white_check_mark: `system` | dict | System settings |
| :white_check_mark: `controls` | list | Devices to controls. May be empty if none present (but then what's the point!?) |
| :white_check_mark: `displays` | list | 7-segment displays. May be empty if none present. |
| :white_check_mark: `scripts` | dict | Pre-defined scripts that can be run |

### System Options

:white_check_mark: **means required**

| Name                  | Type   | Default   | Description                                                                                                                                                    |
|-----------------------|--------|-----------|----------------------------------------------------------------------------------------------------------------------------------------------------------------|
| :white_check_mark: `id` | string | None      | ID of the system, used for creating entity names. No spaces!                                                                                                   |
| `name` | string | id | Long name of the system for display purposes. If not specified, will default to the ID.                                                                        |
| `log_level`           | string | 'warning' | How verbose to be.                                                                                                                                             |
| `wifihw`              | string | None      | Type of WiFi hardware. Ignored on Linux. May be 'esp32' or 'esp32spi'. Will attempt autodetection if not specified, which usually works but is not guaranteed. | 
| `i2c`                 | bool   | None      | Defines I2C pins to use. Required if using I2C displays or external GPIO boards.                                                                               |
| `indicators`          | dict   | None      | Defines GPIO pins for indicators lights.                                                                                                                       |
| `mqtt` | dict | None | MQTT settings.                                                                                                                                                 |
| `ha`                  | dict   | None      | Options for Home Assistant discovery. If excluded, will disable HA discovery.                                                                                  |

#### I2C
I2C is required if using I2C displays (the only kind of supported displays) or Controls on an I2C board (AW9523).

#### Indicators

System status indicators. These must be GPIO pins on the main board, as they are used before any extension boards
(ie: AW9523s) are loaded. If you don't have indicators, you can exclude this.

| Name     | Type   | Default | Description                                                                                |
|----------|--------|---------|--------------------------------------------------------------------------------------------|
| `sysrun` | string | None    | GPIO pin to indicate system is running.                                                    |
| `neton` | string | None    | Set active when both Wifi and MQTT are connected. |
| `netoff` | string | None | Set active when either MQTT or Wifi are disconnected. If defined, neton must also be defined. |

Note in my hardware configuration, the neton and netoff pins run to different legs of a bi-color LED. Separate LEDs
could also be used.

#### MQTT

Settings for MQTT.

| Name     | Type   | Default | Description                                                                     |
|----------|--------|---------|---------------------------------------------------------------------------------|
| `broker` | string | None    | IP or Hostname of the broker to use.                                            |
| `port`   | int    | 1883    | Port to connect to. Defaults to the MQTT default.                               |
| `user`   | string | None    | Username to authenticate to the broker.                                         | 
| `key`    | string | None    | Key to authenticate to the broker.                                              |
| `log`    | bool   | False   | Enable MQTT client debugging. Probably don't need this!                         |

#### Home Assistant (ha)

| Name        | Type   | Default   | Description                                                                                                                                                                                                                                                                                                                          |
|-------------|--------|-----------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `area`      | string | None      | Area to suggest for the device when performing discovery.                                                                                                                                                                                                                                                                            |
| `base` | string | 'homeassistant' | Base for homeassistant discovery. Default is the same as HA's default, don't change unless you know you changed it in HA.                                                                                                                                                                                                            |
| `meminfo`    | string | 'unified' | How to set up system memory information.<li>'unified' creates one entity, showing percent of memory free. <li>'unified-used' creates one entity, showing percent of memory used. <li>'split-pct' creates seperate used and free percent entities.<li>'split-all' creates entities for free and used in both percent and total bytes. |

### Controls

Controls attached to the system. Main controls list must be defined, but may be empty if none are present.

Four types of control are supported:
* **Single** - A simple on-off. This is the default.
* Flasher - Flashes across a sequence of pins.

If a type is not specified for a control, it defaults to *Single*.

#### Defining Pins

A pin definition can come in one of three forms.

1. A single GPIO pin.

`"pins": "D1"`

This pin is raised high when the control is turned on, and low when turned off.

2. An on-off pair of pins.

  `"pins": { "on": "D2", "off": "D3" }`

When this control is off pin D3 is set high and D2 is set low. When the control is set on, D2 is set high and D3 low. 
This configuration is useful for controlling latching relays.    

3. A list of pins.

`"pins": ["D1", { "on": "D2", "off": "D3" }, "D4"`

This list has three sub-elements, D1, D3/D4 and D4. This syntax is used to specify the list for a Flasher control.

#### I2C Context

All pins are evaluated in one of two contexts.

If no 'extio' is specified, pins are assumed to be directly on the board. (Pi, Feather, what have you).

If an 'extio' is assigned, all pins must be valid on the external io board.

Mixing onboard and IO expander pins in a single control is not supported.

#### Pin IDs

Pin IDs should always be quoted to ensure they're interpreted as strings. Since boards present pins differently, it's 
simpler to always treat them as strings in the config file. For reference, common pins observed are listed below. The
system will also publish a dump of its properties to topic ```<base>/<board>/system/pins```


ESP32 Feather v2: A0, A1, A2, A3, A4, A5, A6, A7, A8, A9, A10, A11, A12, D4, D5, D7, D8, D12, D13, D14, D15, D19, D20, D21, D22, D24, D26, D27, D32, D33, D34, D35, D36, D37, D39
AW9523 GPIO Expander: 0-15

#### Single Control
:white_check_mark: **means required**

| Name                      | Type   | Default  | Description                                                                                                                                                      |
|---------------------------|--------|----------|------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| :white_check_mark: `name` | string | None     | Name of the control. This will be part of the topic name.                                                                                                        |
| :white_check_mark: `type` | string | 'single' | Type of the control. May be 'single' or 'flasher'.                                                                                                               | 
| :white_check_mark: `pins` | string | None     | GPIO control to map too. Must be a valid name from the Adafruit board library. For example, Pi pin 25 is "D25"                                                   |
| `invert`                  | boolean | False    | Invert the control so 'off' holds the pin high and 'on' sets it low. This is required for some relay boards.                                                     |
| `disable`                 | boolean | False    | If defined and true, ignore this control. This allows currently unused controls to remain defined in the config file but not be exposed for use or pushed to HA. |

#### Flashing Control

A flashing control has many of the same options as a Single Control. The control will be pulsed automatically.
A flasher's base pins get defined as a list of pins. The control will turn on each pin or set of pins for ```loiter_time```
seconds, with ```switch_time``` seconds in between. To have a single control that flashes, put only one item in the pins
list.

Note that Flashers cannot be inverted!

:white_check_mark: **means required**

| Name                      | Type   | Default | Description                                                                                                                                                      |
|---------------------------|--------|---------|------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| :white_check_mark: `name` | string | None    | Name of the control. This will be part of the topic name.                                                                                                        |
| :white_check_mark: `type` | string | 'gpio'  | Defines the control type. This is GPIO.                                                                                                                          | 
| :white_check_mark: `pins` | string | None    | GPIO control to map too. Must be a valid name from the Adafruit board library. For example, Pi pin 25 is "D25"                                                   |
| `loiter_time`             |int | 1 | Time an individual element should remain on, in seconds. |
| `switch_time`             | int | 0 | Time to wait between setting on element off and the next on, in seconds. |
| `disable`                 | boolean | False | If defined and true, ignore this control. This allows currently unused controls to remain defined in the config file but not be exposed for use or pushed to HA. |


### Displays

Displays attached to the system. Main displays list must be defined, but may be empty if none are present. Each display
is defined as a dict with the following definition.

:white_check_mark: **means required**

| Name                         | Type   | Default | Description                                                                                                       |
|------------------------------|--------|---------|-------------------------------------------------------------------------------------------------------------------|
| :white_check_mark: `name`    | string |         | Name of the display. Will be referenced elsewhere.                                                                |
| :white_check_mark: `type`    | string |         | Type of display.<br/>Valid values are `bigseg7x4`, `seg7x4`                                                       |
| :white_check_mark: `address` | string |         | Address of the display. Must be a string in format `0xDD`, will be hex converted.                                 |
| :white_check_mark: `idle`    | dict   |         | What the display should show when not otherwise running. May be empty.                                            |
| `idle` -> `show`             | string | 'blank' | What to show when idle. May be `blank` (turn off display), `time` (time in local timezone), `date` (current date) |
| `idle` -> `brightness`       | float  | 1       | Brightness of the display when idle. Can be between 0.25 and 1.                                                   |

### Scripts

:white_check_mark: **means required**

| Name                     | Type   | Default                               | Description                                                                                                           |
|--------------------------|--------|---------------------------------------|-----------------------------------------------------------------------------------------------------------------------|
| :white_check_mark: `dir` | string | 'scripts'                             | Directory for scripts.                                                                                                |
| `scan_dir`               | string | `False` on Circuitpython, else `True` | Should the script directory be scanned for script files? If so, any json file (*.json) will be processed as a script. |
| `files`                  | list   | None                                  | **Required** for Circuitpython as it can't scan files. List of file names to include explicitly.                      |
