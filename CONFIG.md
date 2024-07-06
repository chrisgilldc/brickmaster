# BrickMaster2
## Configuration file

The configuration file is a JSON text file, which unfortunately means it can't be commented.


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

| Name                  | Type   | Default    | Since  | Description                                                                                                         |
|-----------------------|--------|------------|--------|---------------------------------------------------------------------------------------------------------------------|
| :white_check_mark: `name` | string | 'hostname' | v0.1   | Name of the system to be used in MQTT topics and elsewhere.                                                         |
| `log_level`           | string | 'warning'  | v0.1   | How verbose to be.                                                                                                  |
| `wifihw`              | string | None | v0.4   | Type of WiFi hardware. May be 'esp32' or 'esp32spi'. If not specified, will try to auto-detect, but not guaranteed. | 
| `i2c`                 | dict   | None       | v0.1   | Defines I2C pins to use. Required if using I2C displays.                                                            |
| `indicators`          | dict | None | v0.3.1 | Defines GPIO pins for indicators lights.                                                                            |
| `ha`                  | dict | None | v0.3.1 | Options for Home Assistant discovery. If excluded, will disable HA discovery.                                       |

#### I2C
I2C is required if using I2C displays (the only kind of supported displays) because obviously.


#### Indicators

System status indicators. These must be GPIO pins on the main board, as they are used before any extension boards
(ie: AW9523s) are loaded. If you don't have indicators, you can exclude this.

| Name     | Type   | Default | Since  | Description                                                                                |
|----------|--------|---------|--------|--------------------------------------------------------------------------------------------|
| `sysrun` | string | None    | v0.3.1 | GPIO pin to indicate system is running.                                                    |
| `neton` | string | None    | v0.3.1 | Set active when both Wifi and MQTT are connected. If defined, netoff must also be defined. |
| `netoff` | string | None | v0.3.1 | Set active when either MQTT or Wifi are disconnected. If defined, neton must also be defined. |

Note in my hardware configuration, the neton and netoff pins run to different legs of a bi-color LED. Separate LEDs
could also be used.

#### Home Assistant (ha)

| Name        | Type   | Default   | Since  | Description                                                                                                                                                                                                                                                                                                                           |
|-------------|--------|-----------|--------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `area`      | string | None      | v0.3.1 | Area to suggest for the device when performing discovery.                                                                                                                                                                                                                                                                             |
| `meminfo`    | string | 'unified' | v0.3.1 | How to set up system memory information.<li>'unified' creates one entity, showing percent of memory free. <li>'unified-used' creates one entitiy, showing percent of memory used. <li>'split-pct' creates seperate used and free percent entities.<li>'split-all' creates entities for free and used in both percent and total bytes. |

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