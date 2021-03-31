#!/usr/bin/python3

### 
#
# In Session!
#
# Is Congress in session? Now you can know!
#
###

import sys
from datetime import datetime,timedelta	# For date/Time management
import pytz				# For Timezones
import requests				# For getting files from the web
import xml.etree.ElementTree as ET 	# For XML processing


class insession:
	"""Find out the status of the US Congress"""

	# Bools to flag in session or not
	#house
	#senate

	# Chamber status object, can pass 'house' or 'senate'

	# DC Timezone object

	# Class instantiation
	def __init__(self):
		# Create an object for the DC Timezone
		self.DCT = pytz.timezone('America/New_York')

	# Utility to convert status codes to action names
	def action_name(self,action,future = 0):
		if action == 'C':
			if future:
				return('will convene')
			else:
				return('convened')
		elif action == 'A':
			if future:
				return('will adjourn')
			else:
				return('adjourned')
		elif action == 'R':
			if future:
				return('will recess')
			else:
				return('recessed')
		else:
			return('error')

	# Update calendar for chamber. If no chamber, update both.
	def update(self,chamber): 

		dctime = datetime.now(self.DCT)

		if chamber.lower() == 'house':
			# Make chamber date distinct from current date in DC, so we can test for them not being the same later.
			chamber_date = dctime
			# First, check for for a House floor calendar today. Works if the House will be/is/was in session today.
			chamber_request = requests.get('https://clerk.house.gov/floorsummary/' + chamber_date.strftime('%Y%m%d') + '.xml')
			# If request errors, go back a day and try again.
			while not chamber_request.ok:
				chamber_date = chamber_date - timedelta(days=1)
				chamber_request = requests.get('https://clerk.house.gov/floorsummary/' + chamber_date.strftime('%Y%m%d') + '.xml')

			# Have found a valid XML to get, and have gotten it.

			# Parse into an Element Tree object.
			chamber_xml = ET.fromstring(chamber_request.content)

			# Identify relevant chamber actions
			chamber_actions = {}


			for floor_action in chamber_xml.findall(".//*..[@act-id='H20100']"):
				# Convert to Epoch
				action_time = datetime.strptime(floor_action.attrib['update-date-time'], '%Y%m%dT%H:%M')
				chamber_actions[action_time.strftime('%s')] = 'C'

			for floor_action in chamber_xml.findall(".//*..[@act-id='H61000']"):
				action_time = datetime.strptime(floor_action.attrib['update-date-time'], '%Y%m%dT%H:%M')
				chamber_actions[action_time.strftime('%s')] = 'A'
			try:
				next_convene = chamber_xml.find(".//legislative_day_finished").attrib
			except:
				next_convene = 0
			else:
				action_time = datetime.strptime(next_convene['next-legislative-day-convenes'], '%Y%m%dT%H:%M')
				chamber_actions[action_time.strftime('%s')] = 'C'

			self.house_calendar = chamber_actions
			self.house_calendar_updated = datetime.now()

		elif chamber.lower() == 'senate':
			senate_request = requests.get('https://www.senate.gov/legislative/schedule/floor_schedule.xml')
		else:
			sys.exit()

	# Report current status for a chamber.
	def status(self,chamber,time = None):
		# DC time, in Epoch seconds
		if time == None:
			dctime_epoch = datetime.now(self.DCT).strftime('%s')
		else:
			dctime_epoch = time.strftime('%s')

		if chamber.lower() == 'house':
			# IF time requested is less than the earliest calendar item, return an error.
			if dctime_epoch < min(self.house_calendar):
				error = {
					'status': 'E',
					'desc': 'Requested time ' + time.strftime('%Y-%m-%d %H:%M') + ' before available calendar data.' }
				return(error)
			elif dctime_epoch > max(self.house_calendar):
				error = {
					'status': 'E',
					'desc': 'Requested time ' + time.strftime('%Y-%m-%d %H:%M') + ' after available calendar data.' }
				return(error)
			else:
				action_time = max(k for k in self.house_calendar if k <= dctime_epoch)
				action = self.house_calendar[action_time]
		result = {
			'status': action,
			'timestamp': action_time,
			'desc': 'House ' + self.action_name(action) + ' at ' + datetime.fromtimestamp(int(action_time)).strftime('%m/%d/%Y %H:%M')
			}
		return result

	# Figure next action
	def next(self,chamber,time = None):
		if time == None:
			dctime_epoch = datetime.now(self.DCT).strftime('%s')
		else:
			dctime_epoch = time.strftime('%s')

		if chamber.lower() == 'house':
			action_time = min(k for k in self.house_calendar if k >= dctime_epoch)
			action = self.house_calendar[action_time]

		result = {
			'status': action,
			'timestamp': action_time,
			'desc': 'House ' + self.action_name(action,1) + ' at ' + datetime.fromtimestamp(int(action_time)).strftime('%m/%d/%Y %H:%M')
			}
		return result

if __name__ == "__main__":
	insession = insession()
	insession.update('house')

	testtime = datetime.strptime('20210329T1035','%Y%m%dT%H%M')
	print(insession.next('house'))
