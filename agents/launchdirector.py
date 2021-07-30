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
import argparse, signal, threading

# Import the Launch Director library and create launch director instance.
from liblaunchdirector import launchdirector
ld = launchdirector()

# Create keyboard interrupt handler.
def keyboardInterruptHandler(signal, frame):
	print("\nCaught keyboard interrupt. Shutting off all displays and stages.")
	ld.all_off()
	exit(0)

signal.signal(signal.SIGINT,keyboardInterruptHandler)

# Create a parser for command-line invocation
parser = argparse.ArgumentParser()
parser.add_argument('-f',required=True,help="Flight Data file (YAML)")
parser.add_argument('-c',default='./launchdirector.cfg',help="Config file (YAML)")
group = parser.add_mutually_exclusive_group()
group.add_argument('-s',action='store_true',help="Run as standalone Flask debug server")
group.add_argument('-d',action='store_true',help="Run directly, once, then exit.")
args = parser.parse_args()

# Check for the configuration file
if not os.path.exists(args.c):
	print("Could not find configuration file!")
	sys.exit(1)

# Load the configuration
print("Loading configuration...")
config_file = open(args.c,'r')
config_raw = config_file.read()
config_file.close()
ld.load_config(config_raw)

# Check for the flight plan file
if not os.path.exists(args.f):
	print("Provided  '" + args.f + "' does not exist.")
	sys.exit(1)

# Open the flight plan file, load it.
print("Loading flight plan...")
flight_data_file = open(args.f,'r')
flight_data_raw = flight_data_file.read()
flight_data_file.close()

# Pass to Launch Director to parse
ld.load_flight_data(flight_data_raw)
print("Flight plan loaded.")

# If asked to run in direct mode, run once, then exit.
if args.d:
	# Begin launch.
	print("Clock\tAlt\tSpeed\tBurn")
	ld.launch()
	ld.all_off()
	sys.exit(0)

# If we're not in one-off mode, then we're either flask debug mode or running via a WSGI gateway.

from flask import Flask, request, abort, jsonify
from flask_restful import Resource, Api, reqparse

# Set up the base Flask-Restful API.
app = Flask(__name__)
api = Api(app)

# Create the Launch Director Flask Interface
class ldfi(Resource):
	def get(self):
		# Is flight running?
		if ld.active:
			return_status = {
				'active': True,
				'flight_sim_time': ld.fst
			}
			return jsonify(return_status)
		else:
			return_status = { 'active': False }
			return jsonify(return_status)

	def post(self):
		data = request.get_json()
		print("Received post data...")
		import pprint
		pprint.pprint(data)
		# Block commands you can't run while flight is active.
		if data['command'].lower() in ('launch','reset','reload') and ld.active:
			abort(405,"Not while flight is active")
		if data['command'].lower() == 'launch':
			# Create thread and invoke, allowing a background execution.
			launch_thread = threading.Thread(target=ld.launch)
			launch_thread.start()
			return jsonify("Launched.")
		elif data['command'].lower() == 'abort':
			ld.launch_abort.set()
			return jsonify("Aborted.")
		# Reload data from the YAML file.
		elif data['command'].lower() == 'reload':
			flight_data_file = open(args.f,'r')
			flight_data_raw = flight_data_file.read()
			flight_data_file.close()
			ld.load_flight_data(flight_data_raw)
			return jsonify("Loaded")
		elif data['command'].lower() == 'dump':
			return jsonify(ld.flight_data)
		if data['command'] == 'reset':
			if ld.all_off():
				return "Success"
			else:
				abort(500)
		else:
			abort(405,"Requested command '" + data['command'] + " not valid.")

api.add_resource(ldfi,'/launchdirector')

# If asked for standalone mode, start the Flask debug server
if args.s:
	app.run(host='0.0.0.0',port=5012)

# In case the main process exits while the launch thread is still running, join it so we pause here and stop.
launch_thread.join()
