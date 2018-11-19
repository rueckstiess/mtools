import datetime

from dateutil import parser

from mtools.util.logevent import LogEvent

line_ctime_pre24 = ("Sun Aug  3 21:52:05 [initandlisten] db version v2.2.4, "
                    "pdfile version 4.5")
line_ctime = "Sun Aug  3 21:52:05.095 [initandlisten] db version v2.4.5"
line_iso8601_local = ("2013-08-03T21:52:05.095+1000 [initandlisten] db "
                      "version v2.5.2-pre-")
line_iso8601_utc = ("2013-08-03T11:52:05.095Z [initandlisten] db "
                    "version v2.5.2-pre-")
line_getmore = ("Mon Aug  5 20:26:32 [conn9] getmore local.oplog.rs "
                "query: { ts: { $gte: new Date(5908578361554239489) } } "
                "cursorid:1870634279361287923 ntoreturn:0 keyUpdates:0 "
                "numYields: 107 locks(micros) r:85093 nreturned:13551 "
                "reslen:230387 144ms")
line_253_numYields = ("2013-10-21T12:07:27.057+1100 [conn2] query test.docs "
                      "query: { foo: 234333.0 } ntoreturn:0 ntoskip:0 "
                      "keyUpdates:0 numYields:1 locks(micros) r:239078 "
                      "nreturned:0 reslen:20 145ms")
line_246_numYields = ("Mon Oct 21 12:14:21.888 [conn4] query test.docs query: "
                      "{ foo: 23432.0 } ntoreturn:0 ntoskip:0 nscanned:316776 "
                      "keyUpdates:0 numYields: 2405 locks(micros) r:743292 "
                      "nreturned:2 reslen:2116 451ms")
line_26_planSummary = ("2014-04-09T23:25:32.502+0000 [conn3355] query "
                       "toothsome.dimgray.cranberry query: { "
                       "cid: ObjectId('535c8bc39194bf134f7757c0') } "
                       "planSummary: IXSCAN { cid: 1 } ntoreturn:20 "
                       "ntoskip:0 keyUpdates:0 numYields:0 locks(micros) "
                       "r:793 nreturned:0 reslen:20 0ms")
line_pattern_26_a = ("2014-03-18T18:34:30.435+1100 [conn10] query test.new "
                     "query: { a: 1.0 } planSummary: EOF ntoreturn:0 "
                     "ntoskip:0 keyUpdates:0 numYields:0 locks(micros) r:103 "
                     "nreturned:0 reslen:20 0ms")
line_pattern_26_b = ("2014-03-18T18:34:34.360+1100 [conn10] query test.new "
                     "query: { query: { a: 1.0 }, orderby: { b: 1.0 } } "
                     "planSummary: EOF ntoreturn:0 ntoskip:0 keyUpdates:0 "
                     "numYields:0 locks(micros) r:55 nreturned:0 "
                     "reslen:20 0ms")
line_pattern_26_c = ("2014-03-18T18:34:50.777+1100 [conn10] query test.new "
                     "query: { $query: { a: 1.0 }, $orderby: { b: 1.0 } } "
                     "planSummary: EOF ntoreturn:0 ntoskip:0 keyUpdates:0 "
                     "numYields:0 locks(micros) r:60 nreturned:0 "
                     "reslen:20 0ms")
line_command_26_a = ("2014-11-21T18:20:20.263+0800 [conn9] command "
                     "admin.$cmd command: replSetGetStatus "
                     "{ replSetGetStatus: 1.0, forShell: 1.0 } keyUpdates:0 "
                     "numYields:0  reslen:76 0ms")
line_command_26_b = ('2014-11-21T18:20:57.076+0800 [conn9] command test.$cmd '
                     'command: aggregate { aggregate: "mgendata", '
                     'pipeline: [ { $group: { _id: "$bar", '
                     'avg: { $avg: "$foo" } } } ], cursor: {} } keyUpdates:0 '
                     'numYields:0 locks(micros) r:6783 reslen:229 11ms')
line_truncated_24 = ("Wed Jan 28 00:31:16.302 [conn12345] warning: log line "
                     "attempted (26k) over max size(10k), printing beginning "
                     "and end ... getmore MyDB.MyColl query: "
                     "{ foo: ObjectId('123456789012345678901234'), "
                     "foo: { $in: [ 1, 2, 3 ] }, bar: false } "
                     "cursorid:1234567890123456789 ntoreturn:0 keyUpdates:0 "
                     "numYields: 23 locks(micros) r:24715 nreturned:1324 "
                     "reslen:256993 1445ms")
