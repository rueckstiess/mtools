import io
import os
from datetime import datetime
import re

from dateutil.tz import tzoffset, tzutc

import mtools
from mtools.util.logevent import LogEvent
from mtools.util.logfile import LogFile


class TestUtilLogFile(object):

    def setup_method(self):
        """Start up method for LogFile fixture."""

        # load logfile(s)
        self.logfile_path = os.path.join(os.path.dirname(mtools.__file__),
                                         'test/logfiles/', 'year_rollover.log')
        self.file_year_rollover = open(self.logfile_path, 'rb')
        self.current_year = datetime.now().year

    def test_len(self):
        """LogFile: test len() and iteration over LogFile method."""

        logfile = LogFile(self.file_year_rollover)
        length = len(logfile)

        i = 0
        for i, le in enumerate(logfile):
            assert isinstance(le, LogEvent)

        assert length == i + 1
        assert length == 1836

    def test_start_end(self):
        """LogFile: test .start and .end property work correctly."""

        logfile = LogFile(self.file_year_rollover)

        assert logfile.start == datetime(self.current_year - 1, 12, 30, 00,
                                         13, 1, 661000, tzutc())
        assert logfile.end == datetime(self.current_year, 1, 2, 23, 27, 11,
                                       720000, tzutc())

    def test_timezone(self):

        logfile_path = os.path.join(os.path.dirname(mtools.__file__),
                                    'test/logfiles/', 'mongod_26.log')
        mongod_26 = open(logfile_path, 'rb')

        logfile = LogFile(mongod_26)
        assert logfile.timezone == tzoffset(None, -14400)

    def test_rollover_detection(self):
        """LogFile: test datetime_format and year_rollover properties."""

        logfile = LogFile(self.file_year_rollover)
        assert logfile.datetime_format == "ctime"
        assert logfile.year_rollover == logfile.end

    def test_storage_engine_detection(self):
        """LogFile: test if the correct storage engine is detected."""

        logfile = LogFile(self.file_year_rollover)
        assert logfile.storage_engine is None

        logfile_path = os.path.join(os.path.dirname(mtools.__file__),
                                    'test/logfiles/', 'mongod_26.log')
        mmapv1 = open(logfile_path, 'rb')
        logfile = LogFile(mmapv1)
        assert logfile.storage_engine == 'mmapv1'

        # test for 3.0 WT detection
        logfile_path = os.path.join(os.path.dirname(mtools.__file__),
                                    'test/logfiles/', 'wiredtiger.log')
        wiredtiger = open(logfile_path, 'rb')
        logfile = LogFile(wiredtiger)
        assert logfile.storage_engine == 'wiredTiger'

        # test for 3.2 WT detection
        logfile_path = os.path.join(os.path.dirname(mtools.__file__),
                                    'test/logfiles/', 'mongod_328.log')
        wiredtiger = open(logfile_path, 'rb')
        logfile = LogFile(wiredtiger)
        assert logfile.storage_engine == 'wiredTiger'

    def test_rsinfo(self):
        """LogFile: test if replication info is detected (MongoDB 3.2+) """

        logfile_path = os.path.join(os.path.dirname(mtools.__file__),
                                    'test/logfiles/', 'rsinfo_36.log')
        rslog = open(logfile_path, 'rb')
        logfile = LogFile(rslog)
        assert logfile.repl_set == 'replset'
        assert logfile.repl_set_version == '1'
        assert logfile.repl_set_protocol == '1'

    def test_hostname_port(self):
        # mongod
        logfile_path = os.path.join(os.path.dirname(mtools.__file__),
                                    'test/logfiles/', 'mongod_26.log')
        mongod_26 = open(logfile_path, 'rb')

        logfile = LogFile(mongod_26)
        assert logfile.hostname == 'enter.local'
        assert logfile.port == '27019'

        # mongos
        logfile_path = os.path.join(os.path.dirname(mtools.__file__),
                                    'test/logfiles/', 'mongos.log')
        mongos = open(logfile_path, 'rb')

        logfile2 = LogFile(mongos)
        print(logfile2.hostname)
        assert logfile2.hostname == 'jimoleary.local'
        assert logfile2.port == '27017'

    def test_shard_info(self):
        """LogFile: test if sharding info is detected (MongoDB 3.6+) """

        # mongos log
        logfile_path = os.path.join(os.path.dirname(mtools.__file__),
                                    'test/logfiles/','sharding_360_mongos.log')
        mongos_log = open(logfile_path, 'rb')
        logfile = LogFile(mongos_log)
        shards = logfile.shards
        for name, repl_set in shards:
            assert re.match(r'shard\d+', name)
            assert re.match(r'localhost:270\d+', repl_set)

        # config log
        logfile_path = os.path.join(os.path.dirname(mtools.__file__),
                                    'test/logfiles/','sharding_360_CSRS.log')
        csrs_log = open(logfile_path, 'rb')
        logfile = LogFile(csrs_log)
        shards = logfile.shards
        for name, repl_set in shards:
            assert re.match(r'shard\d+', name)
            assert re.match(r'localhost:270\d+', repl_set)

        # shard log
        logfile_path = os.path.join(os.path.dirname(mtools.__file__),
                                    'test/logfiles/','sharding_360_shard.log')
        shard_log = open(logfile_path, 'rb')
        logfile = LogFile(shard_log)
        shards = logfile.shards
        for name, repl_set in shards:
            assert re.match(r'shard\d+', name)
            assert re.match(r'localhost:270\d+', repl_set)

    def test_shard_csrs(self):
        """LogFile: test if sharded cluster CSRS is detected (MongoDB 3.6+) """

        # mongos log
        logfile_path = os.path.join(os.path.dirname(mtools.__file__),
                                    'test/logfiles/','sharding_360_mongos.log')
        mongos_log = open(logfile_path, 'rb')
        logfile = LogFile(mongos_log)
        assert logfile.csrs == ('configRepl', 'localhost:27033')

        # config log
        logfile_path = os.path.join(os.path.dirname(mtools.__file__),
                                    'test/logfiles/','sharding_360_CSRS.log')
        csrs_log = open(logfile_path, 'rb')
        logfile = LogFile(csrs_log)
        assert logfile.csrs == ('configRepl', '[ { _id: 0, host: "localhost:27033",'
                                   ' arbiterOnly: false, buildIndexes: true, hidden: false,'
                                   ' priority: 1.0, tags: {}, slaveDelay: 0, votes: 1 } ]')

        # shard log
        logfile_path = os.path.join(os.path.dirname(mtools.__file__),
                                    'test/logfiles/','sharding_360_shard.log')
        shard_log = open(logfile_path, 'rb')
        logfile = LogFile(shard_log)
        assert logfile.csrs == ('configRepl', 'localhost:27033')

    def test_shard_chunk_migration_from(self):
        """
        LogFile: test if shard chunk migration (from) is detected (MongoDB 3.6+)
        """

        logfile_path = os.path.join(os.path.dirname(mtools.__file__),
                                    'test/logfiles/','sharding_360_shard.log')
        shard_log = open(logfile_path, 'rb')
        logfile = LogFile(shard_log)
        chunk_moved_from = logfile.chunks_moved_from[0]
        assert len(logfile.chunks_moved_from) == 2
        assert isinstance(chunk_moved_from[0], datetime)
        assert chunk_moved_from[1] == "min: { sku: MinKey }, max: { sku: 23153496 }"
        assert chunk_moved_from[2] == "shard02"
        assert chunk_moved_from[3] == "test.products"
        assert ('step 6 of 6', '57') in chunk_moved_from[4]
        assert chunk_moved_from[5] == "success"

    def test_shard_chunk_migration_to(self):
        """
        LogFile: test if shard chunk migration (to) is detected (MongoDB 3.6+)
        """

        logfile_path = os.path.join(os.path.dirname(mtools.__file__),
                                    'test/logfiles/','sharding_360_shard.log')
        shard_log = open(logfile_path, 'rb')
        logfile = LogFile(shard_log)
        chunk_moved_to = logfile.chunks_moved_to[0]

        assert len(logfile.chunks_moved_to) == 1
        assert isinstance(chunk_moved_to[0], datetime)
        assert chunk_moved_to[1] == "min: { sku: MinKey }, max: { sku: 23153496 }"
        assert chunk_moved_to[2] == "Unknown"
        assert chunk_moved_to[3] == "test.products"
        assert ('step 6 of 6', '213') in chunk_moved_to[4]
        assert chunk_moved_to[5] == "success"


