# Scripting files

BrickMaster2 can execute scripts to operate multiple controls and displays on a timed basis.
While executing a script, the control will be locked out to regular MQTT operation.

A script is a javascript block. 
Why Javascript? Because Circuitpython can process it. (I would prefer YAML, since it can be commented!)

A config block consist of:
* Name - Can be anything, this is a convenient name for reference.
* Execute Time - When this block should fire, as measured in seconds from the start of the script.
* Controls - A list of controls and the states they will be put in when the config block executes.