line_fassert = ("***aborting after fassert() failure")
line_empty = ("")
line_new_oplog_query = ('2018-05-01T21:57:45.989+0000 I REPL [replication-0] Scheduled new oplog query Fetcher source: host.name database: local query: { find: "oplog.rs", filter: { ts: { $gte: Timestamp(1525211859, 1) } }, tailable: true, oplogReplay: true, awaitData: true, maxTimeMS: 60000, batchSize: 13981010, term: 1, readConcern: { afterClusterTime: Timestamp(1525211859, 1) } } query metadata: { $replData: 1, $oplogQueryData: 1, $readPreference: { mode: "secondaryPreferred" } } active: 1 findNetworkTimeout: 65000ms getMoreNetworkTimeout: 7500ms shutting down?: 0 first: 1 firstCommandScheduler: RemoteCommandRetryScheduler request: RemoteCommand 16543 -- target:host.name db:local cmd:{ find: "oplog.rs", filter: { ts: { $gte: Timestamp(1525211859, 1) } }, tailable: true, oplogReplay: true, awaitData: true, maxTimeMS: 60000, batchSize: 13981010, term: 1, readConcern: { afterClusterTime: Timestamp(1525211859, 1) } } active: 1 callbackHandle.valid: 1 callbackHandle.cancelled: 0 attempt: 1 retryPolicy: RetryPolicyImpl maxAttempts: 1 maxTimeMillis: -1ms')

# fake system.profile documents
profile_doc1 = {"op": "query", "ns": "test.foo",
                "thread": "test.system.profile", "query": {"test": 1},
                "ntoreturn": 0, "ntoskip": 0, "nscanned": 0,
                "keyUpdates": 0, "numYield": 0,
                "lockStats": {"timeLockedMicros": {"r": 461, "w": 0},
                              "timeAcquiringMicros": {"r": 4, "w": 3}},
                "nreturned": 0, "responseLength": 20, "millis": 0,
                "ts": parser.parse("2014-03-20T04:04:21.231Z"),
                "client": "127.0.0.1", "allUsers": [], "user": ""}
profile_doc2 = {"op": "query", "ns": "test.foo",
                "thread": "test.system.profile",
                "query": {"query": {"test": 1},
                          "orderby": {"field": 1}}, "ntoreturn": 0,
                "ntoskip": 0, "nscanned": 0, "keyUpdates": 0,
                "numYield": 0,
                "lockStats": {"timeLockedMicros": {"r": 534, "w": 0},
                              "timeAcquiringMicros": {"r": 5, "w": 4}},
                "nreturned": 0, "responseLength": 20, "millis": 0,
                "ts": parser.parse("2014-03-20T04:04:33.775Z"),
                "client": "127.0.0.1", "allUsers": [], "user": ""}
profile_doc3 = {"op": "query", "ns": "test.foo",
                "thread": "test.system.profile",
                "query": {"$query": {"test": 1},
                          "$orderby": {"field": 1}}, "ntoreturn": 0,
                "ntoskip": 0, "nscanned": 0, "keyUpdates": 0,
                "numYield": 0,
                "lockStats": {"timeLockedMicros": {"r": 436, "w": 0},
                              "timeAcquiringMicros": {"r": 5, "w": 8}},
                "nreturned": 0, "responseLength": 20, "millis": 0,
                "ts": parser.parse("2014-03-20T04:04:52.791Z"),
                "client": "127.0.0.1", "allUsers": [], "user": ""}


def test_logevent_datetime_parsing():
    """Check that all four timestamp formats are correctly parsed."""

    le = LogEvent(line_ctime_pre24)
    this_year = datetime.datetime.now().year

    le_str = le.line_str
    assert(str(le.datetime) == '%s-08-03 21:52:05+00:00' % this_year)
    assert(le._datetime_format == 'ctime-pre2.4')
    assert(le.line_str[4:] == le_str[4:])
    # make sure all datetime objects are timezone aware
    assert(le.datetime.tzinfo is not None)

    le = LogEvent(line_ctime)
    le_str = le.line_str
    assert(str(le.datetime) == '%s-08-03 21:52:05.095000+00:00' % this_year)
    assert(le._datetime_format == 'ctime')
    assert(le.line_str[4:] == le_str[4:])
    # make sure all datetime objects are timezone aware
    assert(le.datetime.tzinfo is not None)

    le = LogEvent(line_iso8601_utc)
    le_str = le.line_str
    assert(str(le.datetime) == '2013-08-03 11:52:05.095000+00:00')
    assert(le._datetime_format == 'iso8601-utc')
    assert(le.line_str[4:] == le_str[4:])
    # make sure all datetime objects are timezone aware
    assert(le.datetime.tzinfo is not None)

    le = LogEvent(line_iso8601_local)
    le_str = le.line_str
    assert(str(le.datetime) == '2013-08-03 21:52:05.095000+10:00')
    assert(le._datetime_format == 'iso8601-local')
    assert(le.line_str[4:] == le_str[4:])
    # make sure all datetime objects are timezone aware
    assert(le.datetime.tzinfo is not None)


def test_logevent_pattern_parsing():
    le = LogEvent(line_pattern_26_a)
    assert(le.pattern) == '{"a": 1}'

    le = LogEvent(line_pattern_26_b)
    assert(le.pattern) == '{"a": 1}'

    le = LogEvent(line_pattern_26_c)
    assert(le.pattern) == '{"a": 1}'


