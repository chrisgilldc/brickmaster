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
import signal, sched, time, argparse, json, yaml
from datetime import timedelta

# Quick 7s formatting library
from lib_7s_format import time_7s, number_7s

# Support for 7-segment displays via Adafruit backpacks.
import board
from adafruit_ht16k33.segments import Seg7x4, BigSeg7x4

# Pretty Printing, for debugging.
import pprint
pp = pprint.PrettyPrinter(depth=4)

# Internal functions
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
	display['met'].print(current_state['t'])
	display['alt'].print(current_state['a'])
	display['vel'].print(current_state['v'])

# Function to shut everything down.
def all_off():
	for disp in display:
		display[disp].fill(0)

def keyboardInterruptHandler(signal, frame):
	all_off()
	exit(0)

signal.signal(signal.SIGINT,keyboardInterruptHandler)

def read_flight_data(stage_json):
	# Calculate out the stage!
	flight_data = {}
	flight_sequence = 1
	# Set up the pre-roll
	pre_roll = int(stage_json['pre-roll']) * -1
	while pre_roll < 0:
		if pre_roll > stage_json['ignition']:
			flight_data[flight_sequence] = { "t": time_7s(pre_roll), "s": 1, "a": number_7s(0), "v": number_7s(0)}
		else:
			flight_data[flight_sequence] = { "t": time_7s(pre_roll), "s": 0, "a": number_7s(0), "v": number_7s(0)}
		pre_roll = pre_roll + 1
		flight_sequence = flight_sequence + 1

	flight_data[flight_sequence] = { "t": time_7s(0), "s": 1, "a": number_7s(0), "v": number_7s(0) }

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

def load_config(config_file):
	print("Processing configuration.")
	# Pull the file into a config yaml.
	try:
		config_file_stream = open(config_file,'r')
	except:
		print("Could not open provided configuration file: " + config_file)
		sys.exit(1)
	try:
		config = yaml.load(config_file_stream)
	except:
		print("Could not parse provided configuration file: " + config_file)
		sys.exit(1)

	# Close the file handle
	config_file_stream.close()

	# Is the configuration valid?
	# Probably should do some config validation here, but......

	# Collapse down to just the Launch Director part.
	config = config['launchdirector']

	# If any displays are defined, set them up.
	if config['displays']:
		global display
		display = {}
		i2c = board.I2C()
		for disp_name in config['displays']:
			# Set up i2c communication
			if config['displays'][disp_name]['size'] == '1':
				display[disp_name] = BigSeg7x4(i2c,address=config['displays'][disp_name]['id'])
			else:
				display[disp_name] = Seg7x4(i2c,address=config['displays'][disp_name]['id'])
			display[disp_name].print("00:00")

# If Agent is run directly, take in the flight plan, run once, then exit.
if __name__ == "__main__":

	# Create a parser for command-line invocation
	parser = argparse.ArgumentParser()
	parser.add_argument('-f',required=True,help="Flight Data JSON file")
	parser.add_argument('-c',default='./launchdirector.cfg',help="Config file (YAML)")
	args = parser.parse_args()

	# Check for the configuration file
	if not os.path.exists(args.c):
		print("Could not find configuration file!")
		sys.exit(1)

	# Load the configuration
	load_config(args.c)

	# Check for the flight plan file
	if not os.path.exists(args.f):
		print("Provided  '" + args.f + "' does not exist.")
		sys.exit(1)

	# Open the flight plan file, suck out the JSON
	flight_data_file = open(args.f)
	flight_data_json = json.load(flight_data_file)
	flight_data_file.close()

	# Pass the JSON to the flight plan parser
	flight_data = read_flight_data(flight_data_json)
	print("Flight plan loaded.")

	# Begin launch.
	print("Clock\tAlt\tSpeed\tStage")
	launch_time = time.time()
	launch()
	all_off()
