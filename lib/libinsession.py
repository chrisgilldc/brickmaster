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
		self.calendar = {}
		self.calendar['house'] = {}
		self.calendar['senate'] = {}
		# Initialize variable for updates.
		self.house_updated = ""
		self.senate_updated = ""
		# Days of history to keep
		self.config_house_days = 14
		self.config_senate_days = 14
		# Auto-recheck time. If calendar hasn't be updated in this amount of time, do it.
		self.config_house_recheck = 14400
		self.config_senate_recheck = 14400
		# Trigger updates for both chambers.
		self.__update_house()
		self.__update_senate()


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

	# Updating the Senate.
	def __update_senate(self):
		# Required imports for functions
		from datetime import datetime,timedelta	# For date/Time management
		import pytz				# For Timezones
		import requests				# For getting files from the web
		import xml.etree.ElementTree as ET 	# For XML processing
		import sys

		# Get the Senate floor schedule. It's always one big schedule so we can just grab it.
		senate_request = requests.get('https://www.senate.gov/legislative/schedule/floor_schedule.xml')
		senate_xml = ET.fromstring(senate_request.content)

		for meeting in senate_xml.findall(".//meeting"):
			convene = meeting.find(".//convene")
			adjourn = meeting.find(".//adjourn")
			# Senate only tracks date on the Convene entity. Extract that so we can use it for adjournment too.
			senate_date = "2021" + convene.get('month') + convene.get('date')

			# All Meetings have a convening time.
			convene_timestamp = datetime.strptime(senate_date + convene.get('time'),'%Y%m%d%H%M').strftime('%s')

			# If there's an adjournment, figure that out too.
			# Meetings that haven't adjourned yet have an adjourn element with an empty time, so we have to trap it.
			if ( adjourn is not None ) and ( adjourn.get('time') != "" ):
				adjourn_timestamp = datetime.strptime(senate_date + adjourn.get('time').replace(':',''),'%Y%m%d%H%M').strftime('%s')
				# When the Senate has a Pro Forma session, the convening time and adjournment time will be the same. Skip those.
				if adjourn_timestamp != convene_timestamp:
					self.calendar['senate'][int(convene_timestamp)] = {
						'display_time': datetime.fromtimestamp(int(convene_timestamp)),
						'status': 'C',
						'source': 'cal' }

					self.calendar['senate'][int(adjourn_timestamp)] = {
						'display_time': datetime.fromtimestamp(int(adjourn_timestamp)),
						'status': 'A',
						'source': 'cal' }
				# If the convene time is in the future, no adjourn time is reported. This is fine, so go ahead.
				elif convene_timestamp >= datetime.now(self.DCT).strftime('%s'):
					self.calendar['senate'][int(convene_timestamp)] = {
						'display_time': datetime.fromtimestamp(int(convene_timestamp)),
						'status': 'C',
						'source': 'cal' }
			else:
				self.calendar['senate'][int(convene_timestamp)] = {
					'display_time': datetime.fromtimestamp(int(convene_timestamp)),
					'status': 'C',
					'source': 'cal' }

		# Call for a scrape of Congress.Gov to supplement the legislative calendar.
		self.__scrape('senate')

		self.senate_updated = datetime.now().timestamp()

		# Auto-prune
		self.__prune_calendar('senate')

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
			self.calendar['house'][int(action_time.strftime('%s'))] = {
				'display_time': action_time,
				'status': 'C',
				'source': 'cal' }

		for floor_action in house_xml.findall(".//*..[@act-id='H61000']"):
			action_time = datetime.strptime(floor_action.attrib['update-date-time'], '%Y%m%dT%H:%M')
			self.calendar['house'][int(action_time.strftime('%s'))] = {
				'display_time': action_time,
				'status': 'A',
				'source': 'cal' }
		try:
			next_convene = house_xml.find(".//legislative_day_finished").attrib
		except:
			next_convene = 0
		else:
			action_time = datetime.strptime(next_convene['next-legislative-day-convenes'], '%Y%m%dT%H:%M')
			self.calendar['house'][int(action_time.strftime('%s'))] = {
				'display_time': action_time,
				'status': 'C',
				'source': 'cal' }
		print("Dumping house calendar...")
		print(self.calendar['house'])

		# Call for a scrape of Congress.Gov to supplement the legislative calendar and to get real actual status.
		self.__scrape('house')

		# Update the timestamp...
		self.house_updated = datetime.now().timestamp()

		# Auto-prune.
		self.__prune_calendar('house')

	# Prune the calendar.
	def __prune_calendar(self,chamber = "Both"):
		# Required imports for function
		from datetime import datetime,timedelta	# For date/Time management

		if ( chamber.lower() == "house" ) or ( chamber == "Both" ):
			house_limit_time = datetime.now(self.DCT) - timedelta(days=self.config_house_days)
			house_limit_time = int(house_limit_time.strftime('%s'))
			self.calendar['house'] = {key:val for key, val in self.calendar['house'].items() if key >= house_limit_time}
			self.house_last_pruned = datetime.now().timestamp()

		if ( chamber.lower() == "senate" ) or ( chamber == "Both" ):
			senate_limit_time = datetime.now(self.DCT) - timedelta(days=self.config_senate_days)
			senate_limit_time = int(senate_limit_time.strftime('%s'))
			self.calendar['senate'] = {key:val for key, val in self.calendar['senate'].items() if key >= senate_limit_time}
			self.senate_last_pruned = datetime.now().timestamp()

	# Scrape congress.gov if we don't know anything from the calendar.
	def __scrape(self,chamber):
		import requests
		from datetime import datetime
		from bs4 import BeautifulSoup

		# Has to be a valid chamber
		if chamber.lower() not in ('house','senate'):
			return 1

		# Request Congress.gov
		cg_request = requests.get('https://congress.gov')
		# Return an error if we couldn't scrape congress.gov
		if not cg_request.ok:
			return 1

		# Parse the response into a BeautifulSoup data object.
		cg_data = BeautifulSoup(cg_request.content,'html.parser')

		# Collector for our return data
		return_data = {}

		# Timestamp to use for 'artificial' actions when we need it.
		scrape_timestamp = int(datetime.now().strftime('%s')) - 10

		# Current time in DC.
		dctime_epoch = int(datetime.now(self.DCT).strftime('%s'))

		# Get the most recent calendar action for this chamber, for sake of comparison
		action_time = max(k for k in self.calendar[chamber] if k <= dctime_epoch)
		action = self.calendar[chamber][action_time]

		# Pull the chamber data into an easily identified variable.
		chamber_data = cg_data.find(class_='home-current-' + chamber)

		# What class are they using to show the status?
		if chamber_data.find(class_='outOfSession'):
			# If currently out of session but most recent calendar action says in session, add "artificial" calendar item to update.
			if action['status'] == 'C':
				self.calendar[chamber][scrape_timestamp] = {
					'display_time': datetime.fromtimestamp(int(scrape_timestamp)),
					"status": "A",
					"source": "scrape" }
			# If out of session, should list a next meeting. It's in the span of the 'activity' div.
			chamber_activity = chamber_data.find(class_='activity').span.text
			# If it's a real result, process it and add it to the calendar.
			if type(chamber_activity) == str:
				# Convert to timestamp
				chamber_next_timestamp = int(datetime.strptime(chamber_activity,'%B %d, %Y at %H:%M %p %Z').strftime('%s'))
				# If this action isn't already in the calendar, add it.
				if chamber_next_timestamp not in self.calendar[chamber].keys():
					self.calendar[chamber][chamber_next_timestamp] = {
						"display_time": datetime.fromtimestamp(int(chamber_next_timestamp)),
						"status": "C",
						"source": "scrape" }
		elif chamber_data.find(class_='inSession'):
		# If currently in session but most recent calendar says adjourned, add "artifical" calendar item to update.
			if action['status'] == 'A':
				self.calendar[chamber][scrape_timestamp] = {
					"display_time": datetime.fromtimestamp(int(scrape_timestamp)),
					"status": "C",
					"source": "scrape" }
		else:
			# Should always find either in session or out of session. If neither, return error.
			return 1
		return 0


	# Gateway function for updating chambers.
	def update_chamber(self,chamber):
		if chamber.lower() == 'house':
			self.__update_house
		elif chamber.lower() == 'senate':
			self.__update_senate
		else:
			return 1
		return 0

	# Report current status for a chamber.
	def status(self,chamber,time = None):
		# Required imports for function
		from datetime import datetime,timedelta	# For date/Time management
		import pytz				# For Timezones
		import sys

		# Validate chamber names, and if calendar is empty, call an update
		if ( chamber.lower() == 'house' ):
			if len(self.calendar['house'].keys()) == 0:
				self.__update_house()
		elif ( chamber.lower() == 'senate' ):
			if len(self.calendar['senate'].keys()) == 0:
				self.update_senate()
		else:
			# If we don't have a valid chamber, blow it all up.
			sys.exit(1)

		# Default time to 'now', otherwise use the requested time passed to us.
		if time == None:
			dctime_epoch = int(datetime.now(self.DCT).strftime('%s'))
		else:
			dctime_epoch = int(time.strftime('%s'))

		# IF time requested is less than the earliest calendar item, return an error.
		if dctime_epoch < min(self.calendar[chamber]):
			print(chamber,file=sys.stderr)
			print(dctime_epoch,file=sys.stderr)
			print(min(self.calendar[chamber]),file=sys.stderr)
			print(self.calendar[chamber],file=sys.stderr)
			error = {
				'status': 'E',
				'desc': 'Requested time ' + time.strftime('%Y-%m-%d %I:%M %p') + ' before available calendar data.' }
			return(error)
		else:
			# Find the most recent calendar item.
			action_time = max(k for k in self.calendar[chamber] if k <= dctime_epoch)
			action = self.calendar[chamber][action_time]

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

		if action['source'] == 'cal':
			description = chamber.capitalize() + ' ' + self.action_name(action['status']) + ' ' + datetime.fromtimestamp(int(action_time)).strftime('%A %B %d at %I:%M %p')
		elif action['source'] == 'scrape':
			description = chamber.capitalize() + ' stands adjourned.' if action['status'] == 'A' else ' is in session.' if action['status'] == 'C' else ' has unknown status.'
		else:
			description = chamber.capitalize() + ' has unknown status.'

		result = {
			'status': action['status'],
			'source': action['source'],
			'timestamp': action_time,
			'desc': description
			}
		return result

	# Figure next action
	def next(self,chamber,time = None):
		# Required imports for function
		from datetime import datetime,timedelta	# For date/Time management
		import pytz				# For Timezones

		if time == None:
			dctime_epoch = int(datetime.now(self.DCT).strftime('%s'))
		else:
			dctime_epoch = int(time.strftime('%s'))

		if chamber.lower() == 'house':
			target_calendar = self.calendar['house']
		elif chamber.lower() == 'senate':
			target_calendar = self.calendar['senate']
		else:
			return 1

		# Check if there are future events in the calendar.
		future_actions = []
		for k in target_calendar:
			if k >= dctime_epoch:
				future_actions.append(k)

		if len(future_actions) > 0:
			next_action_time = int(min(future_actions))
			next_action = target_calendar[next_action_time]
			result = {
				'status': next_action,
				'timestamp': next_action_time,
				'desc': chamber.capitalize() + ' ' + self.action_name(next_action,1) + ' at ' + datetime.fromtimestamp(int(next_action_time)).strftime('%m/%d/%Y %I:%M %p')
			}
		else:
			result = {
				'status': 'none',
				'timestamp': '0',
				'desc': 'No future actions on calendar'
			}

		return result
