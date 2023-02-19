# BrickMaster2 Core

import adafruit_logging as logging
import atexit
from .config import BM2Config
from .controls import CtrlGPIO
from .network import BM2Network

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

        # Set up the network.
        self._network = BM2Network(self._bm2config.network_config)

        # Dict to store control objects.
        self._controls = {}

        # Set up the controls.
        for control_cfg in self._bm2config.controls:
            self._logger.info("Setting up control '{}'".format(control_cfg['name']))
            if control_cfg['type'].lower() == 'gpio':
                self._controls[control_cfg['name']] = CtrlGPIO(control_cfg)

        self._logger.debug("Have controls: {}".format(self._controls))

        # Pass the controls to the Network module.
        for control_name in self._controls:
            self._network.add_control(self._controls[control_name])

    def run(self):
        self._logger.info("Entering run loop.")
        while True:
            # Poll the network.
            self._network.poll()

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
        # Poll the network one more time to ensure the new control status is sent.
        self._network.poll()
        # Send an offline message.
        self._network._publish('connectivity', 'offline')
        self._print_or_log("critical", "Cleanup complete.")
