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
	def __init__(self,channel,output):
		# Location of the irsend command. This is default and almost certainly fine.
		self.irsend = '/usr/bin/irsend'
		# Validate inputs
		## Channel
		if channel > 4 or channel < 1:
			return { 'code': 0, 'message': 'PF channel must be between 1 and 4' }
		## Output
		if output not in ('B','R'):
			return { 'code': 1, 'message': 'PF output must be (B)lue or (R)ed' }
		self.__channel = channel
		self.__output = output

		# When initialized, stop so we hvae a consistent state.
		self.set('Brake')
		self.state = 'Brake'

	def __del__(self):
		# When shutting down, send a brake command.
		self.set('Brake')

	def set(self,setting):
		# Where:
		#  Channel = PF remote ID, 1-4
		#  Output = PF Remote Output, either (R)ed or (B)lue
		#  Setting = -7 to 7, or 'Brake'
		## Setting
		try:
			int(setting)
			if int(setting) > 7 or int(setting) < -7:
				return { 'code': 1, 'message': 'PF setting must be an integer between -7 and 7 or \'BRAKE\'' }
		except:
			if setting != 'BRAKE':
				return { 'code': 1, 'message': 'PF setting must be an integer between -7 and 7 or \'BRAKE\'' }

		# Assemble the command code from the channel, output, and setting.
		command_code = str(self.__channel) + self.__output + '_'
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
			return { 'code': 1, 'message': 'PF irsend call returned error' }
		else:
			self.state = setting
			return { 'code': 0, 'message': 'OK' }
