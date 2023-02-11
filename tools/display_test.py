# BrickMaster2
# Test 7 Segment Displays

import argparse

parser = argparse.ArgumentParser(
    prog = 'display_test',
    description = 'Test 7-segment I2C Displays',
    epilog = 'A part of BrickMaster2'
)

parser.add_argument('-a', '--address', nargs='+')
args = parser.parse_args()

for i2c_addr in args.address:
    # Convert to Base 16 integer
    i2c_addr = int(i2c_addr, 16)
    print(hex(i2c_addr))