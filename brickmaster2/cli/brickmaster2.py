#!/usr/bin/python3
# Brickmaster2 Command Executor.
import brickmaster2
import argparse
from pathlib import Path
from pid import PidFile
import pwd
import os
import sys

# Do some argument parsing here.
cmd_opts = None

def main():
    print("CobraBay Parking System - {}".format(brickmaster2.__version__))
    print("Running as '{}'".format(pwd.getpwuid(os.getuid()).pw_name))
    # Parse command line options.
    parser = argparse.ArgumentParser(
        description="CobraBay Parking System"
    )
    parser.add_argument("-c", "--config", default="./config.json", help="Config file location.")
    parser.add_argument("-r", "--rundir", default="/tmp", help="Run directory, for the PID file.")
    args = parser.parse_args()

    config_path = Path(args.config)
    if not config_path.is_absolute():
        print("Config file path is not absolute. Presuming it's relative to current directory.")
        config_path = Path.cwd() / config_path
    if not config_path.is_file():
        print("Config file '{}' does not exist! Cannot continue!")
        sys.exit(1)

    print("Using config file '{}'".format(config_path))

    # Start the main operating loop.
    try:
        with PidFile('CobraBay_' + config_path.stem, piddir=args.rundir) as p:
            print("Running as PID {}".format(p.pid))

            # Initialize the system
            print("Initializing...")
            bm2 = brickmaster2.BrickMaster2(config_file=str(config_path))
            # Start.
            print("Initialization complete. Operation start.")
            bm2.run()

    except pid.base.PidFileAlreadyLockedError:
        print("Cannot start, already running!")

