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
    print(hex(i2c_addr))