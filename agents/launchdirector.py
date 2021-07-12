#!/usr/bin/python3

####
#
# Launch Director!
#
# A Brickmaster agent to simulate space launches.
#
####

# Path for Brickmaster libraries.
import sys, os
sys.path.append(os.path.join(os.path.dirname(sys.path[0]),'lib'))

# Config file
stage_file = "saturn5.json"

# Basic libraries
import sys
import signal
import sched, time
from datetime import timedelta
import json

# Quick 7s formatting library
from lib_7s_format import time_7s, number_7s

# Support for 7-segment displays via Adafruit backpacks.
import board
from adafruit_ht16k33.segments import Seg7x4, BigSeg7x4

# Pretty Printing, for debugging.
import pprint
pp = pprint.PrettyPrinter(depth=4)

# Set up i2c communication
i2c = board.I2C()
# Initialize three displays
mc_clock = BigSeg7x4(i2c,address=0x70)
mc_alt = Seg7x4(i2c,address=0x72)
mc_speed = Seg7x4(i2c,address=0x71)
# Set initial values
mc_clock.print("00:00")
mc_alt.print("0000")
mc_speed.print("0000")

def launch():
	next_time = time.time() + 1
	fst = 1
	while fst <= len(flight_data):
		time.sleep(max(0,next_time - time.time()))
		update_flight(fst)
		fst = fst + 1
		next_time += (time.time() - next_time) // 1 * 1 + 1

def update_flight(fst):
	# We use 'flight sim time' (fst) to distinguish from actual mission elapsed time
	current_state = flight_data[fst]

	# Print to log
	print(str(current_state['t']) + "\t" + str(current_state['a']) + "\t" + str(current_state['v']) + "\t" + str(current_state['s']))

	# Push to displays
	mc_clock.print(current_state['t'])
	mc_alt.print(current_state['a'])
	mc_speed.print(current_state['v'])

# Function to shut everything down.
def all_off():
	mc_clock.fill(0)
	mc_alt.fill(0)
	mc_speed.fill(0)

def keyboardInterruptHandler(signal, frame):
	all_off()
	exit(0)

signal.signal(signal.SIGINT,keyboardInterruptHandler)

def read_flight_data(stage_file):

	stage_handle = open(stage_file)
	stage_json = json.load(stage_handle)
	stage_handle.close()
	# Calculate out the stage!
	flight_data = {}
	flight_sequence = 1
	# Set up the pre-roll
	pre_roll = int(stage_json['pre-roll']) * -1
	while pre_roll < 0:
		if pre_roll > stage_json['ignition']:
			flight_data[flight_sequence] = { "t": time_7s(pre_roll), "s": 1, "a": number_7s(0), "v": number_7s(0), "gpio": stage_json['stages']['1']['gpio']}
		else:
			flight_data[flight_sequence] = { "t": time_7s(pre_roll), "s": 0, "a": number_7s(0), "v": number_7s(0), "gpio": 0 }
		pre_roll = pre_roll + 1
		flight_sequence = flight_sequence + 1

	flight_data[flight_sequence] = { "t": time_7s(0), "s": 1, "a": number_7s(0), "v": number_7s(0), "gpio": stage_json['stages']['1']['gpio'] }
	# Save the Zero-Mark for later calculations
	zero_mark = flight_sequence

	# Set up staging variables variables
	working_stage = 1
	# Add in each stage in sequence.
	while working_stage <= len(stage_json['stages']):

		# 1st stage has no previous stage
		if working_stage == 1:
			burn_time = stage_json['stages'][str(working_stage)]['burn_time'] + stage_json['ignition']
			dV = stage_json['stages'][str(working_stage)]['final_velocity'] / burn_time
			dA = stage_json['stages'][str(working_stage)]['final_alt'] / burn_time
		else:
			burn_time = stage_json['stages'][str(working_stage)]['burn_time']
			# Find the ending data from the previous stage.
			previous = max(flight_data)
			dV = (stage_json['stages'][str(working_stage)]['final_velocity'] - float(flight_data[previous]['v']) )/ burn_time
			dA = (stage_json['stages'][str(working_stage)]['final_alt'] - float(flight_data[previous]['a']) ) / burn_time
		target_time = flight_sequence + int(stage_json['stages'][str(working_stage)]['burn_time'])
		while flight_sequence <= target_time:
			flight_data[flight_sequence] = {
				"t": time_7s(flight_sequence-zero_mark),
				"s": working_stage,
				"a": number_7s(float(flight_data[flight_sequence-1]['a']) + dA),
				"v": number_7s(float(flight_data[flight_sequence-1]['v']) + dV)
			}
			flight_sequence = flight_sequence + 1

		# Process an inter-stage pause.
		if stage_json['stages'][str(working_stage)]['interstage']:
			# During inter-stage, altitude and time increase, but velocity doesn't.
			target_time = flight_sequence + int(stage_json['stages'][str(working_stage)]['interstage'])
			while flight_sequence <= target_time:
				flight_data[flight_sequence] = {
					"t": time_7s(flight_sequence - zero_mark),
					"s": working_stage,
					"a": number_7s(float(flight_data[flight_sequence-1]['a']) + dA),
					"v": number_7s(float(flight_data[flight_sequence-1]['v']))
				}
				flight_sequence = flight_sequence + 1

		working_stage = working_stage + 1

	# Add in the post-roll
	if stage_json['post-roll']:
		target_time = flight_sequence + stage_json['post-roll']
		while flight_sequence <= target_time:
			flight_data[flight_sequence] = {
				# Freeze all values.
				"t": flight_data[flight_sequence-1]['t'],
				"s": "Post-roll",
				"a": flight_data[flight_sequence-1]['a'],
				"v": flight_data[flight_sequence-1]['v']
			}
			flight_sequence = flight_sequence + 1

	return(flight_data)

# Flight data prep!
flight_data = read_flight_data('saturn5.json')

print("Flight plan loaded.")
pp.pprint(flight_data)
print("")

print("Clock\tAlt\tSpeed\tStage")
launch_time = time.time()
launch()
all_off()
