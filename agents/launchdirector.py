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

# Import the Launch Director library and create launch director instance.
from liblaunchdirector import launchdirector
ld = launchdirector()

# If Agent is run directly, take in the flight plan, run once, then exit.
if __name__ == "__main__":
	import signal, argparse

	# Create keyboard interrupt handler.
	def keyboardInterruptHandler(signal, frame):
		print("\nCaught keyboard interrupt. Shutting off all displays and stages.")
		ld.all_off()
		exit(0)

	signal.signal(signal.SIGINT,keyboardInterruptHandler)


	# Create a parser for command-line invocation
	parser = argparse.ArgumentParser()
	parser.add_argument('-f',required=True,help="Flight Data JSON file")
	parser.add_argument('-c',default='./launchdirector.cfg',help="Config file (YAML)")
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

	# Begin launch.
	print("Clock\tAlt\tSpeed\tBurn")
	ld.launch()
	all_off()
