###
#
# Mini-library to format strings for 7 segment displays
#
###


def time_7s(data):
	# Return an error if this is out of range.
	if data <= -599 or data > 6039:
		return("ERR")
	# Negative values under 60s.
	elif data < -59:
		data = abs(data)
		return("-" + str(int(data // 60)) + ":" + str(int(data % 60)).zfill(2))
	elif data < 0:
		data = abs(data)
		return("- :" + str(data).zfill(2))
	elif data == 0:
		return("00:00")
	# Over 60s, M:S
	elif data >= 60:
		return(str(int(data // 60)).zfill(2) + ":" + str(int(data % 60)).zfill(2))
	# Otherwise, 00:SS
	else:
		return("00:" + str(int(data)).zfill(2))

def number_7s(data):
	data = str(data).split('.')
	# Return error if integer part is too long to display.
	if len(data[0]) > 4:
		return("E-TL")
	# If it's not a float, just return the value back.
	elif len(data) == 1:
		return(str(data[0]))
	else:
		# Have we gotten to >= 1000? Then just return that.
		if int(data[0]) >= 1000:
			return(str(data[0]))
		else:
		# Otherwise, include as many decimals as we can.
			float_len = 4 - len(data[0])
			return(str(data[0] + '.' + data[1][0:float_len]))
