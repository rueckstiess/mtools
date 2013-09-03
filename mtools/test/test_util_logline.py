import sys
from nose.tools import *
from mtools.util.logline import LogLine
import time

line_ctime_pre24 = "Sat Aug  3 21:52:05 [initandlisten] db version v2.2.4, pdfile version 4.5"
line_ctime = "Sat Aug  3 21:52:05.995 [initandlisten] db version v2.4.5"
line_iso8601_local = "2013-08-03T21:52:05.995+1000 [initandlisten] db version v2.5.2-pre-"
line_iso8601_utc = "2013-08-03T11:52:05.995Z [initandlisten] db version v2.5.2-pre-"
line_getmore = "Mon Aug  5 20:26:32 [conn9] getmore local.oplog.rs query: { ts: { $gte: new Date(5908578361554239489) } } cursorid:1870634279361287923 ntoreturn:0 keyUpdates:0 numYields: 107 locks(micros) r:85093 nreturned:13551 reslen:230387 144ms"


def test_logline_datetime_parsing():
    """ Check that all four timestamp formats are correctly parsed. """

    ll = LogLine(line_ctime_pre24)
    ll_str = ll.line_str
    assert(str(ll.datetime) == '2013-08-03 21:52:05')
    assert(ll._datetime_format == 'ctime-pre2.4')
    print ll_str
    print ll.line_str
    assert(ll.line_str == ll_str)

    ll = LogLine(line_ctime)
    ll_str = ll.line_str
    assert(str(ll.datetime) == '2013-08-03 21:52:05.995000')
    assert(ll._datetime_format == 'ctime')
    assert(ll.line_str == ll_str)

    ll = LogLine(line_iso8601_utc)
    ll_str = ll.line_str
    assert(str(ll.datetime) == '2013-08-03 11:52:05.995000+00:00')
    assert(ll._datetime_format == 'iso8601-utc')
    assert(ll.line_str == ll_str)

    ll = LogLine(line_iso8601_local)
    ll_str = ll.line_str
    assert(str(ll.datetime) == '2013-08-03 21:52:05.995000+10:00')
    assert(ll._datetime_format == 'iso8601-local')
    assert(ll.line_str == ll_str)


def test_logline_value_extraction():
    """ Check for correct value extraction of all fields. """
    
    ll = LogLine(line_getmore)
    assert(ll.thread == 'conn9')
    assert(ll.operation == 'getmore')
    assert(ll.namespace == 'local.oplog.rs')
    assert(ll.duration == 144)
    assert(ll.numYields == 107)
    assert(ll.r == 85093)
    assert(ll.ntoreturn == 0)
    assert(ll.nreturned == 13551)


def test_logline_lazy_evaluation():
    """ Check that all LogLine variables are evaluated lazily. """
    
    fields = ['_thread', '_operation', '_namespace', '_duration', '_numYields', '_r', '_ntoreturn', '_nreturned']

    # before parsing all member variables need to be None
    ll = LogLine(line_getmore)
    for attr in fields:
        assert(getattr(ll, attr) == None)

    # after parsing, they all need to be filled out
    ll.parse_all()
    for attr in fields:
        assert(getattr(ll, attr) != None)
