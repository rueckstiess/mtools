import os
from datetime import datetime
import re

from dateutil.tz import tzoffset, tzutc

import mtools
from mtools.util.logevent import LogEvent
from mtools.util.logfile import LogFile


class TestUtilLogFile(object):

    def setup(self):
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

