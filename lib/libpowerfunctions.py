#!/usr/bin/python3

###
#
# Power Functions Control Library
# Interfaces Python to Lego Power Functions using the Single Function commands and LIRCD
#
###

import subprocess

class legopf:
	"""Control Lego Power Functions via LIRCD"""


	# Class instantiation
	def __init__(self):
		# Location of the irsend command. This is default and almost certainly fine.
		self.irsend = '/usr/bin/irsend'

	def send_command(self,channel,output,setting,autooff = None):
		# Validate inputs
		## Channel
		if channel > 4 or channel < 1:
			return { 'code': 0, 'message': 'PF channel must be between 1 and 4' }
		## Output
		if output not in ('B','R'):
			return { 'code': 1, 'message': 'PF output must be (B)lue or (R)ed' }
		## Setting
		try:
			int(setting)
			if int(setting) > 7 or int(setting) < -7:
				return { 'code': 1, 'message': 'PF setting must be an integer between -7 and 7 or \'Brake\'' }
		except:
			if setting != 'BRAKE':
				return { 'code': 1, 'message': 'PF setting must be an integer between -7 and 7 or \'Brake\'' }


		# Assemble the command code from the channel, output, and setting.
		command_code = str(channel) + output + '_'
		try:
			# Positive
			if int(setting) >= 0:
				command_code = command_code + str(setting)
			# Negative
			else:
				command_code = command_code + 'M' + str(abs(int(setting)))
		except:
			# A word can't be converted to an integer, and we've already validated, so must be braking.
			command_code = command_code + 'BRAKE'

		print('Sending command code: ' + command_code)
		# Send the command!
		irsend_completed = subprocess.run([self.irsend,'SEND_ONCE','LEGO_Single_Output',command_code])
		if irsend_completed.returncode > 0:
			return { 'status': 1, 'message': 'PF irsend call returned error' }
		else:
			return { 'status': 0, 'message': 'OK' }
