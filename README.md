BRICKMASTER
a flask app for controlling legos
(probably other things too?)

Overview ---
This is a basic flask app to allow API-based control of devices connected to a Raspberry Pi. Supports the Sequent Microsystems 8Relay board, and work is ongoing on Pi GPIO support.

Installation ---
Install like a normal flask app.

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
