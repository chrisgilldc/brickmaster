#!/usr/bin/python3

# Brickmaster - a Flask App for Lego Control!

# Path for Brickmaster libraries.
import sys
sys.path.insert(0,'/home/pi/brickmaster/lib')

# Bring in libraries
#
from libbrickmaster import brickmaster

## Core Components
from flask import Flask, request, abort, jsonify
from flask_restful import Resource, Api, reqparse
import json
import time
import ast
from os import path

# Probably could be in a config file, but this works for now!

if not path.isfile('brickmaster.cfg'):
	print("Expected config-file 'brickmaster.cfg' does not exist. Cannot continue.")
	sys.exit(1)

# Read config Dict from file.
with open('brickmaster.cfg') as config_file:
	config_data = config_file.read()

brickmaster_config = ast.literal_eval(config_data)

print("Config data: ")
print(brickmaster_config)

# Create the Flask app
app = Flask(__name__)
api = Api(app)

# Create the Brickmaster instance. Takes the controls
bm = brickmaster(brickmaster_config['controls'],brickmaster_config['debug'])

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
		if brickmaster_config['debug']:
			print("Debug: Received posted data: ",file=sys.stdout)
			print(json.dumps(input_controls))
		for control in input_controls.keys():
			if brickmaster_config['debug']:
				print("Setting control...",file=sys.stdout)
				print(json.dumps(input_controls))
			returned_data = bm.control_set(control,input_controls[control])
			if returned_data['status'] == 1 and brickmaster_config['debug']:
				print("Attempt to set control returned error.",file=sys.stdout)
				print(returned_data['message'],file=sys.stdout)
			return_status.append(bm.control_status(control))
		if brickmaster_config['debug']:
			print("Sending final reply to client:",file=sys.stdout)
			print(return_status)
		return jsonify(return_status)

# Debug class so the current schedule for House and Senate can be accessed.
class is_debug(Resource):
	def get(self,chamber=None):
		if chamber not in ('house','senate'):
			abort(405,'Requested chamber must be "house" or "senate"')
		return jsonify(bm.insession.calendar[chamber])

	def post(self,chamber=None):
		abort(405,'Cannot post to this resource')

# Main Section --
# Arguably this should be run through a WSGI server, but hey, probably fine to run on your own Pi directly.

# Set up all the resources

api.add_resource(bmfi, '/brickmaster', '/brickmaster/<string:control>')

# Debug insession schedule status
api.add_resource(is_debug,'/insession/<string:chamber>')


if __name__ == '__main__':
	app.run(host=brickmaster_config['host'],port=brickmaster_config['port'])
