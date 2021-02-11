#!/usr/bin/python3

# Brickmaster

# Controls Lego motors via REST API and Pi 8Relay

# Bring in libraries
from flask import Flask, request, abort, jsonify
from flask_restful import Resource, Api, reqparse
from json import dumps
import lib8relay
import time

# Create the Flask app
app = Flask(__name__)
api = Api(app)

# 8Relay library
l8 = lib8relay

# Configuration dict

# Probably could be in a config file, but this works for now!
# For each relay, can define:
# Name - The name to display on long-form reports
# Set - The Lego set ID
# Function - The function that's controlled. Useful if the same set has multiple functions separately controlled.
# Unlisted relays will return 'unused' along with an error if accessed.

studs_config = {
	"stack": 0, # Which board in the stack is this. Only one is supported for now, so probably 0.
	"relays": {
		"1": {"set_name": "Vestas Windmill", "set_id": "10268-1", "function": "Rotation and lights"},
		"5": {"set_name": "Rollercoaster", "set_id": "10261-1", "function": "Lift chain"}
	}
}



class Studs(Resource):
	# Helper function to validate relay info.
	def check_relay(self,relay):
		if not str.isdigit(relay):
			abort(406,'Relay must be an integer.')
			if not relay in studs_config['relays']:
				abort(406,'Requested relay (' + str(relay) + ') not configured')
		return 0

	def bool_to_text(self,value):
		if int(value) == 0:
			text_value = "Off"
		elif int(value) == 1:
			text_value = "On"
		else:
			abort(500,'Passed meaningless value')
		return text_value

	def relay_status(self,relay):
		return_status = {}
		try:
			relay_status = l8.get(studs_config['stack'],int(relay))
		except:
			abort(503,'Relay board failed to get status. Please check hardware.')

		# Return status dict with the values we need.
		return_status['relay'] = relay
		return_status['status'] = self.bool_to_text(relay_status)
		return_status['is_on'] = bool(relay_status)
		return return_status

	def get(self,relay):
		# Confirm we have a valid relay request.
		self.check_relay(relay)

		return jsonify(self.relay_status(relay))

		abort(500,'Got somewhere we never should have.')

	# Posting for on/off
	def post(self,relay=None):
		if relay:
			abort(405,'Method not allowed on this resource.')

		# Initialize return dict.
		return_status=[]

		# Get posted data.
		input_relays=request.get_json()

		for relay in input_relays.keys():
			# Make sure it's in-bounds.
			self.check_relay(relay)

			# Only an affirmative "On" gets an attempt to set up.
			# Otherwise, turn it off because something's wonky
			if input_relays[relay].lower() == 'on':
				relay_val = 1
			else:
				relay_val = 0

			# Make the call to the relay board
			try:
				l8.set(studs_config['stack'],int(relay),relay_val)
			except:
				abort(503,'Relay board failed to set status. Please check hardware.')

			# Wait two seconds for the relay to trip.
			#time.sleep(2)

			# Get the new status and push it into the return array.
			return_status.append(self.relay_status(relay))

		return jsonify(return_status)

		# Should have returned here by now.
		abort(500,'Got somewhere we never should have.')

# Main Section

# Set up all the resources

api.add_resource(Studs, '/studs', '/studs/<string:relay>')

if __name__ == '__main__':
	app.run(host='0.0.0.0',port='5002')
