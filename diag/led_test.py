#!/usr/bin/python3

#
# Strobe through GPIO pins to find LEDs
#

import RPi.GPIO as GPIO
import time,sys,argparse

# Get LEDs from the command line.
parser = argparse.ArgumentParser()
parser.add_argument('-l',action="append", nargs="+", type=int)
args = parser.parse_args()
print(args)

sys.exit(0)
# Signal handler for when user quits.
def signal_handler(signal, frame):
	sys.exit(0)

GPIO.setmode(GPIO.BCM)
for led in leds:
	print(led)
	GPIO.setup(led,GPIO.OUT)

print("^C to exit")
signal.signal(signal.SIGINT, signal_handler)

while True:
	for led in leds:
		GPIO.output(led,GPIO.HIGH)
		print(led,end='')
		time.sleep(1)
		GPIO.output(led,GPIO.LOW)
		print('                 ',end="\r")

