import inspect
import json
import os
import shutil
import sys
from packaging import version

import pytest

from mtools.mlaunch.mlaunch import MLaunchTool


class TestMLaunch(object):

    # Setup & teardown functions

    def setup_method(self):
        self.base_dir = 'data_test_mlaunch'
        self.tool = MLaunchTool(test=True)
        self.tool.args = {'verbose': False}
        self.mongod_version = self.tool.getMongoDVersion()

    def teardown_method(self):
        self.tool = None
        if os.path.exists(self.base_dir):
            shutil.rmtree(self.base_dir)

    # Helper functions

    @pytest.mark.xfail(raises=SystemExit)
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
        # 8.2+ on macOS omits --fork; the process is detached in Python.
        drop_fork = self.tool._macos_fork_unsupported()
        for observed, expected in zip(cmdset, cmdlisttest):
            if drop_fork:
                expected = set(expected) - {'--fork'}
            # if mongod, account for some extra observed parameter
            # (e.g. wiredTigerCacheSizeGB)
            if '"mongod"' in expected:
                assert expected.issubset(observed)
                assert expected.intersection(observed) == expected
            # if mongos, expected must match observed
            else:
                assert expected == observed

    @pytest.mark.xfail(raises=IOError)
    def raises_ioerror(self):
        """Check for IOError exceptions"""
        self.read_config()

    @pytest.fixture(autouse=True)
    def check_supported_version(self):
        """Skip unless minimum supported version"""
        if version.parse(self.mongod_version) <= version.parse('4.2.0'):
            raise pytest.skip('MongoDB version is older than 4.2.0')

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
        self.run_tool('init --single --storageEngine wiredTiger')
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

    def test_sharded_replicaset_csrs_1(self):
        """
        mlaunch should start 1 replicaset config, 2 shards (3 nodes each),
        1 mongos (CSRS).
        """
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
        self.run_tool('init --sharded 2 --replicaset --config 4 --csrs')
        cmdlist = (
            [set(['"mongod"', '--replSet', '--dbpath', '--logpath', '--port',
                  '--fork', '--configsvr'])] * 4 +
            [set(['"mongod"', '--replSet', '--dbpath', '--logpath', '--port',
                  '--fork', '--shardsvr'])] * 6 +
            [set(['"mongos"', '--logpath', '--port', '--configdb', '--fork'])]
            )
        self.cmdlist_assert(cmdlist)

    def test_sharded_oplogsize_csrs(self):
        """mlaunch should not pass --oplogSize to config server (CSRS)."""
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

    def test_sharded_three_mongos_csrs(self):
        """mlaunch should start 3 mongos (CSRS)."""
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

    def test_default_replicaset_csrs(self):
        """
        mlaunch should create csrs by default -- replicaset shards
        """
        self.run_tool('init --sharded 2 --replicaset')
        cmdlist = (
            [set(['"mongod"', '--port', '--logpath', '--dbpath', '--configsvr',
                  '--fork', '--replSet'])] +
            [set(['"mongod"', '--port', '--logpath', '--dbpath', '--shardsvr',
                  '--fork', '--replSet'])] * 6 +
            [set(['"mongos"', '--port', '--logpath', '--configdb', '--fork'])]
            )
        self.cmdlist_assert(cmdlist)

    def test_default_7_replicaset_csrs(self):
        """
        mlaunch should create csrs by default -- 7 node replicaset shards.
        """
        self.run_tool('init --sharded 2 --replicaset --nodes 7')
        cmdlist = (
            [set(['"mongod"', '--port', '--logpath', '--dbpath', '--configsvr',
                  '--fork', '--replSet'])] +
            [set(['"mongod"', '--port', '--logpath', '--dbpath', '--shardsvr',
                  '--fork', '--replSet'])] * 14 +
            [set(['"mongos"', '--port', '--logpath', '--configdb', '--fork'])]
            )
        self.cmdlist_assert(cmdlist)

    def test_default_7_replicaset_5_config_csrs(self):
        """
        mlaunch should create csrs by default -- 7 node replicaset shards,
        5 nodes config servers.
        """
        self.run_tool('init --sharded 2 --replicaset --nodes 7 --config 5')
        cmdlist = (
            [set(['"mongod"', '--port', '--logpath', '--dbpath', '--configsvr',
                  '--fork', '--replSet'])] * 5 +
            [set(['"mongod"', '--port', '--logpath', '--dbpath', '--shardsvr',
                  '--fork', '--replSet'])] * 14 +
            [set(['"mongos"', '--port', '--logpath', '--configdb', '--fork'])]
            )
        self.cmdlist_assert(cmdlist)

    def test_default_2_replicaset_arb_4_config_2_mongos_csrs(self):
        """
        mlaunch should create csrs by default -- 2 node replicaset shards +
        arbiter, 4 nodes config servers, 2 mongos.
        """
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

    def test_storageengine_csrs(self):
        """
        mlaunch should not pass storageEngine option to config server.
        """
        self.run_tool('init --sharded 2 --replicaset --storageEngine wiredTiger')
        cmdlist = (
            [set(['"mongod"', '--port', '--logpath', '--dbpath', '--configsvr',
                  '--fork', '--replSet'])] +
            [set(['"mongod"', '--port', '--logpath', '--dbpath', '--shardsvr',
                  '--fork', '--storageEngine'])] * 6 +
            [set(['"mongos"', '--port', '--logpath', '--configdb', '--fork'])]
            )
        self.cmdlist_assert(cmdlist)

    @pytest.mark.xfail(raises=SystemExit)
    def test_invalid_hostname(self):
        """
        mlaunch should not start if hostname is specified but not bind_ip.
        """
        self.run_tool('init --replicaset --hostname this_host')
        self.read_config()


