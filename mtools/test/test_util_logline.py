import sys
from nose.tools import *
from mtools.util.logline import LogLine
import time

line_ctime_pre24 = "Sat Aug  3 21:52:05 [initandlisten] db version v2.2.4, pdfile version 4.5"
line_ctime = "Sat Aug  3 21:52:05.995 [initandlisten] db version v2.4.5"
line_iso8601_local = "2013-08-03T21:52:05.995+1000 [initandlisten] db version v2.5.2-pre-"
line_iso8601_utc = "2013-08-03T11:52:05.995Z [initandlisten] db version v2.5.2-pre-"

def test_logline_datetime_parsing():
    """ Check that all four timestamp formats are correctly parsed. """

    ll = LogLine(line_ctime_pre24)
    assert(str(ll.datetime) == '2013-08-03 21:52:05')
    assert(ll._datetime_format == 'ctime-pre2.4')

    ll = LogLine(line_ctime)
    assert(str(ll.datetime) == '2013-08-03 21:52:05.995000')
    assert(ll._datetime_format == 'ctime')

    ll = LogLine(line_iso8601_utc)
    assert(str(ll.datetime) == '2013-08-03 11:52:05.995000+00:00')
    assert(ll._datetime_format == 'iso8601-utc')

    ll = LogLine(line_iso8601_local)
    assert(str(ll.datetime) == '2013-08-03 21:52:05.995000+10:00')
    assert(ll._datetime_format == 'iso8601-local')

