import inspect
import json
import os
import shutil
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
        for observed, expected in zip(cmdset, cmdlisttest):
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
