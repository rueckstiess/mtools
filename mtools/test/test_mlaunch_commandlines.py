import inspect
import json
import os
import shutil
from distutils.version import LooseVersion

from nose.plugins.skip import SkipTest
from nose.tools import raises

from mtools.mlaunch.mlaunch import MLaunchTool


class TestMLaunch(object):

    # Setup & teardown functions

    def setUp(self):
        self.base_dir = 'data_test_mlaunch'
        self.tool = MLaunchTool(test=True)
        self.tool.args = {'verbose': False}
        self.mongod_version = self.tool.getMongoDVersion()

    def tearDown(self):
        self.tool = None
        if os.path.exists(self.base_dir):
            shutil.rmtree(self.base_dir)

    # Helper functions

    @raises(SystemExit)
    def run_tool(self, arg_str):
        """Wrapper to call self.tool.run() with or without auth."""
        # name data directory according to test method name
        caller = inspect.stack()[1][3]
        self.data_dir = os.path.join(self.base_dir, caller)

        # add data directory to arguments for all commands
        arg_str += ' --dir %s' % self.data_dir

        self.tool.run(arg_str)

    def read_config(self):
        """Read the generated mlaunch startup file, get the command lines."""
        fp = open(self.data_dir + '/.mlaunch_startup', 'r')
        cfg = json.load(fp)
        cmd = [cfg['startup_info'][x] for x in cfg['startup_info'].keys()]
        return cfg, cmd

    def cmdlist_filter(self, cmdlist):
        """Filter command lines to contain only [mongod|mongos] --parameter."""
        # NOTE: Command "mongo was intentionally written with a leading quote
        res = map(lambda cmd: set([param for param in cmd.split()
                                   if param.startswith('"mongo') or
                                   param.startswith('--')]),
                  [cmd for cmd in cmdlist if cmd.startswith('"mongod') and
                   '--configsvr' in cmd] +
                  [cmd for cmd in cmdlist if cmd.startswith('"mongod') and
                   '--shardsvr' in cmd] +
                  [cmd for cmd in cmdlist if cmd.startswith('"mongod') and
                   '--configsvr' not in cmd and '--shardsvr' not in cmd] +
                  [cmd for cmd in cmdlist if cmd.startswith('"mongos')]
                  )
        return(res)

    def cmdlist_print(self):
        """Print the generated command lines to console."""
        cfg, cmdlist = self.read_config()
        print('\n')
        print(cmdlist)
        print('\n')
        cmdset = self.cmdlist_filter(cmdlist)
        for cmd in cmdset:
            print(cmd)

    def cmdlist_assert(self, cmdlisttest):
        """Assert helper for command lines."""
        cfg, cmdlist = self.read_config()
        cmdset = [set(x) for x in self.cmdlist_filter(cmdlist)]
        assert len(cmdlist) == len(cmdlisttest)
        for observed, expected in zip(cmdset, cmdlisttest):
            # if mongod, account for some extra observed parameter
            # (e.g. wiredTigerCacheSizeGB)
            if '"mongod"' in expected:
                assert expected.issubset(observed)
                assert expected.intersection(observed) == expected
            # if mongos, expected must match observed
            else:
                assert expected == observed

    def check_csrs(self):
        """Check if CSRS is supported, skip test if unsupported."""
        if LooseVersion(self.mongod_version) < LooseVersion('3.1.0'):
            raise SkipTest('CSRS not supported by MongoDB < 3.1.0')

    def check_sccc(self):
        """Check if SCCC is supported, skip test if unsupported."""
        if LooseVersion(self.mongod_version) >= LooseVersion('3.3.0'):
            raise SkipTest('SCCC not supported by MongoDB >= 3.3.0')

    def check_3_4(self):
        """Check for MongoDB 3.4, skip test otherwise."""
        if LooseVersion(self.mongod_version) < LooseVersion('3.4.0'):
            raise SkipTest('MongoDB version is < 3.4.0')

    def check_3_6(self):
        """Check for MongoDB 3.6, skip test otherwise."""
        if LooseVersion(self.mongod_version) < LooseVersion('3.6.0'):
            raise SkipTest('MongoDB version is < 3.6.0')

    @raises(IOError)
    def raises_ioerror(self):
        """Check for IOError exceptions"""
        self.read_config()

    # Tests

    def test_single(self):
        """mlaunch should start 1 node."""
        self.run_tool('init --single')
        cmdlist = [
            set(['"mongod"', '--dbpath', '--logpath', '--port', '--fork'])
            ]
        self.cmdlist_assert(cmdlist)

    def test_single_storage(self):
        """mlaunch should start 1 node with specified storage."""
        self.run_tool('init --single --storageEngine mmapv1')
        cmdlist = [
            set(['"mongod"', '--dbpath', '--logpath', '--port', '--fork',
                 '--storageEngine'])
            ]
        self.cmdlist_assert(cmdlist)

    def test_replicaset_3(self):
        """mlaunch should start 3 nodes replicaset."""
        self.run_tool('init --replicaset')
        cmdlist = (
            [set(['"mongod"', '--replSet', '--dbpath', '--logpath', '--port',
                  '--fork'])] * 3
            )
        self.cmdlist_assert(cmdlist)

    def test_replicaset_7(self):
        """mlaunch should start 7 nodes replicaset."""
        self.run_tool('init --replicaset --nodes 7')
        cmdlist = (
            [set(['"mongod"', '--replSet', '--dbpath', '--logpath', '--port',
                  '--fork'])] * 7
            )
        self.cmdlist_assert(cmdlist)

    def test_replicaset_6_1(self):
        """mlaunch should start 6 nodes + 1 arbiter replicaset."""
        self.run_tool('init --replicaset --nodes 6 --arbiter')
        cmdlist = (
            [set(['"mongod"', '--replSet', '--dbpath', '--logpath', '--port',
                  '--fork'])] * 7
            )
        self.cmdlist_assert(cmdlist)

    def test_sharded_single(self):
        """mlaunch should start 1 config, 2 single shards 1 mongos."""
        self.run_tool('init --sharded 2 --single')
        if LooseVersion(self.mongod_version) >= LooseVersion('3.6.0'):
            self.raises_ioerror()
        elif LooseVersion(self.mongod_version) >= LooseVersion('3.3.0'):
            cmdlist = (
                [set(['"mongod"', '--dbpath', '--logpath', '--port', '--fork',
                      '--replSet', '--configsvr'])] +
                [set(['"mongod"', '--dbpath', '--logpath', '--port', '--fork',
                      '--shardsvr'])] * 2 +
                [set(['"mongos"', '--logpath', '--port', '--configdb',
                      '--fork'])]
                )
            self.cmdlist_assert(cmdlist)
        else:
            cmdlist = (
                [set(['"mongod"', '--dbpath', '--logpath', '--port', '--fork',
                      '--configsvr'])] +
                [set(['"mongod"', '--dbpath', '--logpath', '--port', '--fork',
                      '--shardsvr'])] * 2 +
                [set(['"mongos"', '--logpath', '--port', '--configdb',
                      '--fork'])]
                )
            self.cmdlist_assert(cmdlist)

    def test_sharded_replicaset_sccc_1(self):
        """
        mlaunch should start 1 config, 2 shards (3 nodes each), 1 mongos
        (SCCC).
        """
        self.check_sccc()
        self.run_tool('init --sharded 2 --replicaset')
        cmdlist = (
            [set(['"mongod"', '--dbpath', '--logpath', '--port', '--fork',
                  '--configsvr'])] +
            [set(['"mongod"', '--replSet', '--dbpath', '--logpath', '--port',
                  '--fork', '--shardsvr'])] * 6 +
            [set(['"mongos"', '--logpath', '--port', '--configdb', '--fork'])]
            )
        self.cmdlist_assert(cmdlist)

    def test_sharded_replicaset_sccc_2(self):
        """
        mlaunch should start 1 config, 2 shards (3 nodes each), 1 mongos
        (SCCC).
        """
        self.check_sccc()
        self.run_tool('init --sharded 2 --replicaset --config 2')
        cmdlist = (
            [set(['"mongod"', '--dbpath', '--logpath', '--port', '--fork',
                  '--configsvr'])] +
            [set(['"mongod"', '--replSet', '--dbpath', '--logpath', '--port',
                  '--fork', '--shardsvr'])] * 6 +
            [set(['"mongos"', '--logpath', '--port', '--configdb', '--fork'])]
            )
        self.cmdlist_assert(cmdlist)

    def test_sharded_replicaset_sccc_3(self):
        """
        mlaunch should start 3 config, 2 shards (3 nodes each), 1 mongos
        (SCCC).
        """
        self.check_sccc()
        self.run_tool('init --sharded 2 --replicaset --config 3')
        cmdlist = (
            [set(['"mongod"', '--dbpath', '--logpath', '--port', '--fork',
                  '--configsvr'])] * 3 +
            [set(['"mongod"', '--replSet', '--dbpath', '--logpath', '--port',
                  '--fork', '--shardsvr'])] * 6 +
            [set(['"mongos"', '--logpath', '--port', '--configdb', '--fork'])]
            )
        self.cmdlist_assert(cmdlist)

    def test_sharded_replicaset_sccc_4(self):
        """
        mlaunch should start 3 config, 2 shards (3 nodes each), 1 mongos
        (SCCC).
        """
        self.check_sccc()
        self.run_tool('init --sharded 2 --replicaset --config 4')
        cmdlist = (
            [set(['"mongod"', '--dbpath', '--logpath', '--port', '--fork',
                  '--configsvr'])] * 3 +
            [set(['"mongod"', '--replSet', '--dbpath', '--logpath', '--port',
                  '--fork', '--shardsvr'])] * 6 +
            [set(['"mongos"', '--logpath', '--port', '--configdb', '--fork'])]
            )
        self.cmdlist_assert(cmdlist)

    def test_sharded_replicaset_csrs_1(self):
        """
        mlaunch should start 1 replicaset config, 2 shards (3 nodes each),
        1 mongos (CSRS).
        """
        self.check_csrs()
        self.run_tool('init --sharded 2 --replicaset --config 1 --csrs')
        cmdlist = (
            [set(['"mongod"', '--replSet', '--dbpath', '--logpath', '--port',
                  '--fork', '--configsvr'])] +
            [set(['"mongod"', '--replSet', '--dbpath', '--logpath', '--port',
                  '--fork', '--shardsvr'])] * 6 +
            [set(['"mongos"', '--logpath', '--port', '--configdb', '--fork'])]
            )
        self.cmdlist_assert(cmdlist)

    def test_sharded_replicaset_csrs_2(self):
        """
        mlaunch should start 2 replicaset config, 2 shards (3 nodes each),
        1 mongos (CSRS).
        """
        self.check_csrs()
        self.run_tool('init --sharded 2 --replicaset --config 2 --csrs')
        cmdlist = (
            [set(['"mongod"', '--replSet', '--dbpath', '--logpath', '--port',
                  '--fork', '--configsvr'])] * 2 +
            [set(['"mongod"', '--replSet', '--dbpath', '--logpath', '--port',
                  '--fork', '--shardsvr'])] * 6 +
            [set(['"mongos"', '--logpath', '--port', '--configdb', '--fork'])]
            )
        self.cmdlist_assert(cmdlist)

    def test_sharded_replicaset_csrs_3(self):
        """
        mlaunch should start 3 replicaset config, 2 shards (3 nodes each),
        1 mongos (CSRS).
        """
        self.check_csrs()
        self.run_tool('init --sharded 2 --replicaset --config 3 --csrs')
        cmdlist = (
            [set(['"mongod"', '--replSet', '--dbpath', '--logpath', '--port',
                  '--fork', '--configsvr'])] * 3 +
            [set(['"mongod"', '--replSet', '--dbpath', '--logpath', '--port',
                  '--fork', '--shardsvr'])] * 6 +
            [set(['"mongos"', '--logpath', '--port', '--configdb', '--fork'])]
            )
        self.cmdlist_assert(cmdlist)

    def test_sharded_replicaset_csrs_4(self):
        """
        mlaunch should start 4 replicaset config, 2 shards (3 nodes each),
        1 mongos (CSRS).
        """
        self.check_csrs()
        self.run_tool('init --sharded 2 --replicaset --config 4 --csrs')
        cmdlist = (
            [set(['"mongod"', '--replSet', '--dbpath', '--logpath', '--port',
                  '--fork', '--configsvr'])] * 4 +
            [set(['"mongod"', '--replSet', '--dbpath', '--logpath', '--port',
                  '--fork', '--shardsvr'])] * 6 +
            [set(['"mongos"', '--logpath', '--port', '--configdb', '--fork'])]
            )
        self.cmdlist_assert(cmdlist)

    def test_sharded_replicaset_csrs_mmapv1(self):
        """mlaunch should not change config server storage engine (CSRS)."""
        self.check_csrs()
        self.run_tool('init --sharded 2 --replicaset --csrs '
                      '--storageEngine mmapv1')
        cmdlist = (
            [set(['"mongod"', '--replSet', '--dbpath', '--logpath', '--port',
                  '--fork', '--configsvr'])] +
            [set(['"mongod"', '--replSet', '--dbpath', '--logpath', '--port',
                  '--fork', '--storageEngine', '--shardsvr'])] * 6 +
            [set(['"mongos"', '--logpath', '--port', '--configdb', '--fork'])]
            )
        self.cmdlist_assert(cmdlist)

    def test_sharded_oplogsize_sccc(self):
        """mlaunch should not pass --oplogSize to config server (SCCC)."""
        self.check_sccc()
        self.run_tool('init --sharded 1 --replicaset --nodes 1 --oplogSize 19')
        cmdlist = (
            [set(['"mongod"', '--port', '--logpath', '--dbpath', '--configsvr',
                  '--fork'])] +
            [set(['"mongod"', '--port', '--replSet', '--shardsvr', '--logpath',
                  '--dbpath', '--oplogSize', '--fork'])] +
            [set(['"mongos"', '--port', '--logpath', '--configdb', '--fork'])]
            )
        self.cmdlist_assert(cmdlist)

    def test_sharded_oplogsize_csrs(self):
        """mlaunch should not pass --oplogSize to config server (CSRS)."""
        self.check_csrs()
        self.run_tool('init --sharded 1 --replicaset --nodes 1 '
                      '--oplogSize 19 --csrs')
        cmdlist = (
            [set(['"mongod"', '--port', '--logpath', '--dbpath', '--configsvr',
                  '--fork', '--replSet'])] +
            [set(['"mongod"', '--port', '--replSet', '--shardsvr', '--logpath',
                  '--dbpath', '--oplogSize', '--fork'])] +
            [set(['"mongos"', '--port', '--logpath', '--configdb', '--fork'])]
            )
        self.cmdlist_assert(cmdlist)

    def test_sharded_two_mongos_sccc(self):
        """mlaunch should start 2 mongos (SCCC)."""
        self.check_sccc()
        self.run_tool('init --sharded 2 --single --config 1 --mongos 2')
        cmdlist = (
            [set(['"mongod"', '--port', '--logpath', '--dbpath', '--configsvr',
                  '--fork'])] +
            [set(['"mongod"', '--port', '--shardsvr', '--logpath', '--dbpath',
                  '--fork'])] * 2 +
            [set(['"mongos"', '--port', '--logpath', '--configdb',
                  '--fork'])] * 2
            )
        self.cmdlist_assert(cmdlist)

    def test_sharded_two_mongos_csrs(self):
        """mlaunch should start 2 mongos (CSRS)."""
        self.check_csrs()
        self.run_tool('init --sharded 2 --single --config 1 --mongos 2 --csrs')
        if LooseVersion(self.mongod_version) >= LooseVersion('3.6.0'):
            self.raises_ioerror()
        else:
            cmdlist = (
                [set(['"mongod"', '--port', '--logpath', '--dbpath',
                      '--configsvr', '--fork', '--replSet'])] +
                [set(['"mongod"', '--port', '--shardsvr', '--logpath',
                      '--dbpath', '--fork'])] * 2 +
                [set(['"mongos"', '--port', '--logpath', '--configdb',
                      '--fork'])] * 2
                )
            self.cmdlist_assert(cmdlist)

    def test_sharded_three_mongos_sccc(self):
        """mlaunch should start 3 mongos (SCCC)."""
        self.check_sccc()
        self.run_tool('init --sharded 2 --replicaset --config 3 --mongos 3')
        cmdlist = (
            [set(['"mongod"', '--port', '--logpath', '--dbpath', '--configsvr',
                  '--fork'])] * 3 +
            [set(['"mongod"', '--port', '--shardsvr', '--logpath', '--dbpath',
                  '--fork', '--replSet'])] * 6 +
            [set(['"mongos"', '--port', '--logpath', '--configdb',
                  '--fork'])] * 3
            )
        self.cmdlist_assert(cmdlist)

    def test_sharded_three_mongos_csrs(self):
        """mlaunch should start 3 mongos (CSRS)."""
        self.check_csrs()
        self.run_tool('init --sharded 2 --replicaset --config 3 '
                      '--mongos 3 --csrs')
        cmdlist = (
            [set(['"mongod"', '--port', '--logpath', '--dbpath', '--configsvr',
                  '--fork', '--replSet'])] * 3 +
            [set(['"mongod"', '--port', '--shardsvr', '--logpath', '--dbpath',
                  '--fork', '--replSet'])] * 6 +
            [set(['"mongos"', '--port', '--logpath', '--configdb',
                  '--fork'])] * 3
            )
        self.cmdlist_assert(cmdlist)

    # 3.4 tests

    def test_default_single_3_4(self):
        """
        mlaunch should create csrs by default -- single node shards (3.4).
        """
        self.check_3_4()
        self.run_tool('init --sharded 2 --single')
        if LooseVersion(self.mongod_version) >= LooseVersion('3.6.0'):
            self.raises_ioerror()
        else:
            cmdlist = (
                [set(['"mongod"', '--port', '--logpath', '--dbpath',
                      '--configsvr', '--fork', '--replSet'])] +
                [set(['"mongod"', '--port', '--logpath', '--dbpath',
                      '--shardsvr', '--fork'])] * 2 +
                [set(['"mongos"', '--port', '--logpath', '--configdb',
                      '--fork'])]
                )
            self.cmdlist_assert(cmdlist)

    def test_default_replicaset_3_4(self):
        """mlaunch should create csrs by default -- replicaset shards (3.4)."""
        self.check_3_4()
        self.run_tool('init --sharded 2 --replicaset')
        cmdlist = (
            [set(['"mongod"', '--port', '--logpath', '--dbpath', '--configsvr',
                  '--fork', '--replSet'])] +
            [set(['"mongod"', '--port', '--logpath', '--dbpath', '--shardsvr',
                  '--fork', '--replSet'])] * 6 +
            [set(['"mongos"', '--port', '--logpath', '--configdb', '--fork'])]
            )
        self.cmdlist_assert(cmdlist)

    def test_default_7_replicaset_3_4(self):
        """
        mlaunch should create csrs by default -- 7 node replicaset
        shards (3.4).
        """
        self.check_3_4()
        self.run_tool('init --sharded 2 --replicaset --nodes 7')
        cmdlist = (
            [set(['"mongod"', '--port', '--logpath', '--dbpath', '--configsvr',
                  '--fork', '--replSet'])] +
            [set(['"mongod"', '--port', '--logpath', '--dbpath', '--shardsvr',
                  '--fork', '--replSet'])] * 14 +
            [set(['"mongos"', '--port', '--logpath', '--configdb', '--fork'])]
            )
        self.cmdlist_assert(cmdlist)

    def test_default_7_replicaset_5_config_3_4(self):
        """
        mlaunch should create csrs by default -- 7 node replicaset shards,
        5 nodes config servers (3.4).
        """
        self.check_3_4()
        self.run_tool('init --sharded 2 --replicaset --nodes 7 --config 5')
        cmdlist = (
            [set(['"mongod"', '--port', '--logpath', '--dbpath', '--configsvr',
                  '--fork', '--replSet'])] * 5 +
            [set(['"mongod"', '--port', '--logpath', '--dbpath', '--shardsvr',
                  '--fork', '--replSet'])] * 14 +
            [set(['"mongos"', '--port', '--logpath', '--configdb', '--fork'])]
            )
        self.cmdlist_assert(cmdlist)

    def test_default_2_replicaset_arb_4_config_2_mongos_3_4(self):
        """
        mlaunch should create csrs by default -- 2 node replicaset shards +
        arbiter, 4 nodes config servers, 2 mongos (3.4).
        """
        self.check_3_4()
        self.run_tool('init --sharded 2 --replicaset --nodes 2 --arbiter '
                      '--config 4 --mongos 2')
        cmdlist = (
            [set(['"mongod"', '--port', '--logpath', '--dbpath', '--configsvr',
                  '--fork', '--replSet'])] * 4 +
            [set(['"mongod"', '--port', '--logpath', '--dbpath', '--shardsvr',
                  '--fork', '--replSet'])] * 4 +
            [set(['"mongod"', '--port', '--logpath', '--dbpath', '--fork',
                  '--replSet'])] * 2 +
            [set(['"mongos"', '--port', '--logpath', '--configdb',
                  '--fork'])] * 2
            )
        self.cmdlist_assert(cmdlist)

    def test_storageengine_3_4(self):
        """
        mlaunch should not pass storageEngine option to config server (3.4).
        """
        self.check_3_4()
        self.run_tool('init --sharded 2 --replicaset --storageEngine mmapv1')
        cmdlist = (
            [set(['"mongod"', '--port', '--logpath', '--dbpath', '--configsvr',
                  '--fork', '--replSet'])] +
            [set(['"mongod"', '--port', '--logpath', '--dbpath', '--shardsvr',
                  '--fork', '--storageEngine'])] * 6 +
            [set(['"mongos"', '--port', '--logpath', '--configdb', '--fork'])]
            )
        self.cmdlist_assert(cmdlist)

    @raises(IOError)
    def test_hostname_3_6(self):
        """
        mlaunch should not start if hostname is specified but not bind_ip.
        """
        self.check_3_6()
        self.run_tool('init --replicaset --hostname this_host')
        self.read_config()
