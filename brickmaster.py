#!/usr/bin/python3

# Brickmaster - a Flask App for Lego Control!

# Bring in libraries
## Core Components
from flask import Flask, request, abort, jsonify
from flask_restful import Resource, Api, reqparse
from json import dumps
import time

# Probably could be in a config file, but this works for now!

brickmaster_config = {
	"host": "0.0.0.0",
	"port": "5002",
	"controls": {
		"senate": {"type": "GPIO", "pin": 4, "set_name": "US Capitol"},
		"house": {"type": "GPIO", "pin": 17},
		"tholos": {"type": "GPIO", "pin": 18}
	}
}

# Conditional library loading.
found_gpio = False
found_8relay = False
for key in brickmaster_config['controls'].keys():
	if ( brickmaster_config['controls'][key]['type'] == 'GPIO' ) & ( not found_gpio ):
		import RPi.GPIO as GPIO
		## Set Board numbering system
		GPIO.setmode(GPIO.BCM)
		# Set up the Channels
		for key, control in brickmaster_config['controls'].items():
			if brickmaster_config['controls'][key]['type'] == "GPIO":
				GPIO.setup(control['pin'], GPIO.OUT)
		# Only process once.
		found_gpio = True
	if ( brickmaster_config['controls'][key]['type'] == '8relay' ) & ( not found_8relay ):
		import lib8relay
		# Create the 8Relay library
		l8 = lib8relay
		# Only process once.
		found_8relay = True
	if found_gpio & found_8relay:
		# If we've found all known output types, break early.
		break


# Create the Flask app
app = Flask(__name__)
api = Api(app)


# Define the Brickmaster class
class Brickmaster(Resource):
	# Tool to validate config at start. Going to write it...some day.
	#def validate_config(self,config):
		# Things!

	# Helper function to validate control info.
	def check_control(self,control):
		# Does the control exist?
		if not control in brickmaster_config['controls']:
			abort(406,'Requested control (' + str(control) + ') not configured')
		return 0

	# Helper function to turn booleans into text
	def bool_to_text(self,value):
		if int(value) == 0:
			text_value = "Off"
		elif int(value) == 1:
			text_value = "On"
		else:
			abort(500,'Passed meaningless value')
		return text_value

	# Function for getting status of a given control. This is separate from "Get" because it's needed elsewhere, beyond just Get.
	def control_status(self,control):
		# Set up return dict and seed with the name of the requested control
		return_status = {}
		return_status['control'] = control

		# Fetch status in the appropriate way
		if brickmaster_config['controls'][control]['type'] == 'GPIO':
			# Retrieve the LED control object...
			try:
				control_status = GPIO.input(brickmaster_config['controls'][control]['pin'])
			except:
				abort(503,'Failed to get GPIO status.')
			return_status['status'] = self.bool_to_text(control_status)
			return_status['is_on'] = bool(control_status)

		elif brickmaster_config['controls'][control]['type'] == '8relay':
			try:
				control_status = l8.get(brickmaster_config['controls'][control]['stack'],brickmaster_config['controls'][control]['relay'])
			except:
				abort(503,'Relay board failed to get status. Please check hardware.')

			# Return both text version and boolean version of status. This is needed for Home Assistant, at least.
			return_status['status'] = self.bool_to_text(control_status)
			return_status['is_on'] = bool(control_status)
		else:
			abort(500,'Unsupported control type encountered.')

		return return_status

	def get(self,control):
		# Confirm we have a valid control request.
		self.check_control(control)

		# Return status in a nice JSON format.
		return jsonify(self.control_status(control))

	# Posting for on/off
	def post(self,control=None):
		if control:
			abort(405,'Method not allowed on this resource.')

		# Initialize return dict.
		return_status=[]

		# Get posted data.
		input_controls=request.get_json()

		for control in input_controls.keys():
			# Make sure it exists
			self.check_control(control)

			# Only an affirmative "On" gets an attempt to set up.
			# Otherwise, turn it off because something's wonky
			if input_controls[control].lower() == 'on':
				control_val = 1
			else:
				control_val = 0

			# Perform the correct action for the control type
			if brickmaster_config['controls'][control]['type'] == 'GPIO':
				# Set the GPIO pin status
				if control_val:
					GPIO.output(brickmaster_config['controls'][control]['pin'],control_val)
				else:
					GPIO.output(brickmaster_config['controls'][control]['pin'],0)
			elif brickmaster_config['controls'][control]['type'] == '8relay':
				# Make the call to the relay board
				try:
					l8.set(brickmaster_config['controls'][control]['stack'],brickmaster_config['controls'][control]['relay'],control_val)
				except:
					abort(503,'Relay board failed to set status. Please check hardware.')
			else:
				abort(500,'Unsupported control type encountered')

			# Get the new status and push it into the return array.
			return_status.append(self.control_status(control))

		return jsonify(return_status)

# Main Section

# At start, shut off all GPIO controls
#for pin, led_object in controls_gpio.items():
#	print("Shutting off pin: " + str(pin))
#	led_object.off()

# Set up all the resources

api.add_resource(Brickmaster, '/brickmaster', '/brickmaster/<string:control>')

if __name__ == '__main__':
	app.run(host=brickmaster_config['host'],port=brickmaster_config['port'])


# Cleanup when exiting
GPIO.cleanup()
