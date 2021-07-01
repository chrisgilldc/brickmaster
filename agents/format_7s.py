###
#
# Mini-library to format strings for 7 segment displays
#
###


def time_7s(data,elements):
	if data < 10:
		return("00:0" + str(int(data)))
	elif data >= 60:
		return(str(data // 60) + ":" + str(data % 60))
	else:
		return("00:" + str(int(data)))
