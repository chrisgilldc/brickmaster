#!/usr/bin/python3

###
#
# In Session!
#
# Is Congress in session? Now you can know!
#
###

class insession:
	"""Find out the status of the US Congress"""

	# Class instantiation
	def __init__(self):

		import pytz
		# Create an object for the DC Timezone
		self.DCT = pytz.timezone('America/New_York')
		# Initialize dictionaries for the calendars
		self.house_calendar = {}
		self.senate_calendar = {}
		# Initialize variable for updates.
		self.house_updated = ""
		self.senate_updated = ""
		# Days of history to keep
		self.config_house_days = 14
		self.config_senate_days = 14
		# Amount of time to recheck the calendar in seconds
		# (Default: 6 Hours / 21,600 s)
		self.config_house_recheck = 21600
		self.config_senate_recheck = 21600

	# Utility to convert status codes to action names
	def __action_name(self,action,future = 0):
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

	# Updating the Senate.
	def __update_senate(self):
		# Required imports for functions
		from datetime import datetime,timedelta	# For date/Time management
		import pytz				# For Timezones
		import requests				# For getting files from the web
		import xml.etree.ElementTree as ET 	# For XML processing

		# Get the Senate floor schedule. It's always one big schedule so we can just grab it.
		senate_request = requests.get('https://www.senate.gov/legislative/schedule/floor_schedule.xml')
		senate_xml = ET.fromstring(senate_request.content)

		for meeting in senate_xml.findall(".//meeting"):
			convene = meeting.find(".//convene")
			adjourn = meeting.find(".//adjourn")
			# Senate only tracks date on the Convene entity. Extract that so we can use it for adjournment too.
			senate_date = "2021" + convene.get('month') + convene.get('date')

			# All Meetings have a convening time.
			convene_time = datetime.strptime(senate_date + convene.get('time'),'%Y%m%d%H%M').strftime('%s')

			# If there's an adjournment, figure that out too.
			if adjourn is not None:
				# Meetings that haven't adjourned yet have an adjourn element with an empty time, so we have to trap it.
				if adjourn.get('time') != "":
					adjourn_time = datetime.strptime(senate_date + adjourn.get('time').replace(':',''),'%Y%m%d%H%M').strftime('%s')
					# When the Senate has a Pro Forma session, the convening time and adjournment time will be the same. Skip those.
					if adjourn_time != convene_time:
						self.senate_calendar[convene_time] = 'C'
						self.senate_calendar[adjourn_time] = 'A'
				# If the convene time is in the future, no adjourn time is reported. This is fine, so go ahead.
				elif convene_time >= datetime.now(self.DCT).strftime('%s'):
					self.senate_calendar[convene_time] = 'C'
			else:
				self.senate_calendar[convene_time] = 'C'

		self.senate_updated = datetime.now().timestamp()

	# Updating the House.
	def __update_house(self):
		# Required imports for function
		from datetime import datetime,timedelta	# For date/Time management
		import pytz				# For Timezones
		import requests				# For getting files from the web
		import xml.etree.ElementTree as ET 	# For XML processing

		dctime = datetime.now(self.DCT)
		# Make chamber date distinct from current date in DC, so we can test for them not being the same later.
		house_date = dctime
		# Try to get the a House floor summary for today.
		house_request = requests.get('https://clerk.house.gov/floorsummary/' + house_date.strftime('%Y%m%d') + '.xml')
		# If request errors, go back a day and try again.
		while not house_request.ok:
			house_date = house_date - timedelta(days=1)
			house_request = requests.get('https://clerk.house.gov/floorsummary/' + house_date.strftime('%Y%m%d') + '.xml')

		house_xml = ET.fromstring(house_request.content)

		for floor_action in house_xml.findall(".//*..[@act-id='H20100']"):
			# Convert to Epoch
			action_time = datetime.strptime(floor_action.attrib['update-date-time'], '%Y%m%dT%H:%M')
			self.house_calendar[action_time.strftime('%s')] = 'C'

		for floor_action in house_xml.findall(".//*..[@act-id='H61000']"):
			action_time = datetime.strptime(floor_action.attrib['update-date-time'], '%Y%m%dT%H:%M')
			self.house_calendar[action_time.strftime('%s')] = 'A'
		try:
			next_convene = house_xml.find(".//legislative_day_finished").attrib
		except:
			next_convene = 0
		else:
			action_time = datetime.strptime(next_convene['next-legislative-day-convenes'], '%Y%m%dT%H:%M')
			self.house_calendar[action_time.strftime('%s')] = 'C'

		# Update the timestamp...
		self.house_updated = datetime.now().timestamp()

	# Prune the calendar.
	def __prune_calendar(self,chamber = "Both"):
		# Required imports for function
		from datetime import datetime,timedelta	# For date/Time management

		if ( chamber.lower() == "house" ) or ( chamber == "Both" ):
			house_limit_time = datetime.now(self.DCT) - timedelta(days=self.config_house_days)
			house_limit_time = house_limit_time.strftime('%s')
			self.house_calendar = {key:val for key, val in self.house_calendar.items() if key >= house_limit_time}
			self.house_last_pruned = datetime.now().timestamp()

		if ( chamber.lower() == "senate" ) or ( chamber == "Both" ):
			senate_limit_time = datetime.now(self.DCT) - timedelta(days=self.config_senate_days)
			senate_limit_time = senate_limit_time.strftime('%s')
			self.senate_calendar = {key:val for key, val in self.senate_calendar.items() if key >= senate_limit_time}
			self.senate_last_pruned = datetime.now().timestamp()

	# Helper function to fetch the right calendar and trigger updates when necessary.
	def __chamber_calendar(self,chamber):
		# Required imports for function
		import sys
		# Pull the calendar for the correct chamber.
		if ( chamber.lower() == "house" ):
			# If calendar is empty, it's probably startup, trigger an update.
			if len(self.house_calendar.keys()) == 0:
				self.__update_house()
			chamber_calendar = self.house_calendar
		elif ( chamber.lower() == "senate" ):
			# If calendar is empty, it's probably startup, trigger an update.
			if len(self.senate_calendar.keys()) == 0:
				self.__update_senate()
			chamber_calendar = self.senate_calendar
		else:
			sys.exit(1)
		return chamber_calendar

	# Report current status for a chamber.
	def status(self,chamber,time = None):
		# Required imports for function
		from datetime import datetime,timedelta	# For date/Time management
		import pytz				# For Timezones


		chamber_calendar = self.__chamber_calendar(chamber)

		# DC time, in Epoch seconds
		if time == None:
			dctime_epoch = datetime.now(self.DCT).strftime('%s')
		else:
			dctime_epoch = time.strftime('%s')

		# IF time requested is less than the earliest calendar item, return an error.
		if dctime_epoch < min(chamber_calendar):
			error = {
				'status': 'E',
				'desc': 'Requested time ' + time.strftime('%Y-%m-%d %H:%M') + ' before available calendar data.' }
			return(error)
		else:
			action_time = max(k for k in chamber_calendar if k <= dctime_epoch)
			action = chamber_calendar[action_time]

		# Do housekeeping for the chamber before returning.
		# Trigger a pruning for the calendar.
		self.__prune_calendar(chamber)
		# Check for calendar recheck expiration.
		if chamber.lower() == "house":
			if ( datetime.now().timestamp() - self.house_updated ) >= self.config_house_recheck:
				self.__update_house()
		if chamber.lower == "senate":
			if ( datetime.now().timestamp() - self.senate_updated ) >= self.config_senate_recheck:
				self.__update_senate()


		result = {
			'status': action,
			'timestamp': action_time,
			'desc': chamber + ' ' + self.__action_name(action) + ' at ' + datetime.fromtimestamp(int(action_time)).strftime('%m/%d/%Y %H:%M')
			}
		return result

	# Figure next action
	def next(self,chamber,time = None):
		# Required imports for function
		from datetime import datetime,timedelta	# For date/Time management
		import pytz				# For Timezones

		if time == None:
			dctime_epoch = datetime.now(self.DCT).strftime('%s')
		else:
			dctime_epoch = time.strftime('%s')

		if chamber.lower() == 'house':
			action_time = min(k for k in self.house_calendar if k >= dctime_epoch)
			action = self.house_calendar[action_time]
		elif chamber.lower() == 'senate':
			action_time = min(k for k in self.senate_calendar if k >= dctime_epoch)
			action = self.senate_calendar[action_time]

		result = {
			'status': action,
			'timestamp': action_time,
			'desc': chamber + ' ' + self.__action_name(action,1) + ' at ' + datetime.fromtimestamp(int(action_time)).strftime('%m/%d/%Y %H:%M')
			}
		return result
