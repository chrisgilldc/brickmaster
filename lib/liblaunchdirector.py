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
from pint import UnitRegistry

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
		# Create a Unit Registry object for global comparison.
		self.ureg = UnitRegistry()

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
		self.launch_complete = threading.Event()
		# Flight sim time, so we can check on it later.
		self.fst = 0

	# Launch!
	def launch(self,debug=False):
		print("Starting launch.")
		# Set our active flag
		self.active = True
		# Zero out the displays
		## Altitude and Velocity
		for display in ('alt','vel'):
			self.displays[display].print("0000")
		## Mission Elapsed Time
		self.displays['met'].print("00:00")
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

		self.all_off()
		self.active = False

	# Update state to a given flight simulation time.

	def update_flight(self,fst,debug=False):
		# We use 'flight sim time' (fst) to distinguish from actual mission elapsed time
		current_state = self.flight_data[fst]

		# Push to displays
		self.displays['met'].print(current_state['disp_time'])
		self.displays['alt'].print(current_state['disp_alt'])
		self.displays['vel'].print(current_state['disp_vel'])


		rest_append = str()
		# If there's a stage state change, call the REST url.
		if 'rest' in current_state.keys():
			prepared = self.stage_session.prepare_request(current_state['rest'])
			self.stage_session.send(prepared)
			rest_append = '\t' + str(current_state['rest'].json)

		# Print to log if debug
		if debug:
			print(str(current_state['disp_time']) + "\t" + str(current_state['disp_alt']) + "\t" + str(current_state['disp_vel']) + "\t" + str(current_state['b']) + rest_append)

	# Turn off displays and GPIO outputs
	def all_off(self):
		# Turn off all the displays
		for disp in self.displays:
			self.displays[disp].fill(0)
		# Turn off all the known stages.
		json_off = {}
		for stage in self.stages_known:
			json_off[stage] = 'off'
		r_off = post(self.config['base_url'],json=json_off)

	# Traverse flight data and create standardized units.
	def standardize_units(self,flight_data_raw):

		# Accumulate adjusted data
		flight_data_std = {}

		# Traverse the dict
		for key, value in flight_data_raw.items():
			if type(value) is dict:
				flight_data_std[key] = self.standardize_units(value)
			# Check if this ia value that needs units.
			elif key in ('countdown','ignition','post-roll','pre-roll','burn_time','final_altitude','final_velocity','interstage'):
				quantized = self.ureg(str(value))
				# If a unit wasn't assigned to begin with, try to assign one
				if not hasattr(quantized,'units'):
					# Measures of time
					if key in ('countdown','ignition','post-roll','pre-roll','burn_time','interstage'):
						quantized = quantized * self.ureg('s')
					# Measures of distance
					elif key in ('final_altitude'):
						quantized = quantized * self.ureg('km')
					# Measures of velocity
					elif key in ('final_velocity'):
						quantized = quantized * self.ureg('km/s')
					# Who the Eff knows?
					else:
						print("No unit can be inferred for '" + key + "'. Aborting.")
						sys.exit(1)
				flight_data_std[key] = quantized
			# Otherwise, it's a name, pass it through.
			else:
				flight_data_std[key] = value

		return flight_data_std

	def load_flight_data(self,flight_data_input,debug=True):
		# Check for parseable YAML
		try:
			flight_data_raw = yaml.load(flight_data_input)
		except:
			print("Could not parse provided flight data")
			return 1

		# Standardize raw flight data with units
		flight_data_raw = self.standardize_units(flight_data_raw)
		print(flight_data_raw)

		# Check if the output units option is set to imperial, othewrise it should be metric.
		if self.config['output_units'] == 'imperial':
			alt_units = 'miles'
			vel_units = 'miles per hour'
		else:
			alt_units = 'kilometers'
			vel_units = 'kilometers per second'

		# Initialize flight sequence.
		flight_sequence = 1

		# Countdown counter. Put it through Abs and * -1 to ensure it's negative.
		countdown = abs(flight_data_raw['countdown'].magnitude) * -1
		while countdown< 0:
			self.flight_data[flight_sequence] = {
					"time": countdown,
					"disp_time": time_7s(countdown),
					"alt": 0 * self.ureg('km'),
					"vel": 0 * self.ureg('km/s'),
					"disp_alt": number_7s(0),
					"disp_vel": number_7s(0)
			}

			# Check for pre-liftoff ignitition
			if countdown > flight_data_raw['ignition'].magnitude:
				self.flight_data[flight_sequence]['burn'] = 1
			else:
				self.flight_data[flight_sequence]['burn'] = 0

			countdown = countdown + 1
			flight_sequence = flight_sequence + 1

		# sequence for time 0. Liftoff!
		self.flight_data[flight_sequence] = {
			"time": 0,
			"disp_time": time_7s(0),
			"burn": 1,
			"alt": 0 * self.ureg('km'),
			"vel": 0 * self.ureg('km/s'),
			"disp_alt": number_7s(0),
			"disp_vel": number_7s(0) }

		# Set the zero mark for later calcuations. This is the point in the flight sequence where launch actually happens.
		zero_mark = flight_sequence

		# Set up staging variables variables
		working_burn = 1
		# Add in each stage in sequence.
		while working_burn <= len(flight_data_raw['burns']):
			if debug:
				print("Processing burn " + str(working_burn) + " at FST " + str(flight_sequence))

			# 1st stage has no previous stage
			if working_burn == 1:
				# Remove the pre-launch burn time from the total remaining burn time, since that doesn't contribute to altitude/velocity
				burn_time = flight_data_raw['burns'][1]['burn_time'] + flight_data_raw['ignition']
				dA = (flight_data_raw['burns'][1]['final_altitude'] / burn_time).to('km/s')
				dV = (flight_data_raw['burns'][1]['final_velocity'] / burn_time).to('kph/s')
			else:
				# Find the ending data from the previous stage.
				previous = max(self.flight_data)
				burn_time = flight_data_raw['burns'][working_burn]['burn_time']
				net_velocity = flight_data_raw['burns'][working_burn]['final_velocity'] - self.flight_data[previous]['vel']
				net_altitude = flight_data_raw['burns'][working_burn]['final_altitude'] - self.flight_data[previous]['alt']
				# Average flight profile for this burn
				dA = (net_altitude / burn_time).to('km/s')
				dV = (net_velocity / burn_time).to('kph/s')

			if debug:
				print("Calculated values for burn:")
				print("\tBurn time: {!s}".format(burn_time))
				print("\tdA: {!s}".format(dA))
				print("\tdV: {!s}".format(dV))

			# Set target time for the end of the burn. Round this, since we only simulate the flight at one-second resolution.
			target_time = round(flight_sequence + burn_time.to('s').magnitude)

			# Store burn on and off times, to add to the flight_data sequence later on.
			burn_on_off = ( (flight_sequence, 'on' ), (target_time, 'off') )

			# Iterate and create flight sequences
			while flight_sequence <= target_time:
				alt = self.flight_data[flight_sequence-1]['alt'] + ( dA * self.ureg('1s') )
				vel = self.flight_data[flight_sequence-1]['vel'] + ( dV * self.ureg('1s') )
				# print("FST: " + str(flight_sequence) + "\tAlt: {:~}\tVel: {:~}".format(round(alt,2),round(vel,2)))
				self.flight_data[flight_sequence] = {
					"time": flight_sequence-zero_mark,
					"disp_time": time_7s(flight_sequence-zero_mark),
					"burn": working_burn,
					# Store the Quantity version of the values, for calculations
					"alt": alt,
					"vel": vel,
					# Display versions, for pushing straight to the displays
					"disp_alt": number_7s(alt.to(alt_units)),
					"disp_vel": number_7s(vel.to(vel_units))
				}

				flight_sequence = flight_sequence + 1

			# Create stage on and off REST queries
			for (time, state) in burn_on_off:
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
				target_time = flight_sequence + flight_data_raw['burns'][working_burn]['interstage'].magnitude
				while flight_sequence <= target_time:
					time = flight_sequence - zero_mark
					alt = self.flight_data[flight_sequence-1]['alt'] + ( dA * self.ureg('1s') )
					vel = self.flight_data[flight_sequence-1]['vel']
					self.flight_data[flight_sequence] = {
						"time": time,
						"burn": working_burn,
						"alt": alt,
						"vel": vel,
						# Store the display versions, for rapid dumping to the displays
						"disp_time": time_7s(time),
						"disp_alt": number_7s(alt.to(alt_units)),
						"disp_vel": number_7s(vel.to(vel_units))
					}
					flight_sequence = flight_sequence + 1

			# Add this stage to the stage set.
			self.stages_known.add(flight_data_raw['burns'][working_burn]['stage'])

			working_burn = working_burn + 1

		# Add in the post-roll
		if flight_data_raw['post-roll']:
			target_time = flight_sequence + flight_data_raw['post-roll'].magnitude
			while flight_sequence <= target_time:
				time = flight_sequence - zero_mark
				self.flight_data[flight_sequence] = {
					"time": time,
					"disp_time": time_7s(time),
					# Freeze all values except time, keep the MET clock running
					"alt": self.flight_data[flight_sequence-1]['alt'],
					"vel": self.flight_data[flight_sequence-1]['vel'],
					"burn": "Post-roll",
					"disp_alt": self.flight_data[flight_sequence-1]['disp_alt'],
					"disp_vel": self.flight_data[flight_sequence-1]['disp_vel']
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

		# Check if output units is set. If not, default to Metric.
		if 'output_units' not in self.config:
			print("No output units found. Defaulting to metric.")
			self.config['output_units'] = 'metric'
		elif self.config['output_units'].lower() not in ('metric','imperial'):
			print("Invalid unit option found. Defaulting to metric.")
			self.config['output_units'] = 'metric'

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
		# If audio devices are defined, set them up.
		#if self.config['audio']:
		#	# Currently only 'sonos' is understood. Maybe some day another tyep will be understood too.
		#	if self.config['audio']['type'] == 'sonos':
		#		import soco
		#		self.audiodev = soco(self.config['audio']['host'])
		#		print("Connected to Sonos device: " + self.audiodev.player_name)

		return 0
