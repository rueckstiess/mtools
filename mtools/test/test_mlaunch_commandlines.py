import inspect
import json
import os
import shutil
import subprocess
import sys
from packaging import version

import pytest

from mtools.mlaunch.mlaunch import MLaunchTool

_skip_reason = None
if os.getenv("CI") == "true":
    _skip_reason = "Skip starting mongod in CI environment"
elif shutil.which("mongod") is None:
    _skip_reason = "mongod binary not found in PATH"

pytestmark = pytest.mark.skipif(
    _skip_reason is not None,
    reason=_skip_reason or ""
)

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
        """Config servers and shards receive --oplogSize. mongos does not."""
        self.run_tool('init --sharded 1 --replicaset --nodes 1 '
                      '--oplogSize 19 --csrs')
        cmdlist = (
            [set(['"mongod"', '--port', '--logpath', '--dbpath', '--configsvr',
                  '--fork', '--replSet', '--oplogSize'])] +
            [set(['"mongod"', '--port', '--replSet', '--shardsvr', '--logpath',
                  '--dbpath', '--oplogSize', '--fork'])] +
            [set(['"mongos"', '--port', '--logpath', '--configdb', '--fork'])]
            )
        self.cmdlist_assert(cmdlist)
        _, commands = self.read_config()
        for command in commands:
            binary = command.split()[0].strip('"')
            if binary.endswith('mongod') or binary.endswith('mongod.exe'):
                assert '--oplogMinRetentionHours 1' in command
                assert '--oplogSize' in command
            elif binary.endswith('mongos') or binary.endswith('mongos.exe'):
                assert '--oplogSize' not in command
                assert '--oplogMinRetentionHours' not in command

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

    def test_connection_string_single(self):
        self.run_tool('init --single')
        assert self.tool.connection_string() == 'mongodb://localhost:27017'

    def test_connection_string_replicaset(self):
        self.run_tool('init --replicaset --nodes 3 --name testrs')
        expected = ('mongodb://localhost:27017,localhost:27018,'
                    'localhost:27019/?replicaSet=testrs')
        assert self.tool.connection_string() == expected

    def test_connection_string_includes_arbiter(self):
        self.run_tool('init --replicaset --nodes 2 --arbiter --name testrs')
        expected = ('mongodb://localhost:27017,localhost:27018,'
                    'localhost:27019/?replicaSet=testrs')
        assert self.tool.connection_string() == expected

    def test_connection_string_auth_quotes_password(self):
        self.run_tool('init --single --auth --username alice '
                      '--password p@ss --auth-db app')
        expected = 'mongodb://alice:p%40ss@localhost:27017/?authSource=app'
        assert self.tool.connection_string() == expected

    def test_connection_string_auth_without_user(self):
        self.run_tool('init --single --auth --no-initial-user')
        assert self.tool.connection_string() == 'mongodb://localhost:27017'

    def test_connection_string_sharded_mongos(self):
        self.run_tool('init --sharded 2 --replicaset --mongos 2')
        expected = 'mongodb://localhost:27017,localhost:27018'
        assert self.tool.connection_string() == expected

    def test_connection_string_sharded_without_mongos(self):
        self.run_tool('init --sharded 2 --replicaset --nodes 1 --mongos 0')
        uri = self.tool.connection_string()
        assert uri == (
            'mongodb://localhost:27018/?replicaSet=shard01\n'
            'mongodb://localhost:27019/?replicaSet=shard02')

    def test_connection_string_brackets_ipv6(self):
        self.run_tool('init --replicaset --nodes 1 --hostname ::1 '
                      '--bind_ip ::1')
        expected = 'mongodb://[::1]:27017/?replicaSet=replset'
        assert self.tool.connection_string() == expected

    def test_connection_string_require_tls(self):
        self.run_tool('init --single --sslMode requireSSL')
        expected = 'mongodb://localhost:27017/?tls=true'
        assert self.tool.connection_string() == expected

    @pytest.mark.xfail(raises=SystemExit)
    def test_invalid_hostname(self):
        """
        mlaunch should not start if hostname is specified but not bind_ip.
        """
        self.run_tool('init --replicaset --hostname this_host')
        self.read_config()

    def test_default_dial_host_is_localhost(self):
        """A normal launch is dialed at localhost."""
        self.tool.args = {'command': 'init', 'hostname': 'localhost'}
        self.tool.unknown_args = []
        assert self.tool._node_address(27017) == 'localhost:27017'

    def test_hostname_is_used_when_bind_includes_ipv4(self):
        """--hostname is the dial host when an IPv4 bind address exists."""
        self.tool.args = {'command': 'init', 'hostname': 'db.example.com'}
        self.tool.unknown_args = ['--bind_ip', '127.0.0.1,::1']
        assert self.tool._dial_host() == 'db.example.com'
        assert self.tool._node_address(27018) == 'db.example.com:27018'

    def test_ipv6_only_bind_is_dialed_instead_of_localhost(self):
        """--bind_ip ::1 is dialed directly. PyMongo treats localhost as IPv4."""
        self.tool.args = {'command': 'init', 'hostname': 'localhost'}
        self.tool.unknown_args = ['--ipv6', '--bind_ip', '::1']
        assert self.tool._dial_host() == '::1'
        assert self.tool._node_address(27017) == '[::1]:27017'

    def test_bind_ip_equals_form_and_brackets(self):
        """--bind_ip=::1 and a bracketed address both dial that address."""
        self.tool.args = {'command': 'init', 'hostname': 'localhost'}
        self.tool.unknown_args = ['--bind_ip=[::1]']
        assert self.tool._node_address(27017) == '[::1]:27017'

    def test_unspecified_ipv6_bind_dials_loopback(self):
        """--bind_ip :: listens on every IPv6 interface. Dial ::1."""
        self.tool.args = {'command': 'init', 'hostname': 'localhost'}
        self.tool.unknown_args = ['--bind_ip', '::']
        assert self.tool._dial_host() == '::1'

    def test_later_command_uses_stored_bind_ip(self):
        """start/stop keep the bind address stored at init."""
        self.tool.args = {'command': 'start'}
        self.tool.unknown_args = []
        self.tool.loaded_args = {'hostname': 'localhost'}
        self.tool.loaded_unknown_args = ['--bind_ip', '::1']
        assert self.tool._node_address(27017) == '[::1]:27017'

    def test_init_parses_bind_ip_into_the_dial_host(self):
        """The reported init command dials ::1 rather than localhost."""
        self.run_tool('init --single --hostname localhost --bind_ip ::1')
        assert self.tool._node_address(self.tool.args['port']) == '[::1]:27017'


