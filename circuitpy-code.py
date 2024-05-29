#!/usr/bin/python3
# BrickMaster2 Executor for CircuitPython Boards

# from brickmaster2.brickmaster2 import BrickMaster2
# import time
# import supervisor
# import traceback
#
# try:
#     # Create the BrickMaster2 Object.
#     bm2 = BrickMaster2(config_file='config.json')
#     # Run it.
#     bm2.run()
# except KeyboardInterrupt:
#     print("Halted by user!")
# except BaseException as e:
#     print("Received unhandled exception - ")
#     traceback.print_exception(e)
#     print("Waiting for 30s before soft reset.")
#     time.sleep(30)
#     supervisor.reload()