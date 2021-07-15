#!/usr/bin/python3

# 7 Segment display tester

# Path for libraries

import argparse, board, time, signal
from adafruit_ht16k33.segments import Seg7x4, BigSeg7x4

# Parse incoming arguments
parser = argparse.ArgumentParser()
parser.add_argument('-a',action='append',help='Addresses of displays to test',required=True)
addresses = parser.parse_args().a

# Set up Segment objects for all provided IDs.

i2c = board.I2C()

d=0
displays = list()
for display in addresses:
	displays.append(Seg7x4(i2c,address=int(display,16)))

# Register keyboard interrupt handler to clean-up.
def keyboardInterruptHandler(signal, frame):
	for disp in displays:
		disp.fill(0)
	exit(0)

signal.signal(signal.SIGINT, keyboardInterruptHandler)

# Iterate and display until interrupted.

i=0
while i <= 11:
	output = str(i) + str(i) + str(i) + str(i)
	for disp in displays:
		disp.print(output)
	time.sleep(1)

	i = i + 1
	if i == 10:
		i = 0
