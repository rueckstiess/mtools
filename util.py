from datetime import datetime
import re

weekdays = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']


def extractDateTime(line):
    tokens = line.split()
    if len(tokens) < 4:
        # check if there are enough tokens for datetime
        return None

    # log file structure: Wed Sep 05 23:02:26 ...
    weekday, month, day, time = tokens[:4]
    
    # check if it is a valid datetime
    if not (weekday in weekdays and
    	    month in months and
            re.match(r'\d{1,2}', day) and
            re.match(r'\d{2}:\d{2}:\d{2}', time)):
        return None

    month = months.index(month)+1
    h, m, s = time.split(':')

    # TODO: special case if year rolls over but logfile is from old year
    year = datetime.now().year

    dt = datetime(int(year), int(month), int(day), int(h), int(m), int(s))

    return dt