def _logfile(text, name='wrapped.log'):
    handle = io.BytesIO(text.encode('utf-8'))
    handle.name = name
    return LogFile(handle)


WRAPPED_UPDATE = (
    '2016-06-14T23:01:00.886Z I WRITE    [conn78263] update mydb.clxn1 '
    'query: { _id: { $eq: "id1" } } update: { $setOnInsert: '
    '{ text: "<?xml version="1.0"?>\n'
    '<xxxxxx type="Axxxxxxxxxxxxxxxxx">\n'
    '  <xxxxxxxx ..." } } keysExamined:1 docsExamined:1 nMatched:1 '
    'nModified:0 numYields:1 129ms\n'
    '2016-06-14T23:01:05.886Z I COMMAND  [conn78357] command mydb.clxn2 '
    'command: find { find: "clxn2", filter: { _id: "id2" } } '
    'keysExamined:1 nreturned:1 113ms\n'
)


def _assert_update_and_find(logfile):
    events = list(logfile)
    assert len(events) == 2
    assert events[0].operation == 'update'
    assert events[0].namespace == 'mydb.clxn1'
    assert events[0].duration == 129
    assert '<xxxxxx' in events[0].line_str
    assert events[1].operation == 'command'
    assert events[1].namespace == 'mydb.clxn2'
    assert events[1].command == 'find'
    assert events[1].duration == 113


