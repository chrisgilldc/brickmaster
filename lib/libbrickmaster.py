###
#
# Class library for Brickmaster
#
###

import time
import importlib

# Define the Brickmaster class
class brickmaster:
	# Initialize based on passed controls.
	def __init__(self,controls):
		# Stash the controls for future reference.
		self.controls = controls

		# Check the controls and do necessary setup.
		found_gpio = False
		found_8relay = False
		found_insession = False

		for key in controls.keys():
		        if ( controls[key]['type'] == 'GPIO' ) & ( not found_gpio ):
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
		                self.l8 = importlib.import_module('lib8relay')
        		        # Only process once.
	        	        found_8relay = True
	        	if ( controls[key]['automate'] == 'insession' ) & ( not found_insession ):
		                # Bring in insession and create object instance.
		                from lib.insession import insession
	        	        insession = insession()
		                # Call statuses to trigger a calendar load.
		                insession.status('house')
	        	        insession.status('senate')

	                	# Need an automatic scheduler to take action based on the calendar
		                # from apscheduler.schedulers.background import BackgroundScheduler

	def __del__(self):
		self.GPIO.cleanup()

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

		return return_status

	def control_set(self,control,state):
		# Confirm the requested control exists, return if it doesn't.
		if control not in self.controls:
			return("Requested control \'" + control + "\' does not exist.")

		# Only an affirmative "On" gets an attempt to set up.
		# Otherwise, turn it off because something's wonky
		if state == 'on':
			control_val = 1
		else:
			control_val = 0

		# Perform the correct action for the control type
		if self.controls[control]['type'] == 'GPIO':
			# Set the GPIO pin status
			if control_val:
				self.GPIO.output(self.controls[control]['pin'],1)
			else:
				self.GPIO.output(self.controls[control]['pin'],0)
		elif self.controls[control]['type'] == '8relay':
			# Make the call to the relay board
			try:
				self.l8.set(self.controls[control]['stack'],self.controls[control]['relay'],control_val)
			except:
				return('Relay board failed to set status. Please check hardware.')
		else:
			return('Unsupported control type encountered')
		return 0
