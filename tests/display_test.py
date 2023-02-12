# BrickMaster2
# Test 7 Segment Displays

import argparse
import board
from adafruit_ht16k33.segments import Seg7x4, BigSeg7x4
import sys
import time

parser = argparse.ArgumentParser(
    prog = 'display_test',
    description = 'Test 7-segment I2C Displays',
    epilog = 'A part of BrickMaster2'
)

parser.add_argument('-a', '--address', nargs='+')
args = parser.parse_args()

# Create the I2C interface.
i2c = board.I2C()
displays = []

for i2c_addr in args.address:
    # Convert to Base 16 integer
    i2c_addr = int(i2c_addr, 16)
    try:
        display_object = Seg7x4(i2c, address=i2c_addr)
    except ValueError:
        print("No display found at address: {}".format(hex(i2c_addr)))
    else:
        print("Initialized display on address {}".format(hex(i2c_addr)))
        displays.append(display_object)

# Check for having *any* displays to test on.
if len(displays) == 0:
    print("No displays to tests. Exiting!")
    sys.exit(1)
elif len(displays) < len(args.address):
    print("Not all displays initialized. Proceeding with successful displays.")

index = 0
print("Display output:")
try:
    while True:
        print(str(index)*4, end="\r")
        for display in displays:
            display.print(str(index)*4)
            if index % 2 == 0:
                display.ampm = True
        if index == 9:
            index = 0
        else:
            index += 1
        time.sleep(1)
except KeyboardInterrupt:
    for display in displays:
        for digit in (0, 1, 2, 3):
            display.set_digit_raw(digit, 0b00000000)
