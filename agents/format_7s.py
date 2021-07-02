###
#
# Mini-library to format strings for 7 segment displays
#
###


def time_7s(data,elements):
	# Over 60s, M:S
	if data >= 60:
		return(str(int(data // 60)).zfill(2) + ":" + str(int(data % 60)).zfill(2))
	# Otherwise, 00:SS
	else:
		return("00:" + str(int(data)).zfill(2))

def number_7s(data,element):
	if len(str(int(data))) >= 4:
		return str(int(data))
	elif len(str(int(data))) == 3:
		return str(int(data)) + "." + str((data/1) - (data//1))[0]
	elif len(str(int(data))) == 2:
		return str(int(data)) + "." + str((data/1) - (data//1))[0-1]
	elif len(str(int(data))) == 1:
		return str(int(data)) + "." + str((data/1) - (data//1))[0-3]
	else:
		return data
