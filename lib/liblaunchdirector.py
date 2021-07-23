#!/usr/bin/python3

####
#
# Class library for Launch Director
#
####

# Path for Brickmaster libraries.
import sys, os
sys.path.append(os.path.join(os.path.dirname(sys.path[0]),'lib'))

# Basic libraries
import signal, sched, time, argparse, yaml, threading
from datetime import timedelta
from requests import Request, Session, post

# Quick 7s formatting library
from lib_7s_format import time_7s, number_7s

# Support for 7-segment displays via Adafruit backpacks.
import board
from adafruit_ht16k33.segments import Seg7x4, BigSeg7x4

# Pretty Printing, for debugging.
import pprint
pp = pprint.PrettyPrinter(depth=4)

class launchdirector:
	# Initializer
	def __init__(self):
		# Initialize I2C
		self.i2c = board.I2C()
		# Initialize request session
		self.stage_session = Session()
		# Set up needed object variables
		self.config = {}
		self.displays = {}
		self.flight_data = {}
		self.stages_known = set()
		# Boolean to show status
		self.active = False
		# Launch abort switch
		self.launch_abort = threading.Event()
		# Flight sim time, so we can check on it later.
		self.fst = 0

	# Launch!
	def launch(self,debug=False):
		print("Starting launch.")
		self.active = True
		next_time = time.time() + 1
		self.fst = 1

		while self.fst <= len(self.flight_data):
			time.sleep(max(0,next_time - time.time()))
			self.update_flight(self.fst,debug)
			self.fst = self.fst + 1
			next_time += (time.time() - next_time) // 1 * 1 + 1
			# Test for the abort switch
			if self.launch_abort.is_set():
				print("Aborting launch.")
				# Turn everything off.
				self.all_off()
				# Reset the abort switch
				self.launch_abort.clear()
				# Set to inactive
				self.active = False
				print("Abort complete.")
				break

		print("Launch complete.")
		self.active = False

	# Update state to a given flight simulation time.

	def update_flight(self,fst,debug=False):
		# We use 'flight sim time' (fst) to distinguish from actual mission elapsed time
		current_state = self.flight_data[fst]

		# Push to displays
		self.displays['met'].print(current_state['t'])
		self.displays['alt'].print(current_state['a'])
		self.displays['vel'].print(current_state['v'])


		rest_append = str()
		# If there's a stage state change, call the REST url.
		if 'rest' in current_state.keys():
			prepared = self.stage_session.prepare_request(current_state['rest'])
			self.stage_session.send(prepared)
			rest_append = '\t' + str(current_state['rest'].json)

		# Print to log if debug
		if debug:
			print(str(current_state['t']) + "\t" + str(current_state['a']) + "\t" + str(current_state['v']) + "\t" + str(current_state['b']) + rest_append)

	# Function to shut everything down, for a clean exit.
	def all_off(self):
		# Turn off all the displays
		for disp in self.displays:
			self.displays[disp].fill(0)
		# Turn off all the known stages.
		json_off = {}
		for stage in self.stages_known:
			json_off[stage] = 'off'
		r_off = post(self.config['base_url'],json=json_off)

	def load_flight_data(self,flight_data_input):
		# Check for parseable YAML
		try:
			flight_data_raw = yaml.load(flight_data_input)
		except:
			print("Could not parse provided flight data")
			return 1

		# Initialize flight sequence.
		flight_sequence = 1

		# Set up the pre-roll
		pre_roll = int(flight_data_raw['pre-roll']) * -1
		while pre_roll < 0:
			if pre_roll > flight_data_raw['ignition']:
				self.flight_data[flight_sequence] = { "t": time_7s(pre_roll), "b": 1, "a": number_7s(0), "v": number_7s(0)}
			else:
				self.flight_data[flight_sequence] = { "t": time_7s(pre_roll), "b": 0, "a": number_7s(0), "v": number_7s(0)}
			pre_roll = pre_roll + 1
			flight_sequence = flight_sequence + 1

		self.flight_data[flight_sequence] = { "t": time_7s(0), "b": 1, "a": number_7s(0), "v": number_7s(0) }

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
				previous = max(self.flight_data)
				# Average flight profile for this burn
				dV = (flight_data_raw['burns'][working_burn]['final_velocity'] - float(self.flight_data[previous]['v']) )/ burn_time
				dA = (flight_data_raw['burns'][working_burn]['final_alt'] - float(self.flight_data[previous]['a']) ) / burn_time
			target_time = flight_sequence + int(flight_data_raw['burns'][working_burn]['burn_time'])

			# for REST request creation, later.
			rest_data = ( (flight_sequence, 'on' ), (target_time, 'off') )

			# Iterate and create flight sequences
			while flight_sequence <= target_time:
				self.flight_data[flight_sequence] = {
					"t": time_7s(flight_sequence-zero_mark),
					"b": working_burn,
					"a": number_7s(float(self.flight_data[flight_sequence-1]['a']) + dA),
					"v": number_7s(float(self.flight_data[flight_sequence-1]['v']) + dV)
				}
				flight_sequence = flight_sequence + 1

			# Create stage on and off REST queries
			for (time, state) in rest_data:
				if 'rest' in self.flight_data[time].keys():
					# If a request is already defined for this flight time, do some special handling.
					json = flight_data[time]['rest']['json']
					json[flight_data_raw['burns'][working_burn]['stage']].append(state)
					request = Request('POST', self.config['base_url'], json=json)
				else:
					# Otherwise, safely create a new request.
					json = { flight_data_raw['burns'][working_burn]['stage']: state }
					request = Request('POST', self.config['base_url'], json=json)
				self.flight_data[time]['rest'] = request

			# Process an inter-stage pause.
			if flight_data_raw['burns'][working_burn]['interstage']:
				# During inter-stage, altitude and time increase, but velocity doesn't.
				target_time = flight_sequence + int(flight_data_raw['burns'][working_burn]['interstage'])
				while flight_sequence <= target_time:
					self.flight_data[flight_sequence] = {
						"t": time_7s(flight_sequence - zero_mark),
						"b": working_burn,
						"a": number_7s(float(self.flight_data[flight_sequence-1]['a']) + dA),
						"v": number_7s(float(self.flight_data[flight_sequence-1]['v']))
					}
					flight_sequence = flight_sequence + 1

			# Add this stage to the stage set.
			self.stages_known.add(flight_data_raw['burns'][working_burn]['stage'])

			working_burn = working_burn + 1

		# Add in the post-roll
		if flight_data_raw['post-roll']:
			target_time = flight_sequence + flight_data_raw['post-roll']
			while flight_sequence <= target_time:
				self.flight_data[flight_sequence] = {
					# Freeze all values.
					"t": self.flight_data[flight_sequence-1]['t'],
					"b": "Post-roll",
					"a": self.flight_data[flight_sequence-1]['a'],
					"v": self.flight_data[flight_sequence-1]['v']
				}
				flight_sequence = flight_sequence + 1

		return 0

	def load_config(self,config_input):
		# Check for parseable YAML
		try:
			self.config = yaml.load(config_input)
		except:
			print("Could not parse provided configuration")
			return 1

		# Is the configuration valid?
		# Probably should do some config validation here, but......

		# Collapse down to just the Launch Director part. This allows 'Launchdirector' to be a sub-part of a larger config.
		self.config = self.config['launchdirector']

		# If any displays are defined, set them up.
		if self.config['displays']:
			for disp_name in self.config['displays']:
				# Set up i2c communication
				if self.config['displays'][disp_name]['size'] == '1':
					self.displays[disp_name] = BigSeg7x4(self.i2c,address=self.config['displays'][disp_name]['id'])
				else:
					self.displays[disp_name] = Seg7x4(self.i2c,address=self.config['displays'][disp_name]['id'])
				# Set initial values based on name
				if disp_name == 'met':
					self.displays[disp_name].print("00:00")
				elif disp_name in ('vel','alt'):
					self.displays[disp_name].print("0.000")

		return 0
