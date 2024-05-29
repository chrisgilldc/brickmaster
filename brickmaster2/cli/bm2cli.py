#!/usr/bin/python3
# Brickmaster2 Command Executor.
import brickmaster2
import pid
import argparse
from pathlib import Path
from pid import PidFile
import pwd
import os
import sys
from pprint import pprint

import brickmaster2.util

# Do some argument parsing here.
cmd_opts = None

def main():
    print("Brickmaster2 - {}".format(brickmaster2.__version__))
    print("Running as '{}'".format(pwd.getpwuid(os.getuid()).pw_name))
    sys_mac_id = brickmaster2.util.mac_id()
    print("This systems' MAC id is: {}".format(sys_mac_id))
    # Parse command line options.
    parser = argparse.ArgumentParser(
        description="Brickmaster2 MQTT Lego Control System"
    )
    config_group = parser.add_mutually_exclusive_group()
    config_group.add_argument("-c", "--config", action="store", help="Config file path.")
    config_group.add_argument("-nc", "--netconfig", action="store", help="NetConfig URL")
    parser.add_argument("-dc", "--dumpconfig", action="store_true", help="Dump config once loaded")
    parser.add_argument("-r", "--rundir", action="store", default="/tmp", help="Run directory, for the PID file.")
    args = parser.parse_args()

    # Start the main operating loop.
    try:
        with PidFile('CobraBay', piddir=args.rundir) as p:
            print("Running as PID {}".format(p.pid))

            print("Identifying configuration...")

            if args.netconfig:
                print("Loading network config from: {}".format(args.netconfig))
                config_json = brickmaster2.util.fetch_config(args.netconfig)
            else:
                if args.config is None:
                    print("No config path given. Trying './config.json'")
                    config_path = Path.cwd() / 'config.json'
                else:
                    config_path = Path(args.config)
                    if not config_path.is_absolute():
                        print("Specified config file path is not absolute. Trying in working directory.")
                        config_path = Path.cwd() / config_path
                if not config_path.is_file():
                    print("Config file '{}' does not exist! Cannot continue!".format(config_path))
                    sys.exit(1)
                else:
                    config_json = brickmaster2.util.load_config(config_path)

            if args.dumpconfig:
                print("Config read. Dump requested. Here it comes!")
                pprint(config_json)
                print("Now validating...")
            else:
                print("Config read.")

            # Initialize the system
            print("Initializing...")
            bm2 = brickmaster2.BrickMaster2(config_json, sys_mac_id)
            # Start.
            print("Initialization complete. Operation start.")
            bm2.run()

    except pid.base.PidFileAlreadyLockedError:
        print("Cannot start, already running!")

if __name__ == "__main__":
    sys.exit(main())