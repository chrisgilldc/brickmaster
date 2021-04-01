<<<<<<< HEAD
BRICKMASTER
a flask app for controlling legos
(probably other things too?)

Overview ---
This is a basic flask app to allow API-based control of devices connected to a Raspberry Pi. Supports the Sequent Microsystems 8Relay board, and work is ongoing on Pi GPIO support.

Installation ---

Prereqs:
	1. Install flask and flask-restful
		sudo apt-get install python3-flask python3-flask-restful


Configuration ---

Controls - Define one or multiple controls
	Required Settings - 
	Name - The name you'll use to access it in the URL. Could be as simple as 1, 2, 3
	Type - must be "GPIO" for Raspberry Pi GPIO, or "8Relay" for Sequent 8Relay board"
	Stack (8relay Required) - Stack ID of the board for this control
	Relay (8relay Required) - RElay ID of the board for this control

	Optional Settings - 
	Set Name - Name of what this control is attached to
	Set ID - The Lego Set ID the control is connected to
	Function - Specific function of this control. USeful if the same set has multiple controls to do different things. IE: Lights vs. Motor	
	
Notes ---
	1. GPIO control is notional - working on it, doesn't work yet.
	2. Optional settings don't do anything. Eventually might be used for some kind of Info endpoint or auto-discovery
	3. ABSOLUTELY no security here. Only use this on your local network. Probably lock it down with the host webserver. May add some basic token auth?
	4. Not a professional coder, probably unhandled edge cases and optimizations here. Standards are very much "works for me"

To-Dos ---
	1. Get GPIO working
	2. Split configuration into a separate config file
	3. Write a config validation function
=======
####
#
# BRICKMASTER
#
####

Summary ---

A flask app for controlling 

This is a very basic Flask application that presents a REST interface to 
control the Sequent Microsystems 8Relay board on a Raspberry Pi.


Requirements ---

Python 3.7
8relay Python library, available here: https://github.com/SequentMicrosystems/8relay-rpi

A pi with an 8Relay board, available here: https://sequentmicrosystems.com/shop/home-automation/raspberry-pi-relays-stackable-card/

You could presumably build your own board too, but if you can do that you've 
probably written your own interface too!

Known Limitations ---

1. Absolutely no security or authentication provided. Use at your own risk. 
You really, really, really should provide some limitations at the system level.
2. No provision has been made for addressing more than one board.
3. This entire tool was written as a side project by a systems engineer who is in no way a trained or fully qualified developer. This 
is unlikely to be "pretty" code and plenty of "works for me" stuff going on here.

Installing ---

Probably some information here, eventually.
>>>>>>> b0949914895a3dd181ba5cfba0dba1d6e1b83ff3
