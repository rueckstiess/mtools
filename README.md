mlogfilter
==========

filter to parse mongodb log files.

usage: mlogfilter logfile [-h] [--from [FROM]] [--to [TO]] [--tags [TAGS]] [--slow]
                     
positional arguments:
  logfile               logfile to parse

optional arguments:
  -h, --help            show this help message and exit
  --from [FROM]         output starting at FROM
  --to [TO]             output up to TO
  --tags [TAGS]         only output lines matching any of [TAG]
  --slow                only output lines with query times longer than 1000 ms


[FROM] and [TO] can be any combination of [DATE] [TIME] [OFFSET] in that order. 

[DATE] can be 
- a 3-letter weekday (Mon, Tue, Wed, ...)
- a date as 3-letter month, 1-2 digits day   (Sep 5, Jan 31, Aug 08)
- the words: today, now, start, end

[TIME] can be
- hours and minutes    20:15, 04:00, 3:00
- hours, minutes and seconds   13:30:01, 4:55:55

[OFFSET] consists of [OPERATOR][VALUE][UNIT]

[OPERATOR] can be + or -    (note that - can only be used if the whole "[DATE] [TIME] [OFFSET]" is in quotation marks, otherwise it would be confused with a separate parameter)
[VALUE] any number
[UNIT] can be any of s, sec, m, min, h, hours, d, days, w, weeks, m, months, y, years

The [OFFSET] is added/subtracted to/from the specified [DATE] [TIME].

For the [FROM] parameter, the default is the same as 'start' (0001-01-01 00:00:00). If _only_ an [OFFSET] is given, it is added to 'start' (which is not very useful).
For the [TO] parameter, the default is the same as 'end' (9999-31-12 23:59:59). If _only_ an [OFFSET] is given, however, it is added to [FROM].

Example:  "--from today 20:15 --to +3h"  will go from today's date at 20:15:00 to today's date at 23:15:00.

