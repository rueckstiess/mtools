import sys
from nose.tools import *
from mtools.util.logline import LogEvent
import time

line_ctime_pre24 = "Sun Aug  3 21:52:05 [initandlisten] db version v2.2.4, pdfile version 4.5"
line_ctime = "Sun Aug  3 21:52:05.995 [initandlisten] db version v2.4.5"
line_iso8601_local = "2013-08-03T21:52:05.995+1000 [initandlisten] db version v2.5.2-pre-"
line_iso8601_utc = "2013-08-03T11:52:05.995Z [initandlisten] db version v2.5.2-pre-"
line_getmore = "Mon Aug  5 20:26:32 [conn9] getmore local.oplog.rs query: { ts: { $gte: new Date(5908578361554239489) } } cursorid:1870634279361287923 ntoreturn:0 keyUpdates:0 numYields: 107 locks(micros) r:85093 nreturned:13551 reslen:230387 144ms"
line_253_numYields = "2013-10-21T12:07:27.057+1100 [conn2] query test.docs query: { foo: 234333.0 } ntoreturn:0 ntoskip:0 keyUpdates:0 numYields:1 locks(micros) r:239078 nreturned:0 reslen:20 145ms"
line_246_numYields = "Mon Oct 21 12:14:21.888 [conn4] query test.docs query: { foo: 23432.0 } ntoreturn:0 ntoskip:0 nscanned:316776 keyUpdates:0 numYields: 2405 locks(micros) r:743292 nreturned:2 reslen:2116 451ms"

def test_logline_datetime_parsing():
    """ Check that all four timestamp formats are correctly parsed. """

    le =  LogEvent(line_ctime_pre24)

    le_str = le.line_str
    assert(str(le.datetime) == '2014-08-03 21:52:05')
    assert(le._datetime_format == 'ctime-pre2.4')
    print le_str
    print le.line_str
    assert(le.line_str[4:] == le_str[4:])

    le =  LogEvent(line_ctime)
    le_str = le.line_str
    assert(str(le.datetime) == '2014-08-03 21:52:05.995000')
    assert(le._datetime_format == 'ctime')
    assert(le.line_str[4:] == le_str[4:])

    le =  LogEvent(line_iso8601_utc)
    le_str = le.line_str
    assert(str(le.datetime) == '2013-08-03 11:52:05.995000+00:00')
    assert(le._datetime_format == 'iso8601-utc')
    assert(le.line_str[4:] == le_str[4:])

    le =  LogEvent(line_iso8601_local)
    le_str = le.line_str
    assert(str(le.datetime) == '2013-08-03 21:52:05.995000+10:00')
    assert(le._datetime_format == 'iso8601-local')
    assert(le.line_str[4:] == le_str[4:])


def test_logline_extract_new_and_old_numYields():
    le =  LogEvent(line_246_numYields)
    assert(le.numYields == 2405)

    le =  LogEvent(line_253_numYields)
    assert(le.numYields == 1)


def test_logline_value_extraction():
    """ Check for correct value extraction of all fields. """
    
    le =  LogEvent(line_getmore)
    assert(le.thread == 'conn9')
    assert(le.operation == 'getmore')
    assert(le.namespace == 'local.oplog.rs')
    assert(le.duration == 144)
    assert(le.numYields == 107)
    assert(le.r == 85093)
    assert(le.ntoreturn == 0)
    assert(le.nreturned == 13551)
    assert(le.pattern == '{ts: 1}')


def test_logline_lazy_evaluation():
    """ Check that all LogEvent variables are evaluated lazily. """
    
    fields = ['_thread', '_operation', '_namespace', '_duration', '_numYields', '_r', '_ntoreturn', '_nreturned', '_pattern']

    # before parsing all member variables need to be None
    le =  LogEvent(line_getmore)
    for attr in fields:
        assert(getattr(le, attr) == None)

    # after parsing, they all need to be filled out
    le.parse_all()
    for attr in fields:
        assert(getattr(le, attr) != None)
