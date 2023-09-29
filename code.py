#!/usr/bin/python3
# BrickMaster2 Executor for CircuitPython Boards

from brickmaster2.brickmaster2 import BrickMaster2
import time
import supervisor

try:
    # Create the BrickMaster2 Object.
    bm2 = BrickMaster2(config_file='config-bmlc.json')
    # Run it.
    bm2.run()
except MemoryError as e:
    print(e)
    print("Waiting for 10s before soft reset.")
    time.sleep(10)
    supervisor.reload()