class TestStripKeyFile(object):
    """override_auth must remove the whole --keyFile value."""

    def test_quoted_path_with_spaces_is_removed(self):
        command = (
            '"mongod" --replSet shard01 '
            '--dbpath "/Users/bobbytables 1/tmp/data/shard01/rs1/db" '
            '--logpath "/Users/bobbytables 1/tmp/data/shard01/rs1/mongod.log" '
            '--port 27018 --fork '
            '--keyFile "/Users/bobbytables 1/tmp/data/keyfile" '
            '--shardsvr')
        stripped = MLaunchTool._strip_keyfile(command)

        assert '--keyFile' not in stripped
        assert 'keyfile' not in stripped
        assert '--dbpath "/Users/bobbytables 1/tmp/data/shard01/rs1/db"' in stripped
        assert '--logpath "/Users/bobbytables 1/tmp/data/shard01/rs1/mongod.log"' in stripped
        assert '--shardsvr' in stripped

    def test_bare_and_single_quoted_values_are_removed(self):
        bare = MLaunchTool._strip_keyfile(
            'mongod --keyFile /tmp/keyfile --shardsvr')
        assert '--keyFile' not in bare
        assert '/tmp/keyfile' not in bare
        assert '--shardsvr' in bare

        quoted = MLaunchTool._strip_keyfile(
            "mongod --keyFile '/tmp/my key' --shardsvr")
        assert '--keyFile' not in quoted
        assert '/tmp/my key' not in quoted
        assert '--shardsvr' in quoted


