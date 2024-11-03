# BrickMaster2 Core

import adafruit_logging as logging
import board
import busio
# import digitalio # May no longer need this.
import gc
import io
import json
import os
import sys
import brickmaster2


class BrickMaster2:
    """
    Core BrickMaster2 class. Create one of these, then run it.
    """
    def __init__(self, config_json, mac_id, wifi_obj=None, sysrun=None):
        """
        BrickMaster2 Core Module

        :param config_json: A JSON config
        :type config_json: str
        :param mac_id: Interface MAC being used as the system ID.
        :type mac_id: str
        :param wifi_obj: Wifi Object. ONLY used for CircuitPython
        :type wifi_obj: brickmaster2.network.BM2WiFi
        """
        # Force a garbage collection
        gc.collect()

        # Initialize variables.
        self._controls = {} # Controls
        self._displays = {} # I2C displays
        self._indicators = { 'sysrun': sysrun } # LED indicators, if any.
        self._i2c_bus = None
        # If system running indicator was passed, use it, otherwise set up a null indicator.
        if self._indicators['sysrun'] is None:
            self._indicators['sysrun'] = brickmaster2.controls.CtrlNull('sysrun', 'System Status Null', self)

        self._scripts = {} # Scripts
        self._extgpio = {} # GPIO Expanders (ie: AW9523 boards)
        self._active_script = None
        # Lists for displays that show the time or date.
        self._clocks = []
        self._dates = []

        # Save the MAC/system id
        self._mac_id = mac_id
        print("Mac ID is: {}".format(mac_id))
        # Save the Wifi object.
        self._wifi_obj = wifi_obj

        # If we're on a general-purpose linux system, register signal handlers to get signals from elsewhere.
        if os.uname().sysname.lower() == 'linux':
            global signal
            import signal
            self._register_signal_handlers()

        # The Adafruit logger doesn't support child loggers. This is a small
        # enough package, everything goes through the same logger.
        self._logger = logging.getLogger('BrickMaster2')
        # Start out at the DEBUG level. The Config module will load the log level
        # From the config file and adjust appropriately.
        self._logger.setLevel(logging.DEBUG)

        # Validate the config and process it.
        self._bm2config = brickmaster2.BM2Config(config_json)

        # Reset the log level based on the config.
        self._logger.debug("Core: Setting logging level to '{}'".format(self._bm2config.system['log_level']))
        self._logger.setLevel(self._bm2config.system['log_level'])

        # Set up the status indicator, if available.
        self._logger.debug("Core: System config is: {}".format(self._bm2config.system))
        # Create status indicators.
        self._logger.info("Core: Creating status indicator controls.")

        for target in [('neton','Network Connected'),('netoff','Network Disconnected')]:
            id = target[0]
            name = target[1]
            self._logger.debug("Core: Creating indicator for '{}'".format(id))
            try:
                if self._bm2config.system['indicators'][id] is not None:
                    self._indicators[id] = brickmaster2.controls.CtrlSingle(id, name, self,
                                                                            self._bm2config.system['indicators'][id],15)
                else:
                    self._logger.warning(f"Core: No pin defined for status LED '{id}'. Cannot configure.")
                    self._indicators[id] = brickmaster2.controls.CtrlNull(id, name)
            except (KeyError, TypeError):
                 self._logger.warning(f"Core: No pin defined for status LED '{id}'. Cannot configure.")
                 self._indicators[id] = brickmaster2.controls.CtrlNull(id, name)
            except AttributeError:
                 self._logger.warning("Core: Status LED pin '{}' for '{}' cannot be configured.".format(
                     self._bm2config.system['indicators'][id], id))
                 self._indicators[id] = brickmaster2.controls.CtrlNull(id, name, self)

        # All indicators should be configured.
        self._logger.info("Core: Configured indicators - {}".format(self._indicators))
        # Set the system indicator on.
        # This should have been done earlier, but in case it wasn't, we do it again here.
        self._indicators['sysrun'].set('on')

        # Set up the I2C Bus.
        self._setup_i2c_bus()

        gc.collect()

        # Create the controls. Set the publish time to the system-wide publish time.
        self._create_controls(publish_time=self._bm2config.system['publish_time'])
        self._bm2config.del_controls()
        # Create the displays.
        self._create_displays()
        self._bm2config.del_displays()
        # Create the scripts
        self._create_scripts()
        self._bm2config.del_scripts()

        # Set up the network.
        self._logger.debug("Setting up network with config options: {}".format(self._bm2config.system))

        if sys.implementation.name == 'cpython':
            self._logger.info("Core: Setting up network for general-purpose OS.")
            from .network.linux import BM2NetworkLinux
            self._network = BM2NetworkLinux(self,
                                            system_id=self._mac_id,
                                            short_name=self._bm2config.system['id'],
                                            long_name=self._bm2config.system['name'],
                                            broker=self._bm2config.system['mqtt']['broker'],
                                            mqtt_username=self._bm2config.system['mqtt']['user'],
                                            mqtt_password=self._bm2config.system['mqtt']['key'],
                                            mqtt_log=self._bm2config.system['mqtt']['log'],
                                            neton=self._indicators['neton'],
                                            netoff=self._indicators['netoff'],
                                            ha_discover=self._bm2config.system['ha_discover'],
                                            ha_area=self._bm2config.system['ha_area'],
                                            log_level=self._bm2config.system['log_level']
                                            )
        elif sys.implementation.name == 'circuitpython':
            self._logger.info("Core: Setting up network for CircuitPython board.")
            from .network.circuitpython import BM2NetworkCircuitPython
            self._network = BM2NetworkCircuitPython(self,
                                            wifi_obj=self._wifi_obj,
                                            system_id=self._mac_id,
                                            short_name=self._bm2config.system['id'],
                                            long_name=self._bm2config.system['name'],
                                            broker=self._bm2config.system['mqtt']['broker'],
                                            mqtt_username=self._bm2config.system['mqtt']['user'],
                                            mqtt_password=self._bm2config.system['mqtt']['key'],
                                            mqtt_log=self._bm2config.system['mqtt']['log'],
                                            neton=self._indicators['neton'],
                                            netoff=self._indicators['netoff'],
                                            ha_discover=self._bm2config.system['ha_discover'],
                                            ha_area=self._bm2config.system['ha_area'],
                                            log_level=self._bm2config.system['log_level']
                                            )
        else:
            self._logger.critical("Core: Implementation '{}' unknown, cannot determine correct network module.".
                                  format(sys.implementation.name))
            sys.exit(1)

        # Now that the network is up, inform the network module about all the controls, scripts and displays!
        self._logger.debug("Core: Registering controls with network module.")
        for control in self._controls:
            self._network.register_object(self._controls[control])

        self._logger.debug("Core: Registering scripts with network module")
        for script in self._scripts:
            self._network.register_object(self._scripts[script])

        gc.collect()

        if os.uname().sysname.lower() == 'linux':
            self._logger.critical("Running with PID: {}".format(os.getpid()))

    def run(self):
        """
        Main run loop.
        """
        self._logger.debug("Core: Entering run loop.")
        while True:
            # Poll the network.
            self._network.poll()

            # Update controls which have timers.
            for control in self._controls:
                if isinstance(self._controls[control], brickmaster2.controls.CtrlFlasher):
                    self._controls[control].update()

            # If there's an active script, do it.
            if self._active_script is not None:
                # self._logger.debug(f"Core: Script active, executing '{self._active_script}'")
                self._scripts[self._active_script].execute(implicit_start=True)
                # Check to see if the script has gone back to idle.
                if self._scripts[self._active_script].status == 'OFF':
                    self._active_script = None
            else:
                # Otherwise, have the displays do their idle thing.
                # Push time and date to displays that need it.
                # self._logger.debug("Core: Showing idle display state.")
                for display in self._displays:
                    self._displays[display].show_idle()

    def callback_scr(self, client, topic, message):
        """
        Callback for script commands.

        :param client: client
        :param topic: Topic message was sent one
        :param message: Message object.
        :return:
        """
        # Convert the message payload (which is binary) to a string.
        message_text = str(message.payload, 'utf-8')
        # Message text *should* be the name of the script to execute, or Inactive/Abort.
        self._logger.debug("Core: Received script callback message '{}'".format(message_text))
        if message_text in ('Inactive','Abort'):
            # Make the currently active script off. This will reset internal counters.
            self._scripts[self._active_script].set('OFF')
            # Unselect the active script. This publishes 'Inactive' on the next poll.
            self._active_script = None
        else:
            # So now we presume this is the full name of a script. Try to string match it.
            for script_id in self._scripts:
                if self._scripts[script_id].name == message_text:
                    if self._active_script is None:
                        self._logger.debug("Core: Activating script '{}'".format(message_text))
                        self._active_script = script_id
                    else:
                        self._logger.warning("Core: Cannot activate script '{}', script '{}' is already active.".
                                             format(message_text, self._scripts[self._active_script].name))
                    return
            # If we get here, something has gone wrong.
            self._logger.warning("Core: Could not match script '{}' against configured scripts.".format(message_text))

    def _setup_aw9523(self, addr):
        # Condition
        try:
            import adafruit_aw9523
        except ImportError:
            self._logger.critical("Sys: Cannot import modules for GPIO AW9523 control. Exiting!")
            sys.exit(1)
        if isinstance(addr, str):
            addr = int(addr)
        aw = adafruit_aw9523.AW9523(self._i2c_bus, addr)
        return aw

    # Methods to create our objects. Called during setup, or when we're asked to reload.
    def _create_controls(self, publish_time=15):
        """
        Create all the controls in the configuration.

        :param publish_time:
        :return:
        """
        # self._logger.debug("Sys: Memory free at start of control creation: {}".format(gc.mem_free()))
        self._logger.debug("Sys: Controls to create - {}".format(self._bm2config.controls))
        for control_cfg in self._bm2config.controls:
            self._logger.debug("Setting up control '{}' as type '{}'".
                               format(control_cfg['id'], control_cfg['type']))
            self._logger.debug("Complete control config: {}".format(control_cfg))

            # Check for extio boards (AW9523s)
            if control_cfg['extio'] is not None:
                if control_cfg['extio'] not in self._extgpio.keys():
                    self._logger.debug(f"Core: No AW9523 exists at address '{control_cfg['extio']}'. Creating.")
                    self._extgpio[control_cfg['extio']] = self._setup_aw9523(control_cfg['extio'])
                else:
                    self._logger.debug(f"Core: AW9523 already initialized at address '{control_cfg['extio']}'")
                extio_obj = self._extgpio[control_cfg['extio']]
            else:
                extio_obj = None

            # Check the type to create the correct object type.
            # try:
            if control_cfg['type'].lower() == 'single':
                print("Will pass argments:")
                print(dict(**control_cfg))
                self._controls[control_cfg['id']] = brickmaster2.controls.CtrlSingle(
                    id = control_cfg['id'],
                    name = control_cfg['name'],
                    core = self,
                    pins = control_cfg['pins'],
                    publish_time = publish_time,
                    extio_obj = extio_obj,
                    icon = control_cfg['icon'],
                    log_level=self._bm2config.system['log_level'])
            # elif control_cfg['type'].lower() == 'latching':
            #     print("Will pass argments:")
            #     print(dict(**control_cfg))
            #     self._controls[control_cfg['id']] = (brickmaster2.controls.CtrlLatching(**control_cfg, core=self,
            #         publish_time=publish_time, extio_obj=extio_obj, log_level=self._bm2config.system['log_level']))
            elif control_cfg['type'].lower() == 'flasher':
                self._controls[control_cfg['id']] = (brickmaster2.controls.CtrlFlasher(
                    id = control_cfg['id'],
                    name = control_cfg['name'],
                    core = self,
                    pinlist = control_cfg['pins'],
                    loiter_time = control_cfg['loiter_time'],
                    switch_time = control_cfg['switch_time'],
                    publish_time = publish_time,
                    extio_obj = extio_obj,
                    icon = control_cfg['icon'],
                    log_level=self._bm2config.system['log_level']))
            # except (AssertionError, AttributeError, ValueError, KeyError) as e:
            #      self._logger.warning(f"Core: Could not create control '{control_cfg['id']} - '{e}'")

            # This is all the old setup logic.
            # awboard=None
            # if control_cfg['type'].lower() == 'gpio':
            #     # Nothing special to do for on-board GPIO.
            #     pass
            # elif control_cfg['type'].lower() == 'aw9523':
            #     if control_cfg['addr'] not in self._extgpio.keys():
            #         self._logger.debug("No AW9523 exists at address '{}'. Creating.".format(control_cfg['addr']))
            #         self._extgpio[control_cfg['addr']] = self._setup_aw9523(control_cfg['addr'])
            #     else:
            #         self._logger.debug("AW9523 already initialized at address '{}'".format(control_cfg['addr']))
            #     awboard=self._extgpio[control_cfg['addr']]
            # try:
            #     self._controls[control_cfg['id']] = (
            #         brickmaster2.controls.CtrlSingle(**control_cfg, core=self, publish_time=publish_time, awboard=awboard,
            #                                          log_level=self._bm2config.system['log_level']))
            # except (AssertionError, AttributeError, ValueError):
            #     self._logger.warning("Could not create control.")
            # gc.collect()
            # self._logger.debug("Memory free after creation of control '{}': {}".format(control_cfg['control_name'],
            #                                                                            gc.mem_free()))

    def _create_displays(self):
        if len(self._bm2config.displays) == 0:
            self._logger.debug("Core: No displays configured, nothing to initialize.")
            return

        if self._i2c_bus is None:
                self._logger.error("Core: Cannot set up I2C displays without working I2C bus!")
                return

        # Set up the displays.
        for display_cfg in self._bm2config.displays:
            self._logger.info(f"Core: Setting up display '{display_cfg['name']}'")
            self._displays[display_cfg['name']] = brickmaster2.Display(display_cfg, self._i2c_bus, )
            if display_cfg['idle']['show'] == 'time':
                self._clocks.append(display_cfg['name'])
            elif display_cfg['idle']['show'] == 'date':
                self._dates.append(display_cfg['name'])

    def _create_scripts(self):
        # If we're on Linux and scan files is enable, get a list of all the JSON files.
        self._logger.debug("Scan dir setting: {}".format(self._bm2config.scripts['scan_dir']))
        if os.uname().sysname.lower() == 'linux' and self._bm2config.scripts['scan_dir']:
            self._logger.debug("Script directory scan set to: {}".format(self._bm2config.scripts['scan_dir']))
            from pathlib import Path
            script_dir = Path(self._bm2config.scripts['dir'])
            self._logger.debug("Core: Script path is '{}'".format(script_dir))
            # Make the path absolute.
            if not script_dir.is_absolute():
                self._logger.debug("Core: Making script path absolute.")
                script_dir = Path.cwd() / script_dir
                self._logger.debug("Core: Script path is now '{}'".format(script_dir))
            script_list = list(script_dir.glob("*.json"))
            script_list = list(map(lambda e: str(e), script_list))
        else:
            # Otherwise, assemble direct strings.
            script_list = []
            for file in self._bm2config.scripts['files']:
                script_list.append(self._bm2config.scripts['dir'] + '/' + file)
        self._logger.debug("Assembled script list: {}".format(script_list))

        # script_dir = Path.cwd() / "scripts"
        for script_file in script_list:
            self._logger.info("Setting up script: {}".format(script_file))
            try:
                f = io.open(script_file, mode="r", encoding="utf-8")
                with f as source:
                    script_data = json.load(source)
            except FileNotFoundError:
                self._logger.warning("File '{}' specified but does not exist! Skipping.".format(script_file))
            except json.decoder.JSONDecodeError:
                self._logger.warning("Could not decode JSON for script '{}'. Skipping.".format(script_file))
            else:

                self._logger.debug("Loaded script JSON from file {}.".format(script_file))
                try:
                    if script_data['disable'] == 'true':
                        continue
                except KeyError:
                    self._logger.debug("Core: Script '{}' not explicitly disabled. presuming enabled.".
                                       format(script_data['script']))
                try:
                    if script_data['type'] == 'flight':
                        self._logger.debug("Core: Creating flight script object '{}'".format(script_data['script']))
                        script_obj = brickmaster2.scripts.BM2FlightScript(script_data, self._controls, self._displays)
                    else:
                        self._logger.debug("Creating basic script object '{}'".format(script_data['script']))
                        script_obj = brickmaster2.scripts.BM2Script(script_data, self._controls)
                except KeyError:
                    self._logger.debug("Creating basic script object...")
                    script_obj = brickmaster2.scripts.BM2Script(script_data, self._controls)
                # Pass the script object the script data along with the controls that exist.

                self._scripts[script_obj.name] = script_obj

    def _reload_config(self):
        """
        Stud to support config reloading....later?
        :return:
        """
        self._logger.warning("Reload configuration not currently supported.")

    def _print_or_log(self, level, message):
        try:
            logger = getattr(self._logger, level)
            logger(message)
        except AttributeError:
            print(message)

    def _setup_aw9523(self, addr):
        """
        Set up an AW9523 I/O Expander on the given address. Uses the system-wide I2C bus.
        """

        # Conditionally import the libraries.
        try:
            import adafruit_aw9523
        except ImportError:
            self._logger.critical("Sys: Cannot import modules for GPIO AW9523 control. Exiting!")
            sys.exit(1)
        if isinstance(addr, str):
            addr = int(addr)
        aw = adafruit_aw9523.AW9523(self._i2c_bus, addr)
        return aw

    def _setup_i2c_bus(self):
        if self._bm2config.system['i2c'] is not None:
            try:
                self._i2c_bus = busio.I2C(board.SCL, board.SDA)
            except RuntimeError as e:
                self._logger.error("Received Runtime Error while setting up I2C")
                self._logger.error(str(e))
                self._i2c_bus = None
            except ValueError as e:
                self._logger.error("Received Value Error while setting up I2C")
                self._logger.error(str(e))
                self._i2c_bus = None
        else:
            self._logger.info("Core: No I2C bus defined. Skipping setup.")
            self._i2c_bus = None


    # Active script. Returns friendly name of the Active Script. Used to send to MQTT.
    @property
    def active_script(self):
        """
        Report the active script, if any.

        :return:
        """
        if self._active_script is None:
            return "Inactive"
        else:
            return self._scripts[self._active_script].name

    # Private Properties


    # System Signal Handling
    def _register_signal_handlers(self):
        """
        Sets up POSIX signal handlers.
        :return:
        """
        self._print_or_log("debug", "Core: Registering signal handlers.")
        # Reload configuration.
        signal.signal(signal.SIGHUP, self._reload_config)
        # Terminate cleanly.
        # Default quit
        signal.signal(signal.SIGTERM, self._signal_handler)
        # Quit and dump core. Not going to do that, so
        signal.signal(signal.SIGQUIT, self._signal_handler)

        # All other signals are some form of error.
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGILL, self._signal_handler)
        signal.signal(signal.SIGTRAP, self._signal_handler)
        signal.signal(signal.SIGABRT, self._signal_handler)
        signal.signal(signal.SIGBUS, self._signal_handler)
        signal.signal(signal.SIGFPE, self._signal_handler)
        # signal.signal(signal.SIGKILL, receiveSignal)
        signal.signal(signal.SIGUSR1, self._signal_handler)
        signal.signal(signal.SIGSEGV, self._signal_handler)
        signal.signal(signal.SIGUSR2, self._signal_handler)
        signal.signal(signal.SIGPIPE, self._signal_handler)
        signal.signal(signal.SIGALRM, self._signal_handler)

    def cleanup_and_exit(self, signalNumber=None, message=None):
        """
        Shut off controls and displays, then exit.

        :param signalNumber: Signal called for exit.
        :return: None
        """
        if isinstance(signalNumber, int) and 'signal' in sys.modules:
            signame = signal.Signals(signalNumber).name
            self._print_or_log("critical", "Core: Exit triggered by {}. Performing cleanup actions.".format(signame))
        else:
            self._print_or_log("critical", "Core: Exit requested. Performing cleanup actions.")

        # Set the controls to off.
        self._print_or_log("critical", "Core: Setting controls off....")
        # Turn off all the controls
        try:
            for control in self._controls:
                self._print_or_log("info", "Core: \t{}".format(control))
                self._controls[control].set("off")
        except AttributeError:
            self._print_or_log("critical", "Core: Controls not defined, nothing to do.")
        # Turn off all the displays
        self._print_or_log("critical", "Core: Setting displays off....")
        try:
            for display in self._displays:
                self._print_or_log("info", "Core: \t{}".format(display))
                self._displays[display].off()
        except AttributeError:
            self._print_or_log("critical", "Core: Displays not defined, nothing to do.")
        # Poll the network one more time to ensure the new control status is sent.
        # try:
        #     self._network.poll()
        # except Exception:
        #     pass
        # self._print_or_log("critical", "Core: Disconnecting network.")
        # # Disconnect
        # This disconnect call is initiating a poll, which isn't what we want. For now, we can exclude it and rely
        # on the last will to send the offline message.
        # self._network.disconnect()
        self._print_or_log("critical", "Core: Setting system run light off.")
        # Set the system light off.
        try:
            self._led_sysrun.value = False
        except AttributeError:
            pass
        self._print_or_log("critical", "Core: Cleanup complete.")
        # Return a signal. We consider some exits clean, others we throw back the signal number that called us.
        if signalNumber in (None, 15):
            sys.exit(0)
        else:
            sys.exit(signalNumber)

    def _signal_handler(self, signalNumber=None, frame=None):
        """

        :param signalNumber: Signal number
        :param frame: Frame
        :return:
        """
        print("Caught signal {}".format(signalNumber))
        self.cleanup_and_exit(signalNumber)
