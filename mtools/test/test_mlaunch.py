import inspect
import json
import os
import shutil
import sys
import time
import unittest

from bson import SON

import pytest
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure

from mtools.mlaunch.mlaunch import MLaunchTool

pytestmark = pytest.mark.skip("skip all mlaunch tests for now")

class TestMLaunch(object):
    """
    This class tests functionality around the mlaunch tool. It has some
    additional methods that are helpful for the tests, as well as a setup
    and teardown method for all tests.

    Don't call tests from other tests. This won't work as each test gets
    its own data directory (for debugging).
    """

    port = 33333
    base_dir = 'data_test_mlaunch'

    def __init__(self):
        """Constructor."""
        self.use_auth = False
        self.data_dir = ''

    def setup_method(self):
        """Start up method to create mlaunch tool and find free port."""
        self.tool = MLaunchTool(test=True)

        # if the test data path exists, remove it
        if os.path.exists(self.base_dir):
            shutil.rmtree(self.base_dir)

    def teardown_method(self):
        """Tear down method after each test, removes data directory."""

        # kill all running processes
        self.tool.discover()

        ports = self.tool.get_tagged(['all', 'running'])
        processes = self.tool._get_processes().values()
        for p in processes:
            p.terminate()
            p.wait(10)

        self.tool.wait_for(ports, to_start=False)

        # quick sleep to avoid spurious test failures
        time.sleep(1)

        # if the test data path exists, remove it
        if os.path.exists(self.base_dir):
            shutil.rmtree(self.base_dir)

    def run_tool(self, arg_str):
        """Wrapper to call self.tool.run() with or without auth."""
        # name data directory according to test method name
        caller = inspect.stack()[1][3]
        self.data_dir = os.path.join(self.base_dir, caller)

        # add data directory to arguments for all commands
        arg_str += ' --dir %s' % self.data_dir

        if arg_str.startswith('init') or arg_str.startswith('--'):
            # add --port and --nojournal to init calls
            arg_str += ' --port %i --nojournal --smallfiles' % self.port

            if self.use_auth:
                # add --auth to init calls if flag is set
                arg_str += ' --auth'

        self.tool.run(arg_str)

    # -- tests below ---

    @pytest.mark.xfail(raises=ConnectionFailure)
    def test_test(self):
        """TestMLaunch setup and teardown test."""

        # test that data dir does not exist
        assert not os.path.exists(self.data_dir)

        # start mongo process on free test port
        self.run_tool("init --single")

        # call teardown method within this test
        self.teardown()

        # test that data dir does not exist anymore
        assert not os.path.exists(self.data_dir)

        # test that mongod is not running on this port anymore
        # (raises ConnectionFailure)
        mc = MongoClient('localhost:%i' % self.port,
                         serverSelectionTimeoutMS=100).server_info()
        print(mc['version'])

    def test_argv_run(self):
        """
        mlaunch: test true command line arguments, instead of passing
        into tool.run().
        """

        # make command line arguments through sys.argv
        sys.argv = ['mlaunch', 'init', '--single', '--dir', self.base_dir,
                    '--port', str(self.port), '--nojournal']

        self.tool.run()
        assert self.tool.is_running(self.port)

    def test_init_default(self):
        """mlaunch: test that 'init' command can be omitted, is default. """

        # make command line arguments through sys.argv
        sys.argv = ['mlaunch', '--single', '--dir', self.base_dir,
                    '--port', str(self.port), '--nojournal']

        self.tool.run()
        assert self.tool.is_running(self.port)

    def test_init_default_arguments(self):
        """
        mlaunch: test that 'init' command is default, even when specifying
        arguments to run().
        """

        self.run_tool("--single")
        assert self.tool.is_running(self.port)

    def test_single(self):
        """mlaunch: start stand-alone server and tear down again."""

        # start mongo process on free test port
        self.run_tool("init --single")

        # make sure node is running
        assert self.tool.is_running(self.port)

        # check if data directory and logfile exist
        assert os.path.exists(os.path.join(self.data_dir, 'db'))
        assert os.path.isfile(os.path.join(self.data_dir, 'mongod.log'))

        # check that the tags are set correctly: 'single', 'mongod',
        # 'running', <port>
        assert set(self.tool.get_tags_of_port(self.port)) == set(['running',
                                                                  'mongod',
                                                                  'all',
                                                                  'single',
                                                                  str(self.
                                                                      port)])

    def test_replicaset_conf(self):
        """Start replica set of 2 nodes + arbiter and compare rs.conf()."""

        # start mongo process on free test port
        self.run_tool("init --replicaset --nodes 2 --arbiter")

        # check if data directories exist
        assert os.path.exists(os.path.join(self.data_dir, 'replset'))
        assert os.path.exists(os.path.join(self.data_dir, 'replset/rs1'))
        assert os.path.exists(os.path.join(self.data_dir, 'replset/rs2'))
        assert os.path.exists(os.path.join(self.data_dir, 'replset/arb'))

        # create mongo client for the next tests
        mc = MongoClient('localhost:%i' % self.port)

        # get rs.conf() and check for 3 members, exactly one is arbiter
        conf = mc['local']['system.replset'].find_one()
        assert len(conf['members']) == 3
        assert sum(1 for memb in conf['members']
                   if 'arbiterOnly' in memb and memb['arbiterOnly']) == 1

    @pytest.mark.timeout(60)
    @pytest.mark.slow
    def test_replicaset_ismaster(self):
        """Start replica set and verify that first node becomes primary."""

        # start mongo process on free test port
        self.run_tool("init --replicaset")

        # wait for primary
        assert self.tool._wait_for_primary()

        # insert a document and wait to replicate to 2 secondaries
        # (10 sec timeout)
        mc = MongoClient('localhost:%i' % self.port)
        mc.test.smokeWait.insert_one({}, w=2, wtimeout=10 * 60 * 1000)

    @unittest.skip('incompatible with 3.4 CSRS')
    def test_sharded_status(self):
        """Start cluster with 2 shards of single nodes, 1 config server."""

        # start mongo process on free test port
        self.run_tool("init --sharded 2 --single")

        # check if data directories and logfile exist
        assert os.path.exists(os.path.join(self.data_dir, 'shard01/db'))
        assert os.path.exists(os.path.join(self.data_dir, 'shard02/db'))
        assert os.path.exists(os.path.join(self.data_dir, 'config/db'))
        assert os.path.isfile(os.path.join(self.data_dir, 'mongos.log'))

        # create mongo client
        mc = MongoClient('localhost:%i' % (self.port))

        # check for 2 shards and 1 mongos
        assert mc['config']['shards'].count_documents({}) == 2
        assert mc['config']['mongos'].count_documents({}) == 1

    def helper_output_has_line_with(self, keywords, output):
        """Check if output contains a line where all keywords are present."""
        return len(filter(None, [all([kw in line for kw in keywords])
                                 for line in output]))

    @unittest.skip('incompatible with 3.4 CSRS')
    def test_verbose_sharded(self):
        """Test verbose output when creating sharded cluster."""

        self.run_tool("init --sharded 2 --replicaset --config 3 "
                      "--mongos 2 --verbose")

        # capture stdout
        output = sys.stdout.getvalue().splitlines()

        keywords = ('rs1', 'rs2', 'rs3', 'shard01', 'shard02', 'config1',
                    'config2', 'config3')

        # creating directory
        for keyword in keywords:
            # make sure every directory creation was announced to stdout
            assert self.helper_output_has_line_with(['creating directory',
                                                     keyword, 'db'], output)

        assert self.helper_output_has_line_with(['creating directory',
                                                 'mongos'], output)

        # launching nodes
        for keyword in keywords:
            assert self.helper_output_has_line_with(['launching', keyword,
                                                     '--port', '--logpath',
                                                     '--dbpath'], output)

        # mongos
        assert self.helper_output_has_line_with(['launching', 'mongos',
                                                 '--port', '--logpath',
                                                 str(self.port)], output)
        assert self.helper_output_has_line_with(['launching', 'mongos',
                                                 '--port', '--logpath',
                                                 str(self.port + 1)], output)

        # some fixed outputs
        assert self.helper_output_has_line_with(['waiting for nodes to '
                                                 'start'], output)
        assert self.helper_output_has_line_with(['adding shards. can take up '
                                                 'to 30 seconds'], output)
        assert self.helper_output_has_line_with(['writing .mlaunch_startup '
                                                 'file'], output)
        assert self.helper_output_has_line_with(['done'], output)

        # replica sets initialized, shard added
        for keyword in ('shard01', 'shard02'):
            assert self.helper_output_has_line_with(['replica set', keyword,
                                                     'initialized'], output)
            assert self.helper_output_has_line_with(['shard', keyword,
                                                     'added successfully'],
                                                    output)

    def test_shard_names(self):
        """mlaunch: test if sharded cluster with explicit shard names works."""

        # start mongo process on free test port
        self.run_tool("init --sharded tic tac toe --replicaset")

        # create mongo client
        mc = MongoClient('localhost:%i' % (self.port))

        # check that shard names match
        shard_names = set(doc['_id'] for doc in mc['config']['shards'].find())
        assert shard_names == set(['tic', 'tac', 'toe'])

    def test_startup_file(self):
        """mlaunch: create .mlaunch_startup file in data path."""

        # Also tests utf-8 to byte conversion and json import

        self.run_tool("init --single -v")

        # check if the startup file exists
        startup_file = os.path.join(self.data_dir, '.mlaunch_startup')
        assert os.path.isfile(startup_file)

        # compare content of startup file with tool.args
        file_contents = json.load(open(startup_file, 'rb'))
        assert file_contents['parsed_args'] == self.tool.args
        assert file_contents['unknown_args'] == self.tool.unknown_args

    def test_single_mongos_explicit(self):
        """
        mlaunch: test if single mongos is running on start port and creates
        <datadir>/mongos.log.
        """

        # start 2 shards, 1 config server, 1 mongos
        self.run_tool("init --sharded 2 --single --config 1 --mongos 1")

        # check if mongos log files exist on correct ports
        assert os.path.exists(os.path.join(self.data_dir, 'mongos.log'))

        # check for correct port
        assert self.tool.get_tagged('mongos') == set([self.port])

    def test_single_mongos(self):
        """
        mlaunch: test if multiple mongos use separate log files in 'mongos'
        subdir.
        """

        # start 2 shards, 1 config server, 2 mongos
        self.run_tool("init --sharded 2 --single --config 1 --mongos 1")

        # check that 2 mongos are running
        assert len(self.tool.get_tagged(['mongos', 'running'])) == 1

    def test_multiple_mongos(self):
        """
        mlaunch: test if multiple mongos use separate log files in 'mongos'
        subdir.
        """

        # start 2 shards, 1 config server, 2 mongos
        self.run_tool("init --sharded 2 --single --config 1 --mongos 2")

        # this also tests that mongos are started at the beginning of the
        # port range
        assert os.path.exists(os.path.join(self.data_dir, 'mongos',
                                           'mongos_%i.log' % (self.port)))
        assert os.path.exists(os.path.join(self.data_dir, 'mongos',
                                           'mongos_%i.log' % (self.port + 1)))

        # check that 2 mongos are running
        assert len(self.tool.get_tagged(['mongos', 'running'])) == 2

    def test_filter_valid_arguments(self):
        """Check arguments unknown to mlaunch against mongos and mongod."""

        # filter against mongod
        result = self.tool._filter_valid_arguments("--slowms 500 -vvv "
                                                   "--configdb localhost:27017"
                                                   " --foobar".split(),
                                                   "mongod")
        assert result == "--slowms 500 -vvv"

        # filter against mongos
        result = self.tool._filter_valid_arguments("--slowms 500 -vvv "
                                                   "--configdb localhost:27017"
                                                   " --foobar".split(),
                                                   "mongos")
        assert result == "-vvv --configdb localhost:27017"

    def test_large_replicaset_arbiter(self):
        """mlaunch: start large replica set of 7 nodes with arbiter."""

        # start mongo process on free test port
        # (don't need journal for this test)
        self.run_tool("init --replicaset --nodes 6 --arbiter")

        # check if data directories exist
        assert os.path.exists(os.path.join(self.data_dir, 'replset'))
        assert os.path.exists(os.path.join(self.data_dir, 'replset/rs1'))
        assert os.path.exists(os.path.join(self.data_dir, 'replset/rs2'))
        assert os.path.exists(os.path.join(self.data_dir, 'replset/rs3'))
        assert os.path.exists(os.path.join(self.data_dir, 'replset/rs4'))
        assert os.path.exists(os.path.join(self.data_dir, 'replset/rs5'))
        assert os.path.exists(os.path.join(self.data_dir, 'replset/rs6'))
        assert os.path.exists(os.path.join(self.data_dir, 'replset/arb'))

        # create mongo client for the next tests
        mc = MongoClient('localhost:%i' % self.port)

        # get rs.conf() and check for 7 members, exactly one arbiter
        conf = mc['local']['system.replset'].find_one()
        assert len(conf['members']) == 7
        assert sum(1 for memb in conf['members']
                   if 'arbiterOnly' in memb and memb['arbiterOnly']) == 1

        # check that 7 nodes are discovered
        assert len(self.tool.get_tagged('all')) == 7

    def test_large_replicaset_noarbiter(self):
        """mlaunch: start large replica set of 7 nodes without arbiter."""

        # start mongo process on free test port
        # (don't need journal for this test)
        self.run_tool("init --replicaset --nodes 7")

        # check if data directories exist
        assert os.path.exists(os.path.join(self.data_dir, 'replset'))
        assert os.path.exists(os.path.join(self.data_dir, 'replset/rs1'))
        assert os.path.exists(os.path.join(self.data_dir, 'replset/rs2'))
        assert os.path.exists(os.path.join(self.data_dir, 'replset/rs3'))
        assert os.path.exists(os.path.join(self.data_dir, 'replset/rs4'))
        assert os.path.exists(os.path.join(self.data_dir, 'replset/rs5'))
        assert os.path.exists(os.path.join(self.data_dir, 'replset/rs6'))
        assert os.path.exists(os.path.join(self.data_dir, 'replset/rs7'))

        # create mongo client for the next tests
        mc = MongoClient('localhost:%i' % self.port)

        # get rs.conf() and check for 7 members, no arbiters
        conf = mc['local']['system.replset'].find_one()
        assert len(conf['members']) == 7
        assert sum(1 for memb in conf['members']
                   if 'arbiterOnly' in memb and memb['arbiterOnly']) == 0

    def test_stop(self):
        """mlaunch: test stopping all nodes """

        self.run_tool("init --replicaset")
        self.run_tool("stop")

        # make sure all nodes are down
        nodes = self.tool.get_tagged('all')
        assert all(not self.tool.is_running(node) for node in nodes)

    def test_kill_default(self):
        """mlaunch: test killing all nodes with default signal."""

        # start sharded cluster and kill with default signal (15)
        self.run_tool("init --sharded 2 --single")
        self.run_tool("kill")

        # make sure all nodes are down
        nodes = self.tool.get_tagged('all')
        assert all(not self.tool.is_running(node) for node in nodes)

    def test_kill_sigterm(self):
        """mlaunch: test killing all nodes with SIGTERM."""

        # start nodes again, this time, kill with string "SIGTERM"
        self.run_tool("init --sharded 2 --single")
        self.run_tool("kill --signal SIGTERM")

        # make sure all nodes are down
        nodes = self.tool.get_tagged('all')
        assert all(not self.tool.is_running(node) for node in nodes)

    def test_kill_sigkill(self):
        """mlaunch: test killing all nodes with SIGKILL."""

        # start nodes again, this time, kill with signal 9 (SIGKILL)
        self.run_tool("init --sharded 2 --single")
        self.run_tool("kill --signal 9")

        # make sure all nodes are down
        nodes = self.tool.get_tagged('all')
        assert all(not self.tool.is_running(node) for node in nodes)

    def test_stop_start(self):
        """mlaunch: test stop and then re-starting nodes."""

        # start mongo process on free test port
        self.run_tool("init --replicaset")
        self.run_tool("stop")
        time.sleep(2)
        self.run_tool("start")

        # make sure all nodes are running
        nodes = self.tool.get_tagged('all')
        assert all(self.tool.is_running(node) for node in nodes)

    @unittest.skip('tags implementation not up to date')
    @pytest.mark.timeout(180)
    @pytest.mark.slow
    def test_kill_partial(self):
        """Test killing and restarting tagged groups on different tags."""

        # key is tag for command line, value is tag for get_tagged
        tags = ['shard01', 'shard 1', 'mongos', 'config 1', str(self.port)]

        # start large cluster
        self.run_tool("init --sharded 2 --replicaset --config 3 --mongos 3")

        # make sure all nodes are running
        nodes = self.tool.get_tagged('all')
        assert all(self.tool.is_running(node) for node in nodes)

        # go through all tags, stop nodes for each tag, confirm only
        # the tagged ones are down, start again
        for tag in tags:
            print("--------- %s" % tag)
            self.run_tool("kill %s" % tag)
            assert self.tool.get_tagged('down') == self.tool.get_tagged(tag)
            time.sleep(1)

            # short sleep, because travis seems to be sensitive and sometimes
            # fails otherwise
            self.run_tool("start")
            assert len(self.tool.get_tagged('down')) == 0
            time.sleep(1)

        # make sure primaries are running again
        # (we just failed them over above).
        # while True is ok, because test times out after some time
        while True:
            primaries = self.tool.get_tagged('primary')
            if len(primaries) == 2:
                break
            time.sleep(1)
            self.tool.discover()

        # test for primary, but as nodes lose their tags, needs to be manual
        self.run_tool("kill primary")
        assert len(self.tool.get_tagged('down')) == 2

    def test_restart_with_unkown_args(self):
        """mlaunch: test start command with extra unknown arguments."""

        # init environment (sharded, single shards ok)
        self.run_tool("init --single")

        # get verbosity of mongod, assert it is 0
        mc = MongoClient(port=self.port)
        loglevel = mc.admin.command(SON([('getParameter', 1), ('logLevel',
                                                               1)]))
        assert loglevel[u'logLevel'] == 0

        # stop and start nodes but pass in unknown_args
        self.run_tool("stop")

        # short sleep, because travis seems to be sensitive and
        # sometimes fails otherwise
        time.sleep(1)

        self.run_tool("start -vv")

        # compare that the nodes are restarted with the new unknown_args,
        # assert loglevel is now 2
        mc = MongoClient(port=self.port)
        loglevel = mc.admin.command(SON([('getParameter', 1), ('logLevel',
                                                               1)]))
        assert loglevel[u'logLevel'] == 2

        # stop and start nodes without unknown args again
        self.run_tool("stop")

        # short sleep, because travis seems to be sensitive and
        # sometimes fails otherwise
        time.sleep(1)

        self.run_tool("start")

        # compare that the nodes are restarted with the previous loglevel
        mc = MongoClient(port=self.port)
        loglevel = mc.admin.command(SON([('getParameter', 1), ('logLevel',
                                                               1)]))
        assert loglevel[u'logLevel'] == 0

    @unittest.skip('currently not a useful test')
    def test_start_stop_single_repeatedly(self):
        """Test starting and stopping single node in short succession."""

        # repeatedly start single node
        self.run_tool("init --single")

        for i in range(10):
            self.run_tool("stop")

            # short sleep, because travis seems to be sensitive and
            # sometimes fails otherwise
            time.sleep(1)

            self.run_tool("start")

    @pytest.mark.xfail(raises=SystemExit)
    def test_init_init_replicaset(self):
        """mlaunch: test calling init a second time on the replica set."""

        # init a replica set
        self.run_tool("init --replicaset")

        # now stop and init again, this should work if everything is
        # stopped and identical environment
        self.run_tool("stop")
        self.run_tool("init --replicaset")

        # but another init should fail with a SystemExit
        self.run_tool("init --replicaset")

    @unittest.skip('currently not a useful test')
    def test_start_stop_replicaset_repeatedly(self):
        """Test starting and stopping replica set in short succession."""

        # repeatedly start replicaset nodes
        self.run_tool("init --replicaset")

        for i in range(10):
            self.run_tool("stop")

            # short sleep, because travis seems to be sensitive and
            # sometimes fails otherwise
            time.sleep(1)

            self.run_tool("start")

    @pytest.mark.slow
    @pytest.mark.auth
    def test_repeat_all_with_auth(self):
        """Repeates all tests in this class (excluding itself) with auth."""
        tests = [t for t in inspect.getmembers(self,
                                               predicate=inspect.ismethod)
                 if t[0].startswith('test_')]

        self.use_auth = True

        for name, method in tests:
            # don't call any tests that use auth already (tagged with
            # 'auth' attribute), including this method
            if hasattr(method, 'auth'):
                continue

            setattr(method.__func__, 'description',
                    method.__doc__.strip() + ', with auth.')
            yield (method,)

        self.use_auth = False

    @pytest.mark.auth
    def test_replicaset_with_name(self):
        """mlaunch: test calling init on the replica set with given name."""

        self.run_tool("init --replicaset --name testrs")

        # create mongo client for the next tests
        mc = MongoClient('localhost:%i' % self.port)

        # get rs.conf() and check for its name
        conf = mc['local']['system.replset'].find_one()
        assert conf['_id'] == 'testrs'

    # TODO
    # - test functionality of --binarypath, --verbose

    # All tests that use auth need to be decorated with @pytest.mark.auth

    def helper_adding_default_user(self, environment):
        """Helper function for the next test: test_adding_default_user()."""

        self.run_tool("init %s --auth" % environment)

        # connect and authenticate with default credentials:
        # user / password on admin database
        mc = MongoClient('localhost:%i' % self.port)
        mc.admin.authenticate('user', password='password')

        # check if the user roles are correctly set to the default roles
        user = mc.admin.system.users.find_one()
        assert(set([x['role']
                    for x in user['roles']]) == set(self.tool.
                                                    _default_auth_roles))

    @pytest.mark.auth
    def test_adding_default_user(self):
        envs = (
            "--single",
            "--replicaset",
            "--sharded 2 --single",
            "--sharded 2 --replicaset",
            "--sharded 2 --single --config 3"
            )

        for env in envs:
            method = self.helper_adding_default_user
            setattr(method.__func__, 'description', method.__doc__.strip() +
                    ', with ' + env)
            yield (method, env)

    @pytest.mark.auth
    def test_adding_default_user_no_mongos(self):
        """mlaunch: test that even with --mongos 0 there is a user created."""

        self.run_tool("init --sharded 2 --single --mongos 0 --auth")

        # connect to config server instead to check for credentials (no mongos)
        ports = list(self.tool.get_tagged('config'))
        mc = MongoClient('localhost:%i' % ports[0])
        mc.admin.authenticate('user', password='password')

        # check if the user roles are correctly set to the default roles
        user = mc.admin.system.users.find_one()
        assert(set([x['role']
                    for x in user['roles']]) == set(self.tool.
                                                    _default_auth_roles))

    @pytest.mark.auth
    def test_adding_custom_user(self):
        """mlaunch: test custom username and password and custom roles."""

        self.run_tool("init --single --auth --username corben "
                      "--password fitzroy --auth-roles dbAdminAnyDatabase "
                      "readWriteAnyDatabase userAdminAnyDatabase")

        # connect and authenticate with default credentials:
        # user / password on admin database
        mc = MongoClient('localhost:%i' % self.port)
        mc.admin.authenticate('corben', password='fitzroy')

        # check if the user roles are correctly set to the specified roles
        user = mc.admin.system.users.find_one()
        print(user)
        assert(set([x['role']
                    for x in user['roles']]) == set(["dbAdminAnyDatabase",
                                                     "readWriteAnyDatabase",
                                                     "userAdminAnyDatabase"]))
        assert user['user'] == 'corben'

    def test_existing_environment(self):
        """mlaunch: test warning for overwriting an existing environment."""

        self.run_tool("init --single")
        self.run_tool("stop")
        try:
            self.run_tool("init --replicaset")
        except SystemExit as e:
            assert 'different environment already exists' in e.message

    @unittest.skip('mlaunch protocol upgrade is not needed at this point')
    def test_upgrade_v1_to_v2(self):
        """mlaunch: test upgrade from protocol version 1 to 2."""

        startup_options = {"name": "replset", "replicaset": True,
                           "dir": "./data", "authentication": False,
                           "single": False, "arbiter": False, "mongos": 1,
                           "binarypath": None, "sharded": None, "nodes": 3,
                           "config": 1, "port": 33333, "restart": False,
                           "verbose": False}

        # create directory
        self.run_tool("init --replicaset")
        self.run_tool("stop")

        # replace startup options
        with open(os.path.join(self.base_dir, 'test_upgrade_v1_to_v2',
                               '.mlaunch_startup'), 'w') as f:
            json.dump(startup_options, f, -1)

        # now start with old config and check if upgrade worked
        self.run_tool("start")
        with open(os.path.join(self.base_dir, 'test_upgrade_v1_to_v2',
                               '.mlaunch_startup'), 'rb') as f:
            startup_options = json.load(f)
            assert startup_options['protocol_version'] == 2

    def test_sharded_named_1(self):
        """mlaunch: test --sharded <name> for a single shard."""

        self.run_tool("init --sharded foo --single")
        assert len(self.tool.get_tagged('foo')) == 1

    def test_mlaunch_list(self):
        """mlaunch: test list command """

        self.run_tool("init --sharded 2 --replicaset --mongos 2")
        self.run_tool("list")

        # capture stdout and only keep from actual LIST output
        output = sys.stdout.getvalue().splitlines()
        output = output[output.index(next(o for o in output
                                          if o.startswith('PROCESS'))):]

        assert self.helper_output_has_line_with(['PROCESS', 'STATUS',
                                                 'PORT'], output) == 1
        assert self.helper_output_has_line_with(['mongos',
                                                 'running'], output) == 2
        assert self.helper_output_has_line_with(['config server',
                                                 'running'], output) == 1
        assert self.helper_output_has_line_with(['shard01'], output) == 1
        assert self.helper_output_has_line_with(['shard02'], output) == 1
        assert self.helper_output_has_line_with(['running',
                                                 'running'], output) == 9

    def helper_which(self, pgm):
        """equivalent of which command."""

        path = os.getenv('PATH')
        for p in path.split(os.path.pathsep):
            p = os.path.join(p, pgm)
            if os.path.exists(p) and os.access(p, os.X_OK):
                return p

    def test_mlaunch_binary_path_start(self):
        """Test if --binarypath is persistent between init and start."""

        # get true binary path (to test difference to not specifying one)
        path = self.helper_which('mongod')
        path = path[:path.rfind('/')]

        self.run_tool("init --single --binarypath %s" % path)
        self.run_tool("stop")

        self.run_tool("start")
        assert self.tool.loaded_args['binarypath'] == path
        assert self.tool.startup_info[str(self.port)].startswith('%s/mongod'
                                                                 % path)

        self.run_tool("stop")
        try:
            self.run_tool("start --binarypath /some/other/path")
            raise Exception
        except Exception:
            assert self.tool.args['binarypath'] == '/some/other/path'
            assert(self.tool.startup_info[str(self.port)].
                   startswith('/some/other/path/mongod'))

    @pytest.mark.xfail(raises=SystemExit)
    def test_single_and_arbiter(self):
        """mlaunch: test --single with --arbiter error."""

        self.run_tool("init --single --arbiter")

    def test_oplogsize_config(self):
        """mlaunch: test config server never receives --oplogSize parameter."""

        self.run_tool("init --sharded 1 --single --oplogSize 19 --verbose")
        output = sys.stdout.getvalue().splitlines()

        output_launch_config = next(o for o in output if '--configsvr' in o)
        assert '--oplogSize' not in output_launch_config


if __name__ == '__main__':

    # run individual tests with normal print output
    tml = TestMLaunch()
    tml.setup()
    tml.test_kill_partial()
    tml.teardown()
