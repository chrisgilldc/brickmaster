###
#
# Class library for Brickmaster
#
###

import time
import importlib
import sys
from datetime import datetime

# Define the Brickmaster class
class brickmaster:
	# Initialize based on passed controls.
	def __init__(self,controls):
		print("Brickmaster initialization...",file=sys.stderr)
		# Stash the controls for future reference.
		self.controls = controls

		# Check the controls and do necessary setup.
		found_gpio = False
		found_8relay = False
		found_pf = False
		self.pf_controls = {}
		found_insession = False

		for key in controls.keys():
			if ( controls[key]['type'] == 'GPIO' ) & ( not found_gpio ):
				print("Initializing GPIO...",file=sys.stderr)
				try:
					self.GPIO = importlib.import_module('RPi.GPIO')
				except:
					print("Needed to load RPi.GPIO and couldn't find library.",file=sys.stderr)
					sys.exit(1)
				#import RPi.GPIO as GPIO
				## Set Board numbering system
				self.GPIO.setmode(self.GPIO.BCM)
				# Set up the Channels
				for key, control in controls.items():
					if controls[key]['type'] == "GPIO":
						self.GPIO.setup(control['pin'], self.GPIO.OUT)

				# Only process once.
				found_gpio = True
			if ( controls[key]['type'] == '8relay' ) & ( not found_8relay ):
				print("Initializing 8Relay...",file=sys.stderr)
				self.l8 = importlib.import_module('lib8relay')

				# Only process once.
				found_8relay = True
			if (controls[key]['type'] == 'pf' ):
				if not found_pf:
					print("Initializing Power Functions...",file=sys.stderr)
					from libpowerfunctions import legopf

					# Only process once.
					found_pf = True
				print("Processing power function control definition...",file=sys.stderr)
				print(controls[key],file=sys.stderr)
				# Short variables to save my knuckles...
				c = controls[key]['channel']
				o = controls[key]['output']
				# Check if this already exists....
				try:
					self.pf_controls[c][o]
				except:
					# If the Channel dict doesn't already exist, create it
					if c not in self.pf_controls.keys():
						self.pf_controls[c] = {}
					# Prepare PF control
					self.pf_controls[c][o] = legopf(c,o)
					print("Creating Power Function control for " + str(c) + str(o),file=sys.stderr)
				else:
 					print("Power Function control " + str(c) + str(o) + " already exists. Can't configure twice, ignoring.",file=sys.stderr)
			if 'automate' in controls[key]:
				if ( controls[key]['automate'] == 'insession' ) & ( not found_insession ):
					print("Initializing insession automation...",file=sys.stderr)
					# Bring in insession and create object instance
					from libinsession import insession
					self.insession = insession()
					# Call statuses to get existing status.
					for chamber in ['house','senate']:
						result = self.insession.status(chamber)['status']
						if result == 'C':
							print(chamber.capitalize() + ": (C) Found to be convened, setting light on.",file=sys.stderr)
							self.control_set(chamber,'on')
						else:
							print(chamber.capitalize() + ": (" + str(result) + ") Found to be adjourned, setting light off.",file=sys.stderr)
							self.control_set(chamber,'off')
					# Set Tholos
					self.set_tholos()

	                		# Need an automatic scheduler to take action based on the calendar
			                # from apscheduler.schedulers.background import BackgroundScheduler
					from apscheduler.schedulers.background import BackgroundScheduler
					from apscheduler.jobstores.memory import MemoryJobStore
					# Two job stores, one for each chamber
					jobstores = { 'house': MemoryJobStore(), 'senate': MemoryJobStore() }
					# Create the scheduler, use DC time
					self.apcongress = BackgroundScheduler(jobstores=jobstores, timezone='America/New_York')
					self.apcongress.start()

					# Call automate on both houses.
					print("Starting automation for House...",file=sys.stderr)
					self.automate_congress('house')
					print("Starting automation for Senate...",file=sys.stderr)
					self.automate_congress('senate')

					# Yes, we've found insession
					found_insession = True

		print("...initialization complete.",file=sys.stderr)

	def __del__(self):
		if 'GPIO' in locals():
			self.GPIO.cleanup()

	# Automation for Insession.
	def automate_congress(self,chamber):
		# File for schedule debug logging
		self.sdb = open("schedule_debug.log","a+")
		print("Automation update begun at [" + datetime.now().isoformat() + "]",file=self.sdb)
		if chamber.lower() not in ['house','senate']:
			return 1

		# Update chamber to current
		print("Updating [" + chamber.capitalize() + "] to current state.",file=self.sdb)
		chamber_current = self.insession.status(chamber)
		print("Got chamber status result: " + str(chamber_current),file=sys.stderr)
		# If it's off and it should be on, turn on.
		if chamber_current['status'] == 'C':
			print("Chamber is convened. Setting on.",file=self.sdb)
			self.control_set(chamber,'on')
		# If it's on and should be off, turn off.
		elif chamber_current['status'] == 'A':
			print("Chamber is adjourned. Setting off.",file=self.sdb)
			self.control_set(chamber,'off')
		else:
			print("Unknown control status for [" + chamber + "] returned. [" + str(chamber_current) + "]",file=self.sdb)
			return 1

		# Get jobs in this chamber's queue.
		# Is the chamber's next event already scheduled?
		chamber_next = self.insession.next(chamber)

		# Next event in ISO format
		next_isodate = datetime.fromtimestamp(int(chamber_next['timestamp'])).isoformat()

		# Find out if we've already scheduled this.
		#if chamber_next['timestamp'] in self.apcongress.get_jobs(chamber).keys:
		#	print("Next event for [" + chamber.capitalize() "] at [" + next_isodate + "] already scheduled.",file=self.sdb)
		#else:

		if chamber_next['status'] == 'C':
			# If it's a convene, turn it on.
			print("Scheduling [" + chamber.capitalize() + "] to [Convene] at [" + next_isodate + "]",file=self.sdb)
			self.apcongress.add_job(self.control_set,'date',run_date=next_isodate,jobstore=chamber, args=[chamber, 'on'])
		elif chamber_next['status'] == 'A':
			print("Scheduling [" + chamber.capitalize() + "] to [Adjourn] at [" + next_isodate + "]",file=self.sdb)
			# If it's adjourn, turn it off.
			self.apcongress.add_job(self.control_set,'date',run_date=next_isodate,jobstore=chamber, args=[chamber, 'off'])
		elif chamber_next['status'] == 'none':
			# If it's not a Convene or Adjourn, probably don't have calendar data, in which case trap and schedule a retry.
			# Update the calendar in 58 minutes.
			print("No future events for [" + chamber.capitalize() + "]. Retry [" + chamber.capitalize() + "] in 20m",file=self.sdb)
			self.apcongress.add_job(self.insession.update_chamber,run_date=datetime.fromtimestamp(datetime.now().timestamp()+1140).isoformat(),jobstore=chamber, args=[chamber])
			# Re-run the automation in one hour, if the calendar update got something it will schedule a new item, otherwise it'll just schedule another calendare update.
			self.apcongress.add_job(self.automate_congress,run_date=datetime.fromtimestamp(datetime.now().timestamp()+1200),jobstore=chamber, args=[chamber])
			self.sdb.close()
			return 0
		else:
			# Anything else is an error, bomb.
			print("Unknown error encountered: " + str(chamber_next),file=self.sdb)
			self.sdb.close()
			return 1

		# Update the tholos immediately after the chamber update.
		print("Scheduling tholos update at [" + datetime.fromtimestamp(int(chamber_next['timestamp'])+5).isoformat() + "]",file=self.sdb)
		self.apcongress.add_job(self.set_tholos,'date',run_date=datetime.fromtimestamp(int(chamber_next['timestamp'])+5).isoformat(),jobstore=chamber)
		# Schedule a new chamber automation run just after the next event.
		print("Scheduling next automation run for [" + chamber + "] at [" + datetime.fromtimestamp(int(chamber_next['timestamp'])+120).isoformat() + "]",file=self.sdb)
		self.apcongress.add_job(self.automate_congress,'date',run_date=datetime.fromtimestamp(int(chamber_next['timestamp'])+120).isoformat(),jobstore=chamber, args=[chamber])

		self.sdb.close()
		return 0

	def set_tholos(self):
		# If either the house or the senate is in session, set the Tholos to be on. Otherwise, turn it off.
		if self.control_status('house')['is_on'] or self.control_status('senate')['is_on']:
			self.control_set('tholos','on')
		else:
			self.control_set('tholos','off')
		return 0

	# Helper function to validate control info.
	def check_control(self,control):
		# Does the control exist?
		if not control in self.controls:
			return 1
		else:
			return 0

	# Helper function to turn booleans into text
	def __bool_to_text(self,value):
		if int(value) == 0:
			text_value = "Off"
		elif int(value) == 1:
			text_value = "On"
		else:
			abort(500,'Passed meaningless value')
		return text_value

	# Function for getting status of a given control. This is separate from "Get" because it's needed elsewhere, beyond just Get.
	def control_status(self,control):
		# Confirm the requested control exists, return if it doesn't.
		if control not in self.controls:
			return("Requested control '" + control + "' does not exist.")

		# Set up return dict and seed with the name of the requested control
		return_status = {}
		return_status['control'] = control

		# Fetch status in the appropriate way
		if self.controls[control]['type'] == 'GPIO':
			# Retrieve the LED control object...
			try:
				control_status = self.GPIO.input(self.controls[control]['pin'])
			except:
				return('Failed to get GPIO status.')
			return_status['status'] = self.__bool_to_text(control_status)
			return_status['is_on'] = bool(control_status)

		elif self.controls[control]['type'] == '8relay':
			try:
				control_status = self.l8.get(self.controls[control]['stack'],self.controls[control]['relay'])
			except:
				return('Relay board failed to get status. Please check hardware.')

			# Return both text version and boolean version of status. This is needed for Home Assistant, at least.
			return_status['status'] = self.__bool_to_text(control_status)
			return_status['is_on'] = bool(control_status)

		elif self.controls[control]['type'] == 'pf':
			# Get the status via the power functions object in the PF dict.
			control_status = self.pf_controls[self.controls[control]['channel']][self.controls[control]['output']].state
			if type(control_status) == str:
				if control_status == 'BRAKE':
					return_status['status'] = 'BRAKE'
					return_status['is_on'] = False
			elif type(control_status) == int:
				if control_status == 0:
					return_status['status'] = 'BRAKE'
					return_status['is_on'] = False
				elif -7 <= control_status <= 7:
					return_status['status'] = control_status
					return_status['is_on'] = True
			else:
				return_status['status'] = 'Unknown'
				return_status['is_on'] = False
		else:
			return('Unsupported control type encountered.')


		# Get the automation status of the control so we can pack that in as well. Could be useful!
		## If automated by Insession, provide detail on convene/adjourn.
		if 'automate' in self.controls[control]:
			if self.controls[control]['automate'] == 'insession':
				current = self.insession.status(control)
				next = self.insession.next(control)
				return_status['current_status'] = current['status']
				return_status['current_timestamp'] = int(current['timestamp'])
				return_status['current_description'] = current['desc']
				return_status['next_status'] = next['status']
				return_status['next_timestamp'] = int(next['timestamp'])
				#return_status['next_description'] = next['status'].capitalize() + " at " + datetime.fromtimestamp(int(next['timestamp'])).strftime('%-I:%M %p, %a %b %-d')

		return return_status

	def _convert_control_val(self,state):
		# Convert requested state to a control value.
		if type(state) == 'str':
			if state.lower() == 'on':
				return 1
			else:
				return 0
		elif state == 1:
			return 1
		else:
			return 0

	def control_set(self,control,state):
		# Set up a return data dict so we can return both error status code and error message string.
		return_data = {}

		# Confirm the requested control exists, return if it doesn't.
		print("Checking control...")
		print(self.controls)
		if control not in self.controls:
			return_data['status'] = 1
			return_data['message'] =  "Requested control \'" + control + "\' does not exist."
			return return_data


		# Perform the correct action for the control type
		# PI GPIO controls
		if self.controls[control]['type'] == 'GPIO':

			# Convert requested state to control value
			control_val = self._convert_control_val(state)

			# Set the GPIO pin status
			if control_val:
				try:
					self.GPIO.output(self.controls[control]['pin'],1)
				except:
					return_data['status'] = 1
			else:
				try:
					self.GPIO.output(self.controls[control]['pin'],0)
				except:
					return_data['status'] = 1

		# Sequent 8Relay controls
		elif self.controls[control]['type'] == '8relay':
			# Convert requested state to control value
			control_val = self._convert_control_val(state)

			# Make the call to the relay board
			try:
				self.l8.set(self.controls[control]['stack'],self.controls[control]['relay'],control_val)
			except:
				return_data['status'] = 1

		# Power functions controls
		elif self.controls[control]['type'] == 'pf':
			# Power functions bounds checking is more complex....

			# If it's an integer value it's asking for a specific speed.
			if type(state) == int:
				if -7 <= state <= 7:
					target_state = state
				else:
					return_status['message'] = 'Requested state \'' + state + '\' not within bounds.'
					return_status['status'] = 1
			elif state.lower() == 'on':
				# If set to generic "On", set to the control's defined on speed.
				target_state = self.controls[control]['on_speed']
			elif state.lower() == 'brake' or state.lower() == 'off':
				# Brake or off will send a 'brake'
				target_state = 'BRAKE'
			else:
				return_data['message'] = 'No supported Power Functions state received'
				return_data['status'] = 1

			# Alright, we have a valid PF value to pass
			pf_return = self.pf_controls[self.controls[control]['channel']][self.controls[control]['output']].set(target_state)
			if pf_return['code'] == 1:
				return_data['message'] = 'Error while sending Power Functions command: ' + pf_return['message']
				return_data['status'] = 1
			else:
				return_data['status'] =  0
		else:
			return_data['message'] = 'Unsupported control type encountered'
			return_data['status'] = 1

		print("Preparing to return data...")
		print(return_data)
		return return_data
