# BrickMaster2 Core

import adafruit_logging as logging
import atexit
from .config import BM2Config
from .controls import CtrlGPIO
from .display import Display
from .network import BM2Network
from .scripts import BM2Script, BM2FlightScript
import board
import busio
import os
import io
import json


class BrickMaster2:
    def __init__(self, cmd_opts=None):
        # # First thing we do is register our cleanup method.
        atexit.register(self.cleanup_and_exit)

        if cmd_opts is None:
            cmd_opts = {}
        # The Adafruit logger doesn't support child loggers. This is a small
        # enough package, everything goes through the same logger.
        self._logger = logging.getLogger('BrickMaster2')
        # Start out at the DEBUG level. The Config module will load the log level
        # From the config file and adjust appropriately.
        self._logger.setLevel(logging.DEBUG)

        # Create the config processor
        self._bm2config = BM2Config()

        # Setup the I2C Bus.
        self._setup_i2c_bus(None)

        # Set up the network.
        self._network = BM2Network(self, self._bm2config.system)

        # Initiatlize dicts to store objects.
        self._controls = {}
        self._displays = {}
        self._scripts = {}
        self._active_script = None
        # Lists for displays that show the time or date.
        self._clocks = []
        self._dates = []

        # Create the controls
        self._create_controls()
        # Create the displays.
        self._create_displays()
        # Create the scripts
        self._create_scripts()

    def run(self):
        self._logger.info("Entering run loop.")
        while True:
            # Poll the network.
            self._network.poll()

            # If there's an active script, do it.
            if self._active_script is not None:
                self._scripts[self._active_script].execute(implicit_start=True)
                # Check to see if the script has gone back to idle.
                if self._scripts[self._active_script].status == 'idle':
                    self._active_script = None
            else:
                # Otherwise, have the displays do their idle thing.
                # Push time and date to displays that need it.
                for display in self._displays:
                    self._displays[display].show_idle()

    # Callback to get script execution requests.
    def callback_scr(self, client, topic, message):
        # Convert the message payload (which is binary) to a string.
        script_name = topic.split('/')[-2]
        self._logger.debug("Core received '{}' request for script '{}'".format(message, script_name))
        # Starting a script.
        if message.lower() == 'start':
            # If we don't have an active script, mark this script for starting.
            if self._active_script is None:
                self._active_script=script_name
            else:
                self._logger.warning("Cannot start script {}, script {} is already active.".format(script_name, self._active_script))
        elif message.lower() == 'stop':
            # Set the active script to stop
            self._scripts[self._active_script].set('stop')
            self._active_script = None
        else:
            self._logger.info("Ignoring invalid command '{}'".format(message))

    def _setup_i2c_bus(self, i2c_config):
        self._i2c_bus = busio.I2C(board.SCL, board.SDA)

    # Methods to create our objects. Called during setup, or when we're asked to reload.
    def _create_controls(self):
        for control_cfg in self._bm2config.controls:
            self._logger.info("Setting up control '{}'".format(control_cfg['name']))
            if control_cfg['type'].lower() == 'gpio':
                self._controls[control_cfg['name']] = CtrlGPIO(control_cfg)

        # Pass the controls to the Network module.
        for control_name in self._controls:
            self._network.add_item(self._controls[control_name])

    def _create_displays(self):
        # Set up the displays.
        for display_cfg in self._bm2config.displays:
            self._logger.info("Setting up display '{}'".format(display_cfg['name']))
            self._displays[display_cfg['name']] = Display(display_cfg, self._i2c_bus, )
            if display_cfg['idle']['show'] == 'time':
                self._clocks.append(display_cfg['name'])
            elif display_cfg['idle']['show'] == 'date':
                self._dates.append(display_cfg['name'])

    def _create_scripts(self):
        # If we're on Linux and scan files is enable, get a list of all the JSON files.
        self._logger.debug("Script directory scan set to: {}".format(self._bm2config.scripts['scan_dir']))
        if os.uname().sysname.lower() == 'linux' and self._bm2config.scripts['scan_dir']:
            from pathlib import Path
            script_dir = Path(self._bm2config.scripts['dir'])
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
                    if script_data['type'] == 'flight':
                        self._logger.debug("Creating flight script object...")
                        script_obj = BM2FlightScript(script_data, self._controls, self._displays)
                    else:
                        self._logger.debug("Creating basic script object...")
                        script_obj = BM2Script(script_data, self._controls)
                except KeyError:
                    self._logger.debug("Creating basic script object...")
                    script_obj = BM2Script(script_data, self._controls)
                # Pass the script object the script data along with the controls that exist.

                self._scripts[script_obj.name] = script_obj

        for script_name in self._scripts:
            self._network.add_item(self._scripts[script_name])

    # Active script. Returns friendly name of the Active Script. Used to send to MQTT.
    @property
    def active_script(self):
        if self._active_script is None:
            return "None"
        else:
            return self._active_script

    def _print_or_log(self, level, message):
        try:
            logger = getattr(self._logger, level)
            logger(message)
        except AttributeError:
            print(message)

    def cleanup_and_exit(self):
        self._print_or_log("critical", "Exit requested. Performing cleanup actions.")
        # Set the controls to off.
        self._print_or_log("critical", "Setting controls off....")
        # Turn off all the controls
        for control in self._controls:
            self._print_or_log("info", "\t{}".format(control))
            self._controls[control].set("off")
        # Turn off all the displays
        self._print_or_log("critical", "Setting displays off....")
        for display in self._displays:
            self._print_or_log("info", "\t{}".format(display))
            self._displays[display].off()
        # Poll the network one more time to ensure the new control status is sent.
        self._network.poll()
        # Send an offline message.
        self._network._publish('connectivity', 'offline')
        self._print_or_log("critical", "Cleanup complete.")
