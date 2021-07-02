#!/usr/bin/python3

####
#
# Launch Director!
#
# A Brickmaster agent to simulate space launches.
#
####


# Signal handler
import signal
# Basic scheduler
import sched, time
# Datetime conversion
from datetime import timedelta

# Quick 7s formatting library
from format_7s import time_7s, number_7s

# Support for 7-segment displays via Adafruit backpacks.
import board
from adafruit_ht16k33.segments import Seg7x4, BigSeg7x4

# Set up i2c communication
i2c = board.I2C()
# Initialize three displays
mc_clock = BigSeg7x4(i2c,address=0x70)
mc_alt = Seg7x4(i2c,address=0x71)
mc_speed = Seg7x4(i2c,address=0x72)
# Set initial values
mc_clock.print("00:00")
mc_alt.print("0000")
mc_speed.print("0000")


def every(delay, task):
	next_time = time.time() + delay
	while True:
		time.sleep(max(0, next_time - time.time()))
		task()
		next_time += (time.time() - next_time) // delay * delay + delay

def mc_update():
	# Set elapsed clock
	elapsed_time = round(time.time() - launch_time,3)

	# Calculated altitude
	derived_altitude = elapsed_time * 10

	# calculated speed
	derived_speed = elapsed_time * 5

	display_time = time_7s(elapsed_time,4)
	display_alt = number_7s(derived_altitude,4)
	display_speed = number_7s(derived_speed,4)

	# Print to log
	print(display_time + "\t" + display_alt + "\t" + display_speed)

	# Push to displays
	mc_clock.print(display_time)
	mc_alt.print(display_alt)
	mc_speed.print(display_speed)

# Function to shut everything down.
def all_off():
	mc_clock.fill(0)
	mc_alt.fill(0)
	mc_speed.fill(0)

def keyboardInterruptHandler(signal, frame):
	all_off()
	exit(0)

signal.signal(signal.SIGINT,keyboardInterruptHandler)

print("Clock\tAlt\tSpeed")
launch_time = time.time()
every(1,mc_update)