HELP_TEXT = b"""
  --dbpath arg
  --logpath arg
  --port arg
  --fork
  --replSet arg
  --configsvr
  --shardsvr
  --slowms arg
  --configdb arg
  --keyFile arg
  --wiredTigerCacheSizeGB arg
"""


class TestMLaunchOwnedArguments(object):
    """Extra mongod flags that repeat options mlaunch already emits."""

    def _tool(self, monkeypatch):
        tool = MLaunchTool(test=True)
        tool.args = {
            'auth': False,
            'hostname': 'localhost',
            'binarypath': None,
            'sharded': False,
            'replicaset': False,
            'verbose': False,
        }

        def fake_help(binary, argument, fatal=True):
            return HELP_TEXT

        monkeypatch.setattr(
            'mtools.mlaunch.mlaunch.check_mongo_server_output', fake_help)
        return tool

    def test_filter_drops_owned_flags_and_warns_once(self, monkeypatch, capsys):
        tool = self._tool(monkeypatch)
        result = tool._filter_valid_arguments(
            ['--dbpath', 'mongodb/db_files', '--dbpath', 'other',
             '--logpath', 'custom.log', '--port', '27018', '--fork',
             '--replSet', 'other', '--slowms', '1000', '--keyFile', 'secret'],
            'mongod',
            owned={'--dbpath', '--logpath', '--port', '--fork', '--replSet'})

        assert result == '--slowms "1000" --keyFile "secret"'
        output = capsys.readouterr().out
        for flag in ('--dbpath', '--logpath', '--port', '--fork', '--replSet'):
            assert output.count('warning: ignoring %s;' % flag) == 1

    def test_filter_drops_equals_form_without_taking_the_next_flag(
            self, monkeypatch):
        tool = self._tool(monkeypatch)
        result = tool._filter_valid_arguments(
            ['--dbpath=mongodb/db_files', '--fork', '--slowms', '1000'],
            'mongod', owned={'--dbpath', '--fork'})
        assert result == '--slowms "1000"'

    def test_construct_mongod_keeps_a_single_dbpath(self, monkeypatch, capsys):
        tool = self._tool(monkeypatch)
        tool.unknown_args = [
            '--dbpath', 'mongodb/db_files', '--logpath', 'custom.log',
            '--port', '27018', '--fork', '--slowms', '1000',
            '--keyFile', 'secret']
        tool._construct_mongod('/data/db', '/data/mongod.log', 27017)
        command = tool.startup_info['27017']

        assert command.count('--dbpath') == 1
        assert '/data/db' in command
        assert 'mongodb/db_files' not in command
        assert command.count('--logpath') == 1
        assert 'custom.log' not in command
        assert command.count('--port') == 1
        assert '27018' not in command
        assert command.count('--fork') == 1
        assert '--slowms "1000"' in command
        assert '--keyFile "secret"' in command
        assert 'warning: ignoring --dbpath;' in capsys.readouterr().out

    def test_construct_mongod_keeps_its_replset_and_role(self, monkeypatch):
        tool = self._tool(monkeypatch)
        tool.unknown_args = ['--replSet', 'other', '--shardsvr', '--slowms', '1']
        tool._construct_mongod(
            '/data/db', '/data/mongod.log', 27017,
            replset='shard01', extra='--shardsvr')
        command = tool.startup_info['27017']

        assert command.count('--replSet') == 1
        assert 'shard01' in command
        assert 'other' not in command
        assert command.count('--shardsvr') == 1
        assert '--slowms "1"' in command

    def test_construct_mongos_keeps_its_configdb(self, monkeypatch):
        tool = self._tool(monkeypatch)
        tool.unknown_args = [
            '--logpath', 'm.log', '--port', '1',
            '--configdb', 'localhost:27019', '--slowms', '5']
        tool._construct_mongos('/data/mongos.log', 27017, 'localhost:27018')
        command = tool.startup_info['27017']

        assert command.count('--logpath') == 1
        assert 'm.log' not in command
        assert command.count('--port') == 1
        assert command.count('--configdb') == 1
        assert 'localhost:27018' in command
        assert 'localhost:27019' not in command
        assert '--slowms "5"' in command


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

    def test_spawn_retries_while_dbpath_locked(self):
        import subprocess
        calls = []

        def fake_once(command_str, port, timeout=300):
            calls.append(1)
            if len(calls) < 3:
                raise subprocess.CalledProcessError(
                    100, command_str, output='... DBPathInUse: Unable to lock')
            return 'proc'
        self.tool._spawn_once = fake_once
        assert self.tool._spawn_and_wait('mongod', 27017, lock_retry=10) == 'proc'
        assert len(calls) == 3

    def test_spawn_other_errors_not_retried(self):
        import subprocess
        calls = []

        def fake_once(command_str, port, timeout=300):
            calls.append(1)
            raise subprocess.CalledProcessError(48, command_str, output='Address already in use')
        self.tool._spawn_once = fake_once
        with pytest.raises(subprocess.CalledProcessError):
            self.tool._spawn_and_wait('mongod', 27017, lock_retry=10)
        assert len(calls) == 1

    @pytest.mark.skipif(os.name == 'nt', reason='POSIX process capture')
    def test_spawn_reports_console_when_log_is_missing(self, tmp_path):
        script = tmp_path / 'fake-mongod.sh'
        script.write_text(
            '#!/bin/sh\n'
            'echo "Can\'t initialize rotatable log file"\n'
            'echo "BadValue: fork+exec is incompatible with macOS" >&2\n'
            'exit 2\n'
        )
        script.chmod(0o755)
        cmd = '"%s" --port 27017' % script
        with pytest.raises(subprocess.CalledProcessError) as exc:
            self.tool._spawn_and_wait(cmd, 27017, timeout=5)
        assert exc.value.returncode == 2
        assert 'rotatable log file' in exc.value.output
        assert 'fork+exec' in exc.value.output

    def test_retry_ignores_dbpath_in_use_from_earlier_attempt(
            self, tmp_path, monkeypatch):
        import mtools.mlaunch.mlaunch as mlaunch
        log_path = tmp_path / 'mongod.log'
        log_path.write_text('DBPathInUse: previous attempt\n')
        calls = []

        def fake_popen(argv, **kwargs):
            calls.append(1)
            with open(log_path, 'a') as handle:
                handle.write('Fatal: missing data directory\n')
            return _Exited(100)

        monkeypatch.setattr(mlaunch.subprocess, 'Popen', fake_popen)
        cmd = 'mongod --logpath "%s" --port 27017' % log_path
        with pytest.raises(subprocess.CalledProcessError) as exc:
            self.tool._spawn_and_wait(cmd, 27017, lock_retry=1)
        assert len(calls) == 1
        assert 'missing data directory' in exc.value.output
        assert 'previous attempt' not in exc.value.output

    def test_retry_sees_new_dbpath_in_use_after_old_backtrace(
            self, tmp_path, monkeypatch):
        import mtools.mlaunch.mlaunch as mlaunch
        log_path = tmp_path / 'mongod.log'
        log_path.write_text('----- BEGIN BACKTRACE -----\nold frame\n')
        calls = []

        def fake_popen(argv, **kwargs):
            calls.append(1)
            with open(log_path, 'a') as handle:
                handle.write('DBPathInUse: Unable to lock\n')
            if len(calls) >= 2:
                return _Exited(None)
            return _Exited(100)

        monkeypatch.setattr(mlaunch.subprocess, 'Popen', fake_popen)
        monkeypatch.setattr(
            self.tool, '_process_is_listening', lambda proc, port: True)
        cmd = 'mongod --logpath "%s" --port 27017' % log_path
        self.tool._spawn_and_wait(cmd, 27017, lock_retry=5)
        assert len(calls) == 2

    def test_retry_sees_dbpath_in_use_when_log_shrinks(
            self, tmp_path, monkeypatch):
        import mtools.mlaunch.mlaunch as mlaunch
        log_path = tmp_path / 'mongod.log'
        log_path.write_text(('x' * 300) + '\nDBPathInUse: old\n')
        calls = []

        def fake_popen(argv, **kwargs):
            calls.append(1)
            # Same inode, shorter file: mongod truncated the log.
            with open(log_path, 'w') as handle:
                handle.write('DBPathInUse: this attempt\n')
            if len(calls) >= 2:
                return _Exited(None)
            return _Exited(100)

        monkeypatch.setattr(mlaunch.subprocess, 'Popen', fake_popen)
        monkeypatch.setattr(
            self.tool, '_process_is_listening', lambda proc, port: True)
        cmd = 'mongod --logpath "%s" --port 27017' % log_path
        self.tool._spawn_and_wait(cmd, 27017, lock_retry=5)
        assert len(calls) == 2

    def test_retry_sees_dbpath_in_use_when_log_is_replaced(
            self, tmp_path, monkeypatch):
        import mtools.mlaunch.mlaunch as mlaunch
        log_path = tmp_path / 'mongod.log'
        log_path.write_text(('x' * 300) + '\nDBPathInUse: old\n')
        calls = []

        def fake_popen(argv, **kwargs):
            calls.append(1)
            os.remove(log_path)
            log_path.write_text('DBPathInUse: replaced file\n')
            if len(calls) >= 2:
                return _Exited(None)
            return _Exited(100)

        monkeypatch.setattr(mlaunch.subprocess, 'Popen', fake_popen)
        monkeypatch.setattr(
            self.tool, '_process_is_listening', lambda proc, port: True)
        cmd = 'mongod --logpath "%s" --port 27017' % log_path
        self.tool._spawn_and_wait(cmd, 27017, lock_retry=5)
        assert len(calls) == 2


