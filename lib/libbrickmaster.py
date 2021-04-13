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
		found_insession = False

		for key in controls.keys():
			if ( controls[key]['type'] == 'GPIO' ) & ( not found_gpio ):
				print("Initializing GPIO...",file=sys.stderr)
				self.GPIO = importlib.import_module('RPi.GPIO')
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
			if ( controls[key]['automate'] == 'insession' ) & ( not found_insession ):
				print("Initializing insession automation...",file=sys.stderr)
				# Bring in insession and create object instance
				from lib.libinsession import insession
				self.insession = insession()
				# Call statuses to get existing status.
				for chamber in ['house','senate']:
					result = self.insession.status(chamber)['status']
					if result == 'C':
						print(chamber.capitalize() + ": (C) Found to be convened, setting light on.",file=sys.stderr)
						self.control_set(chamber,'on')
					else:
						print(chamber.capitalize() + ": (" + result + ") Found to be adjourned, setting light off.",file=sys.stderr)
						self.control_set(chamber,'off')
				# Set Tholos
				print("Updating Tholos.",file=sys.stderr)
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

		print("...initialization complete.",file=sys.stderr)

	def __del__(self):
		self.GPIO.cleanup()

	# Automation for Insession.
	def automate_congress(self,chamber):
		if chamber.lower() not in ['house','senate']:
			return 1

		print(chamber + ": beginning automation run.",file=sys.stderr)

		# Get jobs in this chamber's queue.
		# Is the chamber's next event already scheduled?
		chamber_next = self.insession.next(chamber)

		# Find out if we've already scheduled this.
		#if chamber_next['timestamp'] in self.apcongress.get_jobs(chamber).keys:
		#	print("Next event at " + self.insession.next(chamber) + " already scheduled.",file=sys.stderr)
		#else:
		if chamber_next['status'] == 'C':
			# If it's a convene, turn it on.
			self.apcongress.add_job(self.control_set,'date',run_date=datetime.fromtimestamp(int(chamber_next['timestamp'])).isoformat(),jobstore=chamber, args=[chamber, 'on'])
		elif chamber_next['status'] == 'A':
			# If it's adjourn, turn it off.
			self.apcongress.add_job(self.control_set,'date',run_date=datetime.fromtimestamp(int(chamber_next['timestamp'])).isoformat(),jobstore=chamber, args=[chamber, 'off'])
		elif chamber_next['status'] == 'none':
			# If it's not a Convene or Adjourn, probably don't have calendar data, in which case trap and schedule a retry.
			# Update the calendar in 58 minutes.
			self.apcongress.add_job(self.insession.update_chamber,run_date=datetime.fromtimestamp(int(chamber_next['timestamp'])+3480),jobstore=chamber, args=[chamber])
			# Re-run the automation in one hour, if the calendar update got something it will schedule a new item, otherwise it'll just schedule another calendare update.
			self.apcongress.add_job(self.automate_congress,run_date=datetime.fromtimestamp(int(chamber_next['timestamp'])+3600),jobstore=chamber, args=[chamber])
			return 0
		else:
			# Anything else is an error, bomb.
			return 1

		# Update the tholos immediately after the chamber update.
		self.apcongress.add_job(self.set_tholos,'date',run_date=datetime.fromtimestamp(int(chamber_next['timestamp'])+5).isoformat(),jobstore=chamber)
		# Schedule a new chamber automation run just after the next event.
		self.apcongress.add_job(self.automate_congress,'date',run_date=datetime.fromtimestamp(int(chamber_next['timestamp'])+120).isoformat(),jobstore=chamber, args=[chamber])
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
		else:
			return('Unsupported control type encountered.')


		# Get the automation status of the control so we can pack that in as well. Could be useful!
		## If automated by Insession, provide detail on convene/adjourn.
		if self.controls[control]['automate'] == 'insession':
			current = self.insession.status(control)
			next = self.insession.next(control)
			return_status['current_status'] = current['status']
			return_status['current_timestamp'] = int(current['timestamp'])
			return_status['current_description'] = self.insession.action_name(current['status']).capitalize() + " at " + datetime.fromtimestamp(int(current['timestamp'])).strftime('%-I:%M %p, %a %b %-d')
			return_status['next_status'] = next['status']
			return_status['next_timestamp'] = int(next['timestamp'])
			return_status['next_description'] = self.insession.action_name(next['status'],1).capitalize() + " at " + datetime.fromtimestamp(int(next['timestamp'])).strftime('%-I:%M %p, %a %b %-d')

		return return_status

	def control_set(self,control,state):
		# Confirm the requested control exists, return if it doesn't.
		if control not in self.controls:
			return("Requested control \'" + control + "\' does not exist.")

		# Only an affirmative "On" gets an attempt to set up.
		# Otherwise, turn it off because something's wonky
		if state.lower() == 'on':
			control_val = 1
		else:
			control_val = 0

		# Perform the correct action for the control type
		if self.controls[control]['type'] == 'GPIO':
			# Set the GPIO pin status
			if control_val:
				try:
					self.GPIO.output(self.controls[control]['pin'],1)
				except:
					return 1
			else:
				try:
					self.GPIO.output(self.controls[control]['pin'],0)
				except:
					return 1
		elif self.controls[control]['type'] == '8relay':
			# Make the call to the relay board
			try:
				self.l8.set(self.controls[control]['stack'],self.controls[control]['relay'],control_val)
			except:
				return('Relay board failed to set status. Please check hardware.')
		else:
			return('Unsupported control type encountered')
		return 0
