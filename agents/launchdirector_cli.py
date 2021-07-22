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

# Basic libraries
import signal, sched, time, argparse, json, yaml, pprint
from datetime import timedelta
from requests import Request, Session

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
	# Open up the session
	stage_session = Session()

	while fst <= len(flight_data):
		time.sleep(max(0,next_time - time.time()))
		update_flight(fst,stage_session)
		fst = fst + 1
		next_time += (time.time() - next_time) // 1 * 1 + 1

def update_flight(fst,stage_session):
	# We use 'flight sim time' (fst) to distinguish from actual mission elapsed time
	current_state = flight_data[fst]

	# Push to displays
	display['met'].print(current_state['t'])
	display['alt'].print(current_state['a'])
	display['vel'].print(current_state['v'])


	rest_append = str()
	# If there's a stage state change, call the REST url.
	if 'rest' in current_state.keys():
		prepared = stage_session.prepare_request(current_state['rest'])
		stage_session.send(prepared)
		rest_append = '\t' + str(current_state['rest'].json)

	# Print to log
	print(str(current_state['t']) + "\t" + str(current_state['a']) + "\t" + str(current_state['v']) + "\t" + str(current_state['b']) + rest_append)

# Function to shut everything down.
def all_off():
	for disp in display:
		display[disp].fill(0)

def keyboardInterruptHandler(signal, frame):
	all_off()
	exit(0)

signal.signal(signal.SIGINT,keyboardInterruptHandler)

def read_flight_data(flight_data_raw):
	# Calculate out the stage!
	flight_data = {}
	flight_sequence = 1

	# list to accumulate stages.
	stages_known = set()

	# Set up the pre-roll
	pre_roll = int(flight_data_raw['pre-roll']) * -1
	while pre_roll < 0:
		if pre_roll > flight_data_raw['ignition']:
			flight_data[flight_sequence] = { "t": time_7s(pre_roll), "b": 1, "a": number_7s(0), "v": number_7s(0)}
		else:
			flight_data[flight_sequence] = { "t": time_7s(pre_roll), "b": 0, "a": number_7s(0), "v": number_7s(0)}
		pre_roll = pre_roll + 1
		flight_sequence = flight_sequence + 1

	flight_data[flight_sequence] = { "t": time_7s(0), "b": 1, "a": number_7s(0), "v": number_7s(0) }

	# Save the Zero-Mark for later calculations
	zero_mark = flight_sequence

	# Set up staging variables variables
	working_burn = 1
	# Add in each stage in sequence.
	while working_burn <= len(flight_data_raw['burns']):

		# 1st stage has no previous stage
		if working_burn == 1:
			# Remove the pre-launch burn time from the total remaining burn time, since that doesn't contribute to altitude/velocity
			burn_time = flight_data_raw['burns'][working_burn]['burn_time'] + flight_data_raw['ignition']
			dV = flight_data_raw['burns'][working_burn]['final_velocity'] / burn_time
			dA = flight_data_raw['burns'][working_burn]['final_alt'] / burn_time
		else:
			burn_time = flight_data_raw['burns'][working_burn]['burn_time']
			# Find the ending data from the previous stage.
			previous = max(flight_data)
			# Average flight profile for this burn
			dV = (flight_data_raw['burns'][working_burn]['final_velocity'] - float(flight_data[previous]['v']) )/ burn_time
			dA = (flight_data_raw['burns'][working_burn]['final_alt'] - float(flight_data[previous]['a']) ) / burn_time
		target_time = flight_sequence + int(flight_data_raw['burns'][working_burn]['burn_time'])

		# for REST request creation, later.
		rest_data = ( (flight_sequence, 'on' ), (target_time, 'off') )

		# Iterate and create flight sequences
		while flight_sequence <= target_time:
			flight_data[flight_sequence] = {
				"t": time_7s(flight_sequence-zero_mark),
				"b": working_burn,
				"a": number_7s(float(flight_data[flight_sequence-1]['a']) + dA),
				"v": number_7s(float(flight_data[flight_sequence-1]['v']) + dV)
			}
			flight_sequence = flight_sequence + 1

		# Create stage on and off REST queries
		for (time, state) in rest_data:
			# If a request is already defined for this flight time, do some special handling.
			if 'rest' in flight_data[time].keys():
				json = flight_data[time]['rest']['json']
				json[flight_data_raw['burns'][working_burn]['stage']].append(state)
				request = Request('POST', config['base_url'], json=json)

			else:
				# Otherwise, safely create a new request.
				json = { flight_data_raw['burns'][working_burn]['stage']: state }
				request = Request('POST', config['base_url'], json=json)
				flight_data[time]['rest'] = request

		# Process an inter-stage pause.
		if flight_data_raw['burns'][working_burn]['interstage']:
			# During inter-stage, altitude and time increase, but velocity doesn't.
			target_time = flight_sequence + int(flight_data_raw['burns'][working_burn]['interstage'])
			while flight_sequence <= target_time:
				flight_data[flight_sequence] = {
					"t": time_7s(flight_sequence - zero_mark),
					"b": working_burn,
					"a": number_7s(float(flight_data[flight_sequence-1]['a']) + dA),
					"v": number_7s(float(flight_data[flight_sequence-1]['v']))
				}
				flight_sequence = flight_sequence + 1

		# Add this stage to the stage set.
		stages_known.add(flight_data_raw['burns'][working_burn]['stage'])

		working_burn = working_burn + 1

	# Add in the post-roll
	if flight_data_raw['post-roll']:
		target_time = flight_sequence + flight_data_raw['post-roll']
		while flight_sequence <= target_time:
			flight_data[flight_sequence] = {
				# Freeze all values.
				"t": flight_data[flight_sequence-1]['t'],
				"b": "Post-roll",
				"a": flight_data[flight_sequence-1]['a'],
				"v": flight_data[flight_sequence-1]['v']
			}
			flight_sequence = flight_sequence + 1

	# Append the known stages to the flight data to return it.
	flight_data['stages'] = stages_known

	return(flight_data)

def load_config(config_file):
	print("Processing configuration.")
	global config
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
	pp = pprint.PrettyPrinter()

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
	flight_data_file = open(args.f,'r')
	flight_data_raw = yaml.load(flight_data_file)
	flight_data_file.close()

	# Pass the JSON to the flight plan parser
	flight_data = read_flight_data(flight_data_raw)
	print("Flight plan loaded.")

	# Begin launch.
	print("Clock\tAlt\tSpeed\tBurn")
	launch_time = time.time()
	launch()
	all_off()
