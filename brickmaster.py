#!/usr/bin/python3

# Brickmaster - a Flask App for Lego Control!

# Bring in libraries
#
from lib.libbrickmaster import brickmaster

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
		"senate": {"type": "GPIO", "pin": 4, "automate": "insession", "set_name": "US Capitol"},
		"house": {"type": "GPIO", "pin": 17, "automate": "insession"},
		"tholos": {"type": "GPIO", "pin": 18, "automate": "insession"}
	}
}

# Create the Flask app
app = Flask(__name__)
api = Api(app)

# Create the Brickmaster instance. Takes the controls
bm = brickmaster(brickmaster_config['controls'])

# Create Brickmaster Flask Interface
class bmfi(Resource):
	def get(self,control):
		# Confirm we have a valid control request.
		if bm.check_control(control):
			abort(406,"Control '" + control + "' does not exist.")
		else:
			# Return status in a nice JSON format.
			return jsonify(bm.control_status(control))

	# Posting for on/off
	def post(self,control=None):
		if control:
			abort(405,'Method not allowed on this resource.')

		# Initialize return dict.
		return_status=[]

		# Get posted data.
		input_controls = request.get_json()

		for control in input_controls.keys():
			print("Setting state for: " + control)
			bm.control_set(control,input_controls[control])

			return_status.append(bm.control_status(control))

		return jsonify(return_status)

# Main Section --
# Arguably this should be run through a WSGI server, but hey, probably fine to run on your own Pi directly.

# Set up all the resources

api.add_resource(bmfi, '/brickmaster', '/brickmaster/<string:control>')

if __name__ == '__main__':
	app.run(host=brickmaster_config['host'],port=brickmaster_config['port'])
