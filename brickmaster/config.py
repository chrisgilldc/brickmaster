"""
Brickmaster2 Configuration Processing
"""

import adafruit_logging as logging
import sys
import json
# import os
import gc


class BM2Config:
    """
    Brickmaster2 Configuration Class
    """
    def __init__(self, config_json):
        self._config = config_json
        self._logger = logging.getLogger("Brickmaster")
        self._logger.setLevel(logging.INFO)

        if not self._validate():
            raise ValueError("File is not a valid Brickmaster configuration.")

        self._logger.info("Config: Setting log level to: {}".format(self._config['system']['log_level_name']))
        self._logger.setLevel(self._config['system']['log_level'])

    def config_json(self):
        """
        Return the validated, active config as JSON.
        """
        return json.dumps(self._config)

    # Validation methods.

    # Master validator
    def _validate(self):
        # Check for the required config sections.
        required_keys = ['system', 'controls']
        optional_keys = ['displays','scripts','sensors']
        optional_defaults = {
            'displays': [],
            'scripts': {},
            'sensors': []
        }
        print(self._config)
        for key in required_keys:
            self._logger.debug("Checking for section '{}'".format(key))
            if key not in self._config:
                self._logger.critical("Required configuration section '{}' not present. Cannot continue!".format(key))
                sys.exit(1)
        for key in optional_keys:
            self._logger.debug("Checking for section '{}'".format(key))
            if key not in self._config:
                self._logger.info("Optional configuration section '{}' not present.".format(key))
                self._config[key] = optional_defaults[key]

        # Change the logging level.
        self._validate_logging()
        self._logger.info("Config: Adjusting log level to '{}'".format(self._config['system']['log_level_name']))
        self._logger.setLevel(self._config['system']['log_level'])
        # Make sure the right sections exist.
        self._validate_system()
        # Validate the controls.
        self._validate_controls()
        # Validate the displays.
        self._validate_displays()
        # Validate the scripts.
        self._validate_scripts()
        if 'sensors' in self._config:
            self._logger.info("Sensors section defined. Checking...")
            self._validate_sensors()
        return True

    def _validate_sensors(self):
        """
        Validate sensor configuration if present.
        """
        if not isinstance(self._config['sensors'], list):
            self._logger.critical('Config: Sensors not correctly defined. Must be a list of dictionaries.')

        i = 0
        to_delete = []
        while i < len(self._config['sensors']):
            self._logger.debug("Config: Validating sensor definition '{}'".format(self._config['sensors'][i]))
            required_params = ['id','type','name','address']
            for param in required_params:
                if param not in self._config['sensors'][i]:
                    self._logger.critical("Config: Required sensor config option '{}' missing in control definition {}. "
                                          "Cannot configure!".format(param, i+1))
                    to_delete.append(i)
                    i += 1
                    continue
            # Sensor is validated. Convert the address to hex integer.
            self._config['sensors'][i]['address'] = int(self._config['sensors'][i]['address'], 16)
            i += 1

        # Make the to_delete list unique.
        to_delete = list(set(to_delete))
        self._logger.debug("Sensors to remove: {}".format(to_delete))
        # Delete any sensors that have been invalidated
        for d in sorted(to_delete, reverse=True):
            del self._config['sensors'][d]

    def _validate_system(self):
        """
        Validate system settings.
        """
        self._logger.debug("Config: Validating system section")
        required_params = ['id', 'mqtt']
        optional_params = ['name', 'i2c', 'interface', 'log_level', 'wifihw']
        optional_defaults = {
            'i2c': None,
            'interface': 'wlan0',
            'log_level': 'info',
            'wifihw': None
        }
        # Check for presence of required options.
        for param in required_params:
            self._logger.debug("Config: Checking for required key '{}'".format(param))
            if param not in self._config['system']:
                self._logger.critical("Config: Required config option '{}' missing. Cannot continue!".format(param))
                sys.exit(1)

        # Check for optional settings, assign the defaults if need be.
        for param in optional_params:
            self._logger.debug("Config: Checking for optional parameter '{}'".format(param))
            if param not in self._config['system']:
                self._logger.info("Option '{}' not found, using default '{}'".
                                     format(param, optional_defaults[param]))
                self._config['system'][param] = optional_defaults[param]
        if 'name' not in self._config['system']:
            self._logger.info("Config: Name not set, defaulting to ID.")
            self._config['system']['name'] = self._config['system']['id']

        # Confirm all MQTT sub-keys are defined.
        mqtt_keys = {'broker','user','key'}
        if not mqtt_keys <= set(self._config['system']['mqtt'].keys()):
            self._logger.error("Config: All MQTT keys not defined. Cannot continue!")
            sys.exit(1)
        # Optional MQTT parameters
        if 'log' not in self._config['system']['mqtt']:
            self._config['system']['mqtt']['log'] = False
        if 'port' not in self._config['system']['mqtt']:
            self._config['system']['mqtt']['port'] = 1883

        # Check for network indicator definition.
        if 'indicators' in self._config['system']:
            # Make sure each item is defined, even if not present.
            #
            for indicator in ('sysrun','neton','netoff'):
                if indicator not in self._config['system']['indicators']:
                    self._config['system']['indicators'][indicator] = None

            # Netoff requires neton.
            if 'netoff' in self._config['system']['indicators'] and not 'neton' in self._config['system']['indicators']:
                self._logger.warning("Config: May not define a network off indicator without a network on indicator.")
                self._config['system']['indicators']['neton'] = None
                self._config['system']['indicators']['netoff'] = None

        else:
            self._config['system']['indicators'] = { 'sysrun': None, 'neton': None, 'netoff': None }

        # Check for a modified publish time.
        try:
            if isinstance(self._config['system']['publish_time'], int):
                self._logger.info("Config: Using Publish Time {}s".format(self._config['system']['publish_time']))
            else:
                self._logger.warning("Config: Provided Publish Time is not an integer, defaulting to 15s.")
                self._config['system']['publish_time'] = 15
        except KeyError:
            self._logger.info("Config: Using default Publish Time of 15s")
            self._config['system']['publish_time'] = 15

        # Check for Home Assistant configuration
        if 'ha' in self._config['system']:
            # If 'ha' is defined, turn home assistant discovery on.
            self._config['system']['ha_discover'] = True
            # Check for a default area.
            try:
                if isinstance(self._config['system']['ha']['area'], str):
                    self._logger.info("Config: Using HA Area '{}'".format(self._config['system']['ha']['area']))
                    self._config['system']['ha_area'] = self._config['system']['ha']['area']
                    del self._config['system']['ha']['area']
            except KeyError:
                pass
            # Check for a base discovery prefix.
            try:
                if isinstance(self._config['system']['ha']['base'], str):
                    self._logger.info("Config: Using HA Base '{}'".format(self._config['system']['ha']['base']))
                    self._config['system']['ha_base'] = self._config['system']['ha']['base']
                    del self._config['system']['ha']['base']
            except KeyError:
                pass

            # Check for how to set up Meminfo.
            try:
                if isinstance(self._config['system']['ha']['meminfo'], str):
                    if self._config['system']['ha']['meminfo'] in ('unified', 'unified-used', 'split-pct', 'split-all'):
                        self._logger.debug("Config: Memory info topics will be discovered as '{}'".
                                           format(self._config['system']['ha']['meminfo']))
                        self._config['system']['ha_meminfo'] = self._config['system']['ha']['meminfo']
                        del self._config['system']['ha']['meminfo']
                    else:
                        self._logger.warning("Config: Memory info option '{}' not valid. Defaulting to 'unified'".
                                             format(self._config['system']['ha']['meminfo']))
                        self._config['system']['ha_meminfo'] = 'unified'
                        del self._config['system']['ha']['meminfo']
            except KeyError:
                self._config['system']['ha_meminfo'] = 'unified'

            # Remove the base HA item.
            del self._config['system']['ha']
        else:
            self._config['system']['ha_discover'] = False

    def _validate_logging(self):
        try:
            # Map the log level to an actual Logging entity.
            if self._config['system']['log_level'].lower() == 'debug':
                self._config['system']['log_level_name'] = 'debug'
                self._config['system']['log_level'] = logging.DEBUG
            elif self._config['system']['log_level'].lower() == 'info':
                self._config['system']['log_level_name'] = 'info'
                self._config['system']['log_level'] = logging.INFO
            elif self._config['system']['log_level'].lower() == 'warning':
                self._config['system']['log_level_name'] = 'warning'
                self._config['system']['log_level'] = logging.WARNING
            elif self._config['system']['log_level'].lower() == 'error':
                self._config['system']['log_level_name'] = 'error'
                self._config['system']['log_level'] = logging.ERROR
            elif self._config['system']['log_level'].lower() == 'critical':
                self._config['system']['log_level_name'] = 'critical'
                self._config['system']['log_level'] = logging.CRITICAL
            else:
                self._config['system']['log_level_name'] = 'warning'
                self._config['system']['log_level'] = logging.WARNING
        except KeyError:
            self._config['system']['log_level_name'] = 'warning'
            self._config['system']['log_level'] = logging.WARNING

    def _validate_controls(self):
        """
        Validate the defined controls
        @return: None
        """
        # Is the control definition a list?
        if not isinstance(self._config['controls'], list):
            self._logger.critical('Config: Controls not correctly defined. Must be a list of dictionaries.')
            return

        # Prepare to iterate, set up variables.
        i = 0
        to_delete = []
        while i < len(self._config['controls']):
            self._logger.debug("Config: Validating control definition '{}'".format(self._config['controls'][i]))
            # Control must have an ID.
            if 'id' not in self._config['controls'][i]:
                self._logger.critical("Config: Required control config option 'id' missing in control definition {}. "
                                      "Cannot configure!".format(i+1))
                to_delete.append(i)
                i += 1
                continue

            if 'pins' not in self._config['controls'][i]:
                self._logger.critical("Config: Control {} does not have pins defined! Cannot configure!".
                                      format(self._config['controls'][i]['id']))
                to_delete.append(i)
                i += 1
                continue
            # Control must have a type, if it doesn't, default it to 'single'.
            if 'type' not in self._config['controls'][i]:
                self._logger.info(f"Config: No type defined for control '{self._config['controls'][i]['id']}'. Defaulting to single.")
                self._config['controls'][i]['type'] = 'single'

            # Check to see if name is defined.
            if 'name' not in self._config['controls'][i]:
                self._logger.info(f"Config: No name defined for control '{self._config['controls']['id']}'. Defaulting to ID.")
                self._config['controls'][i]['name'] = self._config['controls'][i]['id']

            # Check to see if the control is disabled. This allows items to be left in the config file but skipped
            try:
                if self._config['controls'][i]['disable']:
                    self._logger.warning("Config: Control {} marked as disabled. Skipping.".
                                      format(self._config['controls'][i]['name']))
                    to_delete.append(i)
                    i += 1
                    continue
                else:
                    # If the 'disable' setting for the control is anything other than true,
                    # enable and ignore the setting.
                    del self._config['controls'][i]['disable']
            except KeyError:
                pass

            optional_params = ['icon', 'active_low', 'extio', 'loiter_time', 'switch_time']
            optional_defaults = {
                'icon': 'mdi:toy-brick',
                'active_low': False,
                'extio': None,
                'loiter_time': 1000,
                'switch_time': 0
            }
            for param in optional_params:
                self._logger.debug("Config: Checking for optional parameter '{}'".format(param))
                if param not in self._config['controls'][i]:
                    self._logger.info("Config: Option '{}' not found, using default '{}'".
                                         format(param, optional_defaults[param]))
                    self._config['controls'][i][param] = optional_defaults[param]
                else:
                    self._logger.info("Config: Optional parameter '{}' set to '{}'".format(
                        param, self._config['controls'][i][param]
                    ))

            # Validate EXTIO, if used.
            if isinstance(self._config['controls'][i]['extio'],str):
                try:
                    self._config['controls'][i]['extio'] = int(self._config['controls'][i]['extio'], 16)
                except ValueError:
                    self._logger.error("Config: Provided extio setting '{}' cannot convert to an integer. Should be in the format '0x##'.".format(self._config['controls'][i]['extio']))
                    to_delete.append(i)
                    i += 1
                    continue

            # Validate the pin definition
            if (isinstance(self._config['controls'][i]['pins'], str) or
                    isinstance(self._config['controls'][i]['pins'], int)):
                # A string should be a reference to a pin on the appropriate board, that's fine.
                pass
            elif isinstance(self._config['controls'][i]['pins'], dict):
                if 'on' not in self._config['controls'][i]['pins']:
                    self._logger.error("Config: Control '{}' does not have 'on' pin defined.".
                                       format(self._config['controls'][i]['name']))
                    to_delete.append(i)
                    i += 1
                    continue
                if 'off' not in self._config['controls'][i]['pins']:
                    self._logger.error("Config: Control '{}' does not have 'on' pin defined.".
                                       format(self._config['controls'][i]['name']))
                    to_delete.append(i)
                    i += 1
                    continue
            elif isinstance(self._config['controls'][i]['pins'], list):
                if self._config['controls'][i]['type'] != 'flasher':
                    self._logger.error("Config: Control '{}' has a pin list defined, but is not set as a flasher.")
                    to_delete.append(i)
                    i += 1
                    continue
            else:
                self._logger.error("Config: Control '{}' has unsupported data for pin definition.".
                                format(self._config['controls'][i]['name']))
                to_delete.append(i)
                i += 1
                continue
            i += 1

        # Make the to_delete list unique.
        to_delete = list(set(to_delete))
        self._logger.debug("Controls to remove: {}".format(to_delete))
        # Delete any controls that have been invalidated
        for d in sorted(to_delete, reverse=True):
            del self._config['controls'][d]
        self._logger.debug("Config proceeding with successful controls: {}".format(self._config['controls']))

    def _make_pindef(self, input_pindef):
        """
        Iteratively process pin definitions.

        @param input_pindef: Pin definition. Can be a string to indicate a single pin (ex: D25), a dict specifying
        on and off, (ex: {"on": "D26", "off": "D27"}) or a list of dicts or strings (ex: ["D25", {"on": "D26", "off": "D27"}])
        :type input_pindef: str, list or dict

        """
        if isinstance(input_pindef, str) or isinstance(input_pindef, int):
            # If it's just a str/int, then it's a single pin, and expand it to an on/off in the list.
            return { 'on': input_pindef, 'off': input_pindef }
        elif isinstance(input_pindef, dict):
            # A dictionary should be 'on','off'. If it is, we can just wrap it in list to return the correct type.
            for key in ('on', 'off'):
                if key not in input_pindef:
                    raise ValueError
            return input_pindef
        elif isinstance(input_pindef, list):
            output_pindef = []
            # A list should have sets of 'on','off' dicts.
            for pdef in input_pindef:
                try:
                    output_pindef.append(self._make_pindef(pdef))
                except ValueError:
                    raise
            return output_pindef
        return None

    # def _validate_controls_old(self):
    #     if not isinstance(self._config['controls'], list):
    #         self._logger.critical('Config: Controls not correctly defined. Must be a list of dictionaries.')
    #         return
    #     i = 0
    #     to_delete = []
    #     while i < len(self._config['controls']):
    #         self._logger.debug("Config: Validating control definition '{}'".format(self._config['controls'][i]))
    #         # Check to see if required items are defined.
    #         required_keys = ['id', 'type']
    #         for key in required_keys:
    #             if key not in self._config['controls'][i]:
    #                 self._logger.critical("Config: Required control config option '{}' missing in control {}. Cannot configure!".
    #                                       format(key, i+1))
    #                 to_delete.append(i)
    #
    #         # Check to see if name is defined.
    #         if 'name' not in self._config['controls'][i]:
    #             self._config['controls'][i]['name'] = self._config['controls'][i]['id']
    #
    #         # Check to see if the control is disabled. This allows items to be left in the config file but skipped
    #         try:
    #             if self._config['controls'][i]['disable']:
    #                 self._logger.info("Config: Control {} marked as disabled. Skipping.".
    #                                   format(self._config['controls'][i]['name']))
    #                 to_delete.append(i)
    #                 i += 1
    #                 continue
    #             else:
    #                 # If the 'disable' setting for the control is anything other than true,
    #                 # enable and ignore the setting.
    #                 del self._config['controls'][i]['disable']
    #         except KeyError:
    #             pass
    #
    #         # Pull out control type, this just make it easier.
    #         ctrltype = self._config['controls'][i]['type']
    #         if ctrltype == 'gpio':
    #             required_parameters = ['pin']
    #         elif ctrltype == 'aw9523':
    #             required_parameters = ['addr', 'pin']
    #         else:
    #             self._logger.error("Config: Cannot set up control '{}', type '{}' is not supported.".format(i, ctrltype))
    #             to_delete.append(i)
    #             i += 1
    #             continue
    #
    #         for req_param in required_parameters:
    #             if req_param not in self._config['controls'][i]:
    #                 self._logger.error("Config: Cannot set up control '{}', no '{}' directive.".format(
    #                     self._config['controls'][i]['name'], req_param))
    #                 to_delete.append(i)
    #                 i += 1
    #                 continue
    #
    #         optional_params = ['icon']
    #         optional_defaults = {
    #             'icon': 'mdi:toy-brick'
    #         }
    #         for param in optional_params:
    #             self._logger.debug("Config: Checking for optional parameter '{}'".format(param))
    #             if param not in self._config['controls'][i]:
    #                 self._logger.warning("Config: Option '{}' not found, using default '{}'".
    #                                      format(param, optional_defaults[param]))
    #                 self._config['controls'][i][param] = optional_defaults[param]
    #             else:
    #                 self._logger.debug("Config: Optional parameter '{}' set to '{}'".format(
    #                     param, self._config['controls'][i][param]
    #                 ))
    #
    #         i += 1
    #     # Make the to_delete list unique.
    #     to_delete = list(set(to_delete))
    #     self._logger.debug("Controls to remove: {}".format(to_delete))
    #     # Delete any controls that have been invalidated
    #     for d in sorted(to_delete, reverse=True):
    #         del self._config['controls'][d]
    #     self._logger.debug("Config proceeding with successful controls: {}".format(self._config['controls']))

    # Validate the displays on loading.
    def _validate_displays(self):
        if not isinstance(self._config['displays'], list):
            self._logger.critical('Displays not correctly defined. Must be a list of dictionaries.')
            return
        i = 0
        to_delete = []
        while i < len(self._config['displays']):
            self._logger.debug("Checking display {}. Has raw config {}".format(i, self._config['displays'][i]))
            required_keys = ['id', 'type', 'address']
            for key in required_keys:
                self._logger.debug("Checking for required display key '{}'".format(key))
                if key not in self._config['displays'][i]:
                    self._logger.critical("Required control display option '{}' missing in display {}. "
                                          "Discarding display.".format(key, i))
                    to_delete.append(i)
                    # i += 1
                    continue
            # Make sure type is legitimate.
            if self._config['displays'][i]['type'].lower() not in ('seg7x4', 'bigseg7x4'):
                self._logger.critical("Display type '{}' not known in display {}. Discarding display.".
                                      format(self._config['displays'][i]['type'], i))
                to_delete.append(i)
                # i += 1
                continue
            # If name isn't defined, convert ID to name.
            if 'name' not in self._config['displays'][i]:
                self._config['displays'][i]['name'] = self._config['displays'][i]['id']

            # Convert the address to a hex value.
            try:
                self._config['displays'][i]['address'] = int(self._config['displays'][i]['address'], 16)
            except TypeError:
                self._logger.critical("Address not a string for display {}. Should be in \"0xXX\" format. "
                                      "Discarding display.".format(i))
                # i += 1
                to_delete.append(i)
                continue
            # Default when_idle to blank, if not otherwise specified.
            if 'idle' not in self._config['displays'][i]:
                self._config['displays'][i]['idle'] = {'show': 'blank'}
            else:
                # If the idle was put in as a string, convert it into a dict and default to full brightness.
                if isinstance(self._config['displays'][i]['idle'], str):
                    self._config['displays'][i]['idle'] = {
                        'show': self._config['displays'][i]['idle'],
                        'brightness': 1
                         }
                else:
                    # Check the show option.
                    if self._config['displays'][i]['idle']['show'] not in ('time', 'date', 'blank'):
                        self._logger.warning("Specified idle value for display {} ('{}') not valid. Defaulting to "
                                             "blank.".format(i, self._config['displays'][i]['idle']['show']))
                        self._config['displays'][i]['idle']['show'] = 'blank'
                        self._config['displays'][i]['idle']['brightness'] = 1

                    # Convert the brightness setting to a float.
                    try:
                        self._config['displays'][i]['idle']['brightness'] = (
                            float(self._config['displays'][i]['idle']['brightness']))
                    except KeyError:
                        self._config['displays'][i]['idle']['brightness'] = 1
                    except ValueError:
                        self._config['displays'][i]['idle']['brightness'] = 1
            i += 1

        # Delete any invalidated displays
        self._logger.debug("Displays to delete: {}".format(to_delete))
        for d in sorted(to_delete, reverse=True):
            self._logger.debug("Deleting display '{}'".format(d))
            del self._config['displays'][d]

    # Validate the scripts.
    def _validate_scripts(self):
        if not isinstance(self._config['scripts'], dict):
            self._logger.critical('Scripts not correctly defined. Must be a dictionary.')
            return
        # Can we scan the scripts directory?
        # If we're not on linux, absolutely not! CircuitPython doesn't support Pathlib and scanning.

        if sys.implementation.name != 'cpython':
            self._logger.warning("Cannot scan scripts directory. Scripts must be individually enumerated.")
            self._config['scripts']['scan_dir'] = False
        else:
            try:
                # Scan_dir setting, use that, convert it to a proper bool.
                if self._config['scripts']['scan_dir'].lower() == 'true':
                    self._config['scripts']['scan_dir'] = True
                else:
                    self._config['scripts']['scan_dir'] = False
            except KeyError:
                self._logger.warning("Config: scripts/scan_dir setting not found. Defaulting based on platform.")
                if sys.implementation.name == 'cpython':
                    # Scan_dir not included, default it to True since we're on linux.
                    self._config['scripts']['scan_dir'] = True
                    self._logger.warning("Config: cpython, this is likely linux/posix, enabling.")
                else:
                    self._logger.warning("Config: circuitpython, disabling, not supported.")
                    self._config['scripts']['scan_dir'] = False

        # If files isn't explicitly defined, make it an empty list.
        if 'files' not in self._config['scripts']:
            self._config['scripts']['files'] = []

    # Get the complete network config.
    @property
    def system(self):
        """
        System configuration.
        :return: dict
        """
        return self._config['system']

    # No longer needed, will remove later.
    # @property
    # def network(self):
    #     """
    #     Network settings, platform dependent.
    #     :return: dict
    #     """
    #     # On Circuitpython, we both need to support WiFi directly and pull these from the settings.toml environment.
    #     if sys.implementation.name == 'circuitpython':
    #         return {
    #             "wifihw": self._config['system']['wifihw'],
    #             "wifi_ssid": os.getenv('CIRCUITPY_WIFI_SSID'),
    #             "wifi_pw": os.getenv('CIRCUITPY_WIFI_PASSWORD'),
    #             "mqtt_broker": self._config['system']['mqtt']['broker'],
    #             "mqtt_user": self._config['system']['mqtt']['user'],
    #             "mqtt_key": self._config['system']['mqtt']['key'],
    #             "mqtt_log": self._config['system']['mqtt']['log']
    #         }
    #     else:
    #         return {
    #             "wifihw": None,
    #             "wifi_ssid": None,
    #             "wifi_pw": None,
    #             "mqtt_broker": self._config['system']['mqtt']['broker'],
    #             "mqtt_user": self._config['system']['mqtt']['user'],
    #             "mqtt_key": self._config['system']['mqtt']['key'],
    #             "mqtt_log": self._config['system']['mqtt']['log']
    #         }

    # Controls config. No merging of data required here.
    @property
    def controls(self):
        """
        List of configured controls
        """
        return self._config['controls']

    # Displays were already validated, return them when asked.
    @property
    def displays(self):
        """
        List of configured displays
        """
        return self._config['displays']

    @property
    def scripts(self):
        """
        List of configured scripts
        """
        return self._config['scripts']

    @property
    def sensors(self):
        """
        List of configured sensors.
        """
        return self._config['sensors']

    # Allow progressive deletion of the config to free memory.
    def del_controls(self):
        """
        Delete controls and garbage collect
        """
        del self._config['controls']
        gc.collect()

    def del_displays(self):
        """
        Delete displays and garbage collect
        """
        del self._config['displays']
        gc.collect()

    def del_scripts(self):
        """
        Delete scripts and garbage collect
        """
        del self._config['scripts']
        gc.collect()
