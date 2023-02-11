# Brickmaster2
# Circuitpython Executor

# Run this is you're on a CircuitPython board.
# Otherwise you probably want brickmaster2.py, which is more full-featured.
import bm2lib.brickmaster2 as brickmaster2

# Initialize the object
bm2 = brickmaster2.BrickMaster2(cmd_opts={'circuitpython': True})

# Start it.
bm2.run()