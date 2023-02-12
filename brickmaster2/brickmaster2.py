# BrickMaster2 Core

import adafruit_logging as logging
from .config import BM2Config
from .controls import CtrlGPIO
from .network import BM2Network

class BrickMaster2:
    def __init__(self, cmd_opts=None):
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
