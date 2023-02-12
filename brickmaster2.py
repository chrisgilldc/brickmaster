#!/usr/bin/python3
# Brickmaster2 Command Executor.


# Do some argument parsing here.
cmd_opts = None

from brickmaster2.brickmaster2 import BrickMaster2
# Create the BrickMaster2 Object.
bm2 = BrickMaster2(cmd_opts)
bm2.run()