class TestMacosForkLaunch(object):
    """Fork handling does not need a running server."""

    def setup_method(self):
        self.tool = MLaunchTool(test=True)
        # Don't probe real binaries; tests set current_version explicitly.
        self.tool._binary_version = lambda binary: None

    @pytest.mark.parametrize('platform,expected', [
        ('darwin', True), ('linux', False), ('win32', False)])
    def test_version_gate(self, monkeypatch, platform, expected):
        monkeypatch.setattr(sys, 'platform', platform)
        self.tool.current_version = '8.0.32'
        assert self.tool._macos_fork_unsupported() is False
        self.tool.current_version = '8.1.9'
        assert self.tool._macos_fork_unsupported() is False
        self.tool.current_version = '8.2.0'
        assert self.tool._macos_fork_unsupported() is expected
        self.tool.current_version = '9.0.2'
        assert self.tool._macos_fork_unsupported() is expected

    def test_version_gate_unparseable(self, monkeypatch):
        monkeypatch.setattr(sys, 'platform', 'darwin')
        for v in (None, '0.0.0', 'garbage', '8'):
            self.tool.current_version = v
            assert self.tool._macos_fork_unsupported() is False

    def test_launch_argv_strips_nohup_and_fork(self):
        self.tool.current_version = '9.0.2'
        cmd = ('nohup "mongod" --dbpath "/data/db" --logpath "/data/mongod.log" '
               '--port 27017 --fork > /dev/null 2>&1 &')
        argv = self.tool._launch_argv(cmd)
        assert argv[0] == 'mongod'
        assert '--fork' not in argv
        assert '--port' in argv
        assert argv[argv.index('--port') + 1] == '27017'
        assert self.tool._get_log_path(cmd) == '/data/mongod.log'
        assert self.tool._needs_python_detach(cmd) is True

    @pytest.mark.parametrize('platform', ['darwin', 'linux'])
    def test_fork_kept_below_82(self, monkeypatch, platform):
        monkeypatch.setattr(sys, 'platform', platform)
        self.tool.current_version = '7.0.14'
        cmd = '"mongod" --dbpath "/data/db" --logpath "/data/mongod.log" --port 27017 --fork'
        argv = self.tool._launch_argv(cmd)
        assert '--fork' in argv
        assert self.tool._needs_python_detach(cmd) is False

    def test_stored_binary_version_wins(self, monkeypatch):
        """Persisted --binarypath 8.2+ binary, PATH reports something else."""
        monkeypatch.setattr(sys, 'platform', 'darwin')
        self.tool.current_version = '0.0.0'
        self.tool._binary_version = (
            lambda binary: '8.2.1' if binary == '/opt/m82/bin/mongod' else None)
        cmd = ('"/opt/m82/bin/mongod" --dbpath "/data/db" '
               '--logpath "/data/mongod.log" --port 27017 --fork')
        assert self.tool._needs_python_detach(cmd) is True
        assert '--fork' not in self.tool._launch_argv(cmd)

    def test_stored_binary_older_keeps_fork(self, monkeypatch):
        monkeypatch.setattr(sys, 'platform', 'darwin')
        self.tool.current_version = '9.0.2'
        self.tool._binary_version = lambda binary: '7.0.14'
        cmd = ('"/opt/m70/bin/mongod" --dbpath "/data/db" '
               '--logpath "/data/mongod.log" --port 27017 --fork')
        assert self.tool._needs_python_detach(cmd) is False
        assert '--fork' in self.tool._launch_argv(cmd)

    def test_spawn_missing_binary_is_clean_exit(self):
        cmd = ('"/nonexistent/mongod" --dbpath "/data/db" '
               '--logpath "/data/mongod.log" --port 27017')
        with pytest.raises(SystemExit) as exc:
            self.tool._spawn_and_wait(cmd, 27017, timeout=1)
        msg = str(exc.value)
        assert '/nonexistent/mongod' in msg
        assert '27017' in msg