class _Exited(object):
    def __init__(self, code):
        self.pid = 4242
        self._code = code

    def poll(self):
        return self._code


class TestMLaunchStartWhenRunning(object):
    """start() when the environment is already up. No mongod is launched."""

    def setup_method(self):
        self.tool = MLaunchTool(test=True)
        self.tool.discover = lambda: None

    def test_start_succeeds_when_no_nodes_are_down(self, capsys):
        self.tool.startup_info = {'27017': 'mongod'}
        self.tool.args = {'binarypath': None}
        self.tool.unknown_args = []
        self.tool._get_ports_from_args = lambda args, extra_tag: []

        self.tool.start()

        assert 'all nodes already running.' in capsys.readouterr().out

    def test_start_still_errors_for_partial_old_protocol(self):
        self.tool.startup_info = {}

        def get_tagged(tags):
            if tags == ['all']:
                return {27017}
            return set()

        self.tool.get_tagged = get_tagged
        with pytest.raises(SystemExit) as exc:
            self.tool.start()
        assert 'older version of mlaunch' in str(exc.value)


def _uri_for(**args):
    """Build a URI from parsed args without starting mongod."""
    from mtools.mlaunch.mlaunch import MLaunchTool
    tool = MLaunchTool.__new__(MLaunchTool)
    tool.args = args
    return tool._mongodb_uri(['localhost:27017'], [])


def test_uri_userinfo_encodes_spaces_as_percent_20():
    uri = _uri_for(auth=True, username='al ice', password='p ss+',
                   auth_db='admin')
    assert uri == ('mongodb://al%20ice:p%20ss%2B@localhost:27017/'
                   '?authSource=admin')


def test_uri_x509_user_has_no_password():
    uri = _uri_for(auth=True, username='CN=client,O=Org', password='x',
                   auth_db='$external')
    assert uri == ('mongodb://CN%3Dclient%2CO%3DOrg@localhost:27017/'
                   '?authMechanism=MONGODB-X509&authSource=%24external')


def test_uri_tls_includes_ca_and_client_certificate():
    uri = _uri_for(tlsMode='requireTLS', tlsCAFile='/certs/ca.pem',
                   tlsClientCertificateKeyFile='/certs/client.pem')
    assert uri == ('mongodb://localhost:27017/?tls=true'
                   '&tlsCAFile=%2Fcerts%2Fca.pem'
                   '&tlsCertificateKeyFile=%2Fcerts%2Fclient.pem')
