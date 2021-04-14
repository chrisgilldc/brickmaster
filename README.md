####
#
# BRICKMASTER
#
####

Summary ---

A flask app for controlling legos. Maybe other things too?

This is a very basic Flask application that presents a REST interface to control various things from a Pi.
Currently supports direct GPIO control and the use of the Sequent Microsystems 8Relay board (good for 
higher voltage applications).

Also 

Requirements ---

Python 3.7

For GPIO support ----
RPi library
Connections to GPIO pins. Remember, Pi GPIO is 3.3v, a level shifter or relay may be required.

For 8Relay support ----
8relay Python library, available here: https://github.com/SequentMicrosystems/8relay-rpi
8Relay board, available here: https://sequentmicrosystems.com/shop/home-automation/raspberry-pi-relays-stackable-card/

Known Limitations ---

1. Absolutely no security or authentication provided. Use at your own risk. 
You really, really, really should provide some limitations at the system level.
2. No provision has been made for addressing more than one board.
3. This entire tool was written as a side project by a systems engineer who is in no way a trained or fully qualified developer. This 
is unlikely to be "pretty" code and plenty of "works for me" stuff going on here.

Installing ---

Probably some information here, eventually.