def test_logevent_actual_query_parsing():
    le = LogEvent(line_pattern_26_a)
    assert(le.actual_query) == '{ a: 1.0 }'

    le = LogEvent(line_pattern_26_b)
    assert(le.actual_query) == '{ a: 1.0 }'

    le = LogEvent(line_pattern_26_c)
    assert(le.actual_query) == '{ a: 1.0 }'


def test_logevent_command_parsing():
    le = LogEvent(line_command_26_a)
    assert(le.command) == 'replsetgetstatus'

    le = LogEvent(line_command_26_b)
    assert(le.command) == 'aggregate'

    le = LogEvent(line_getmore)
    assert(le.command) is None


def test_logevent_sort_pattern_parsing():
    le = LogEvent(line_pattern_26_a)
    assert(le.sort_pattern) is None

    le = LogEvent(line_pattern_26_b)
    assert(le.sort_pattern) == '{"b": 1}'

    le = LogEvent(line_pattern_26_c)
    assert(le.sort_pattern) == '{"b": 1}'


def test_logevent_actual_sort_parsing():
    le = LogEvent(line_pattern_26_a)
    assert(le.actual_sort) is None

    le = LogEvent(line_pattern_26_b)
    assert(le.actual_sort) == '{ b: 1.0 }'

    le = LogEvent(line_pattern_26_c)
    assert(le.actual_sort) == '{ b: 1.0 }'


def test_logevent_profile_pattern_parsing():
    le = LogEvent(profile_doc1)
    assert(le.pattern == '{"test": 1}')

    le = LogEvent(profile_doc2)
    assert(le.pattern == '{"test": 1}')

    le = LogEvent(profile_doc3)
    assert(le.pattern == '{"test": 1}')


def test_logevent_profile_sort_pattern_parsing():
    le = LogEvent(profile_doc1)
    assert(le.sort_pattern is None)

    le = LogEvent(profile_doc2)
    assert(le.sort_pattern == '{"field": 1}')

    le = LogEvent(profile_doc3)
    assert(le.sort_pattern == '{"field": 1}')


def test_logevent_extract_new_and_old_numYields():
    le = LogEvent(line_246_numYields)
    assert(le.numYields == 2405)

    le = LogEvent(line_253_numYields)
    assert(le.numYields == 1)


def test_logevent_parse_truncated_line():
    le = LogEvent(line_truncated_24)
    assert(le.thread == "conn12345")
    assert(le.numYields == 23)
    assert(le.operation == "getmore")


def test_logevent_extract_planSummary():
    le = LogEvent(line_26_planSummary)
    assert(le.planSummary == "IXSCAN")

    le = LogEvent(line_pattern_26_a)
    assert(le.planSummary == "EOF")


def test_logevent_extract_actualPlanSummary():
    le = LogEvent(line_26_planSummary)
    assert(le.actualPlanSummary == "IXSCAN { cid: 1 }")

    le = LogEvent(line_pattern_26_a)
    assert(le.actualPlanSummary == "EOF")


def test_logevent_value_extraction():
    """ Check for correct value extraction of all fields. """

    le = LogEvent(line_getmore)
    assert(le.thread == 'conn9')
    assert(le.operation == 'getmore')
    assert(le.namespace == 'local.oplog.rs')
    assert(le.duration == 144)
    assert(le.numYields == 107)
    assert(le.r == 85093)
    assert(le.ntoreturn == 0)
    assert(le.nreturned == 13551)
    assert(le.pattern == '{"ts": 1}')


def test_logevent_non_log_line():
    """ Check that LogEvent correctly ignores non log lines"""
    le = LogEvent(line_fassert)
    assert(le.thread == None)
    assert(le.operation == None)
    assert(le.namespace == None)
    assert(le.duration == None)
    assert(le.numYields == None)
    assert(le.r == None)
    assert(le.ntoreturn == None)
    assert(le.nreturned == None)
    assert(le.pattern == None)

    le = LogEvent(line_empty)
    assert(le.thread == None)
    assert(le.operation == None)
    assert(le.namespace == None)
    assert(le.duration == None)
    assert(le.numYields == None)
    assert(le.r == None)
    assert(le.ntoreturn == None)
    assert(le.nreturned == None)
    assert(le.pattern == None)


def test_logevent_new_oplog_query():
    """ Check that LogEvent correctly ignores new oplog query for duration extraction """
    le = LogEvent(line_new_oplog_query)
    assert(le.duration == None)


def test_logevent_lazy_evaluation():
    """ Check that all LogEvent variables are evaluated lazily. """

    fields = ['_thread', '_operation', '_namespace', '_duration',
              '_numYields', '_r', '_ntoreturn', '_nreturned', '_pattern']

    # before parsing all member variables need to be None
    le = LogEvent(line_getmore)
    for attr in fields:
        assert(getattr(le, attr) is None)

    # after parsing, they all need to be filled out
    le.parse_all()
    for attr in fields:
        assert(getattr(le, attr) is not None)
