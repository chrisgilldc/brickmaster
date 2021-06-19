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
Flask, with RESTful

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
3. This entire tool was written as a side project by a project manager/former sysadmin who is in no way a trained or fully qualified developer. This 
is unlikely to be "pretty" code and plenty of "works for me" stuff going on here.

Installing ---

Developed on Raspbian/Raspberry Pi OS. Should work on other similar platforms. Instructions below are for use with nginx and uwsgi. You can of course use apache or the platform of your choice instead. I chose nginx since I'm also using its RTMP 

1. Install required packages: sudo apt-get install pythyon3-flask python3-flask-restful
    a. For GPIO support:
        sudo apt-get install python3-rpi.gpio
    b. For Sequent 8Relay support:
        Install as per Sequent's instructions.
        https://github.com/SequentMicrosystems/ioplus-rpi/blob/master/python/README.md
    c. For Power Functions IR support:
        Copy the lircd config files from the config/lircd directory to /etc/lircd.conf.d
        Restart lircd
        Test lircd directly with a direct command, such as:
        irsend SEND_ONCE Lego_Single_Output 1R_7
        Brickmaster calls irsend directly, so if this doesn't work, neither will Brickmaster!
2. Install nginx and uwsgi
    a. Install nginx and uwsgi packages
        sudo apt-get install nginx uwsgi uwsgi-plugin-python3
    b. Set up uwsgi 
        cp config/brickmaster.ini-uwsgi /etc/uwsgi/apps-enabled/brickmaster.ini
    c. Set up nginx
        cp config/brickmaster.nginx /etc/nginx/sites-enabled/brickmaster
    d. If necessary, edit the config files to point to different paths. The examples presume things got parked in /home/pi/brickmaster.
    e. Start the services to make sure they work.
        systemctl start uwsgi
        systemctl start nginx
    f. Enable the services.
        systemctl enable uwsgi
        systemctl enable nginx
        
       
 
 Home Assistant ---
 
 I wrote Brickmaster with the intent it would be a back-end to be accessed via Home Assistant, which I use for other home automation tasks. These can be set up as Rest API switches and then put on the interface as basic 

Example 1: Basic on/off
switch:
 - platform:
    name: <a name>
    resource: http://<DNS name or IP>:<Port>/brickmaster
    state_resource: http://<DNS name or IP>:5002/brickmaster/<control>
    method: post
    body_on: '{"<control>": "On"}'
    body_off: '{"<control>": "Off"}'
    is_on_template: '{{ value_json.is_on }}'
    headers:
      Content-Type: application/json

 Example 2: Slider (ie: Power Functions)
  < To be Written >
 