def test_wrapped_query_is_one_record():
    """A newline inside a query stays on that operation."""
    logfile = _logfile(WRAPPED_UPDATE)
    assert len(logfile) == 2
    _assert_update_and_find(logfile)


def test_wrapped_query_with_numeric_offset_stays_two_records():
    text = WRAPPED_UPDATE.replace('.886Z', '.886+0100')
    _assert_update_and_find(_logfile(text))


def test_wrapped_query_in_ctime_stays_two_records():
    text = (
        'Tue Jun 14 23:01:00.886 [conn78263] update mydb.clxn1 '
        'query: { _id: { $eq: "id1" } } update: { $setOnInsert: '
        '{ text: "<?xml version="1.0"?>\n'
        '<xxxxxx type="Axxxxxxxxxxxxxxxxx">\n'
        '  <xxxxxxxx ..." } } keysExamined:1 docsExamined:1 129ms\n'
        'Tue Jun 14 23:01:05.886 [conn78357] command mydb.clxn2 '
        'command: find { find: "clxn2", filter: { _id: "id2" } } 113ms\n'
    )
    _assert_update_and_find(_logfile(text))


def test_banner_after_duration_is_not_part_of_the_record():
    text = (
        '2016-06-14T23:01:00.886Z I WRITE    [conn1] update mydb.clxn1 '
        'query: { a: 1.0 } 129ms\n'
        '****************************\n'
        '2016-06-14T23:01:05.886Z I COMMAND  [conn2] command mydb.clxn2 '
        'command: find { find: "clxn2", filter: { _id: "id2" } } 113ms\n'
    )
    logfile = _logfile(text)
    events = list(logfile)
    assert len(events) == 2
    assert events[0].duration == 129
    assert '****' not in events[0].line_str
    assert events[1].duration == 113


def test_continuation_that_ends_with_the_letters_ms_still_joins():
    text = (
        '2016-06-14T23:01:00.886Z I WRITE    [conn1] update mydb.clxn1 '
        'query: { a: 1.0 } update: { text: "items\n'
        'next" } 15ms\n'
        '2016-06-14T23:01:05.886Z I COMMAND  [conn2] command mydb.clxn2 '
        'command: find { find: "clxn2" } 4ms\n'
    )
    events = list(_logfile(text))
    assert len(events) == 2
    assert events[0].duration == 15
    assert 'next' in events[0].line_str
    assert events[1].namespace == 'mydb.clxn2'


def test_orphan_continuation_is_not_glued_to_the_next_record():
    text = (
        '<xxxxxx leftover\n'
        '  tail } } 50ms\n'
        '2016-06-14T23:01:05.886Z I COMMAND  [conn2] command mydb.clxn2 '
        'command: find { find: "clxn2", filter: { _id: "id2" } } 113ms\n'
    )
    events = list(_logfile(text))
    assert len(events) == 1
    assert events[0].namespace == 'mydb.clxn2'
    assert events[0].duration == 113
    assert 'xxxxxx' not in events[0].line_str


def test_wrapped_query_on_stdin_keeps_both_records():
    handle = io.StringIO(WRAPPED_UPDATE)
    handle.name = '<stdin>'
    events = list(LogFile(handle))
    assert len(events) == 2
    assert events[0].duration == 129
    assert events[1].duration == 113
    assert events[0].namespace == 'mydb.clxn1'


def test_structured_logs_stay_one_record_per_line():
    text = (
        '{"t":{"$date":"2022-11-22T00:00:02.933+01:00"},"s":"I",'
        '"c":"COMMAND","id":51803,"ctx":"conn1","msg":"Slow query",'
        '"attr":{"type":"command","ns":"test.foo","command":{"find":"foo"},'
        '"durationMillis":5}}\n'
        '{"t":{"$date":"2022-11-22T00:00:03.000+01:00"},"s":"I",'
        '"c":"COMMAND","id":51803,"ctx":"conn1","msg":"Slow query",'
        '"attr":{"type":"command","ns":"test.bar","command":{"find":"bar"},'
        '"durationMillis":6}}\n'
    )
    events = list(_logfile(text, name='structured.log'))
    assert len(events) == 2
    assert events[0].namespace == 'test.foo'
    assert events[1].namespace == 'test.bar'


def test_single_line_logfile_keeps_its_record_count():
    path = os.path.join(os.path.dirname(mtools.__file__),
                        'test/logfiles/', 'year_rollover.log')
    logfile = LogFile(open(path, 'rb'))
    assert len(logfile) == 1836
    assert sum(1 for _ in logfile) == 1836

