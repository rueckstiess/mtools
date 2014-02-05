import inspect
import shutil
import socket
import time
import os
import json
import sys

from mtools.mlaunch.mlaunch import MLaunchTool, shutdown_host
from pymongo import MongoClient
from pymongo.errors import AutoReconnect, ConnectionFailure
from bson import SON
from nose.tools import *
from nose.plugins.attrib import attr
from nose.plugins.skip import Skip, SkipTest


class TestMLaunch(object):
    """ This class tests functionality around the mlaunch tool. It has some
        additional methods that are helpful for the tests, as well as a setup
        and teardown method for all tests.

        Don't call tests from other tests. This won't work as each test gets
        its own data directory (for debugging).
    """

    port = 33333
    base_dir = 'data_test_mlaunch'


    def __init__(self):
        """ Constructor. """
        self.use_authentication = False
        self.data_dir = ''
        

    def setup(self):
        """ start up method to create mlaunch tool and find free port """
        self.tool = MLaunchTool()

        # if the test data path exists, remove it
        if os.path.exists(self.base_dir):
            shutil.rmtree(self.base_dir)


    def teardown(self):
        """ tear down method after each test, removes data directory """        

        # kill all running processes
        self.tool.discover()

        ports = self.tool.get_tagged(['all', 'running'])
        processes = self.tool._get_processes().values()
        for p in processes:
            p.kill()

        self.tool.wait_for(ports, to_start=False)

        # quick sleep to avoid spurious test failures
        time.sleep(0.1)

        # if the test data path exists, remove it
        if os.path.exists(self.base_dir):
            shutil.rmtree(self.base_dir)


    def run_tool(self, arg_str):
        """ wrapper to call self.tool.run() with or without authentication """
        # name data directory according to test method name
        caller = inspect.stack()[1][3]
        self.data_dir = os.path.join(self.base_dir, caller)

        # add data directory to arguments for all commands
        arg_str += ' --dir %s' % self.data_dir
        
        if arg_str.startswith('init') or arg_str.startswith('--'):
            # add --port and --nojournal to init calls
            arg_str += ' --port %i --nojournal' % self.port 
            
            if self.use_authentication:
                # add --authentication to init calls if flag is set
                arg_str += ' --authentication'

        self.tool.run(arg_str)


    # -- tests below ---

    @raises(ConnectionFailure)
    def test_test(self):
        """ TestMLaunch setup and teardown test """

        # test that data dir does not exist
        assert not os.path.exists(self.data_dir)

        # start mongo process on free test port
        self.run_tool("init --single")

        # call teardown method within this test
        self.teardown()

        # test that data dir does not exist anymore
        assert not os.path.exists(self.data_dir)

        # test that mongod is not running on this port anymore (raises ConnectionFailure)
        mc = MongoClient('localhost:%i' % self.port)


    def test_argv_run(self):
        """ mlaunch: test true command line arguments, instead of passing into tool.run() """
        
        # make command line arguments through sys.argv
        sys.argv = ['mlaunch', 'init', '--single', '--dir', self.base_dir, '--port', str(self.port), '--nojournal']

        self.tool.run()
        assert self.tool.is_running(self.port)


    def test_init_default(self):
        """ mlaunch: test that 'init' command can be omitted, is default """

        # make command line arguments through sys.argv
        sys.argv = ['mlaunch', '--single', '--dir', self.base_dir, '--port', str(self.port), '--nojournal']

        self.tool.run()
        assert self.tool.is_running(self.port)


    def test_init_default_arguments(self):
        """ mlaunch: test that 'init' command is default, even when specifying arguments to run() """
        
        self.run_tool("--single")
        assert self.tool.is_running(self.port)


    def test_single(self):
        """ mlaunch: start stand-alone server and tear down again """

        # start mongo process on free test port
        self.run_tool("init --single")

        # make sure node is running
        assert self.tool.is_running(self.port)

        # check if data directory and logfile exist
        assert os.path.exists(os.path.join(self.data_dir, 'db'))
        assert os.path.isfile(os.path.join(self.data_dir, 'mongod.log'))

        # check that the tags are set correctly: 'single', 'mongod', 'running', <port>
        assert set(self.tool.get_tags_of_port(self.port)) == set(['running', 'mongod', 'all', 'single', str(self.port)])



    def test_replicaset_conf(self):
        """ mlaunch: start replica set of 2 nodes + arbiter and compare rs.conf() """

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
        assert sum(1 for memb in conf['members'] if 'arbiterOnly' in memb and memb['arbiterOnly']) == 1


    @timed(60)
    @attr('slow')
    def test_replicaset_ismaster(self):
        """ mlaunch: start replica set and verify that first node becomes primary """

        # start mongo process on free test port
        self.run_tool("init --replicaset")

        # create mongo client
        mc = MongoClient('localhost:%i' % self.port)

        # test if first node becomes primary after some time
        ismaster = False
        while not ismaster:
            result = mc.admin.command("ismaster")
            ismaster = result["ismaster"]
            time.sleep(1)
            print "sleeping"

        # insert a document and wait to replicate to 2 secondaries (10 sec timeout)
        mc.test.smokeWait.insert({}, w=2, wtimeout=10*60*1000)


    def test_sharded_status(self):
        """ mlaunch: start cluster with 2 shards of single nodes, 1 config server """

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
        assert mc['config']['shards'].count() == 2
        assert mc['config']['mongos'].count() == 1


    def test_shard_names(self):
        """ mlaunch: test if sharded cluster with explicit shard names works """

        # start mongo process on free test port 
        self.run_tool("init --sharded tic tac toe --replicaset")

        # create mongo client
        mc = MongoClient('localhost:%i' % (self.port))

        # check that shard names match
        shard_names = set( doc['_id'] for doc in mc['config']['shards'].find() )
        assert shard_names == set(['tic', 'tac', 'toe'])


    def test_startup_file(self):
        """ mlaunch: create .mlaunch_startup file in data path """
        
        # Also tests utf-8 to byte conversion and json import

        self.run_tool("init --single -v")

        # check if the startup file exists
        startup_file = os.path.join(self.data_dir, '.mlaunch_startup')
        assert os.path.isfile(startup_file)

        # compare content of startup file with tool.args
        file_contents = self.tool._convert_u2b(json.load(open(startup_file, 'r')))
        assert file_contents['parsed_args'] == self.tool.args
        assert file_contents['unknown_args'] == self.tool.unknown_args


    def test_single_mongos_explicit(self):
        """ mlaunch: test if single mongos is running on start port and creates <datadir>/mongos.log """
        
        # start 2 shards, 1 config server, 1 mongos
        self.run_tool("init --sharded 2 --single --config 1 --mongos 1")

        # check if mongos log files exist on correct ports
        assert os.path.exists(os.path.join(self.data_dir, 'mongos.log'))

        # check for correct port
        assert self.tool.get_tagged('mongos') == set([self.port])


    def test_single_mongos(self):
        """ mlaunch: test if multiple mongos use separate log files in 'mongos' subdir """

        # start 2 shards, 1 config server, 2 mongos
        self.run_tool("init --sharded 2 --single --config 1 --mongos 1")

        # check that 2 mongos are running
        assert len( self.tool.get_tagged(['mongos', 'running']) ) == 1


    def test_multiple_mongos(self):
        """ mlaunch: test if multiple mongos use separate log files in 'mongos' subdir """

        # start 2 shards, 1 config server, 2 mongos
        self.run_tool("init --sharded 2 --single --config 1 --mongos 2")

        # this also tests that mongos are started at the beginning of the port range
        assert os.path.exists(os.path.join(self.data_dir, 'mongos', 'mongos_%i.log' % (self.port)))
        assert os.path.exists(os.path.join(self.data_dir, 'mongos', 'mongos_%i.log' % (self.port + 1)))

        # check that 2 mongos are running
        assert len( self.tool.get_tagged(['mongos', 'running']) ) == 2


    def test_filter_valid_arguments(self):
        """ mlaunch: check arguments unknown to mlaunch against mongos and mongod """

        # filter against mongod
        result = self.tool._filter_valid_arguments("--slowms 500 -vvv --configdb localhost:27017 --foobar".split(), "mongod")
        assert result == "--slowms 500 -vvv"

        # filter against mongos
        result = self.tool._filter_valid_arguments("--slowms 500 -vvv --configdb localhost:27017 --foobar".split(), "mongos")
        assert result == "-vvv --configdb localhost:27017"


    def test_large_replicaset_arbiter(self):
        """ mlaunch: start large replica set of 12 nodes with arbiter """

        # start mongo process on free test port (don't need journal for this test)
        self.run_tool("init --replicaset --nodes 11 --arbiter")

        # check if data directories exist
        assert os.path.exists(os.path.join(self.data_dir, 'replset'))
        assert os.path.exists(os.path.join(self.data_dir, 'replset/rs1'))
        assert os.path.exists(os.path.join(self.data_dir, 'replset/rs2'))
        assert os.path.exists(os.path.join(self.data_dir, 'replset/rs3'))
        assert os.path.exists(os.path.join(self.data_dir, 'replset/rs4'))
        assert os.path.exists(os.path.join(self.data_dir, 'replset/rs5'))
        assert os.path.exists(os.path.join(self.data_dir, 'replset/rs6'))
        assert os.path.exists(os.path.join(self.data_dir, 'replset/rs7'))
        assert os.path.exists(os.path.join(self.data_dir, 'replset/rs8'))
        assert os.path.exists(os.path.join(self.data_dir, 'replset/rs9'))
        assert os.path.exists(os.path.join(self.data_dir, 'replset/rs10'))
        assert os.path.exists(os.path.join(self.data_dir, 'replset/rs11'))
        assert os.path.exists(os.path.join(self.data_dir, 'replset/arb'))

        # create mongo client for the next tests
        mc = MongoClient('localhost:%i' % self.port)

        # get rs.conf() and check for 12 members, exactly one arbiter
        conf = mc['local']['system.replset'].find_one()
        assert len(conf['members']) == 12
        assert sum(1 for memb in conf['members'] if 'arbiterOnly' in memb and memb['arbiterOnly']) == 1

        # check that 12 nodes are discovered
        assert len(self.tool.get_tagged('all')) == 12


    def test_large_replicaset_noarbiter(self):
        """ mlaunch: start large replica set of 12 nodes without arbiter """

        # start mongo process on free test port (don't need journal for this test)
        self.run_tool("init --replicaset --nodes 12")

        # check if data directories exist
        assert os.path.exists(os.path.join(self.data_dir, 'replset'))
        assert os.path.exists(os.path.join(self.data_dir, 'replset/rs1'))
        assert os.path.exists(os.path.join(self.data_dir, 'replset/rs2'))
        assert os.path.exists(os.path.join(self.data_dir, 'replset/rs3'))
        assert os.path.exists(os.path.join(self.data_dir, 'replset/rs4'))
        assert os.path.exists(os.path.join(self.data_dir, 'replset/rs5'))
        assert os.path.exists(os.path.join(self.data_dir, 'replset/rs6'))
        assert os.path.exists(os.path.join(self.data_dir, 'replset/rs7'))
        assert os.path.exists(os.path.join(self.data_dir, 'replset/rs8'))
        assert os.path.exists(os.path.join(self.data_dir, 'replset/rs9'))
        assert os.path.exists(os.path.join(self.data_dir, 'replset/rs10'))
        assert os.path.exists(os.path.join(self.data_dir, 'replset/rs11'))
        assert os.path.exists(os.path.join(self.data_dir, 'replset/rs12'))

        # create mongo client for the next tests
        mc = MongoClient('localhost:%i' % self.port)

        # get rs.conf() and check for 12 members, no arbiters
        conf = mc['local']['system.replset'].find_one()
        assert len(conf['members']) == 12
        assert sum(1 for memb in conf['members'] if 'arbiterOnly' in memb and memb['arbiterOnly']) == 0


    def test_stop(self):
        """ mlaunch: test stopping all nodes """

        self.run_tool("init --replicaset")
        self.run_tool("stop")

        # make sure all nodes are down
        nodes = self.tool.get_tagged('all')
        assert all( not self.tool.is_running(node) for node in nodes )


    def test_kill(self):
        """ mlaunch: test killing all nodes """

        # start sharded cluster and kill with default signal (15)
        self.run_tool("init --sharded 2 --single")
        self.run_tool("kill")

        # make sure all nodes are down
        nodes = self.tool.get_tagged('all')
        assert all( not self.tool.is_running(node) for node in nodes )


        # start nodes again, this time, kill with string "SIGTERM"
        self.run_tool("start")
        self.run_tool("kill --signal SIGTERM")

        # make sure all nodes are down
        nodes = self.tool.get_tagged('all')
        assert all( not self.tool.is_running(node) for node in nodes )


        # start nodes again, this time, kill with signal 9 (SIGKILL)
        self.run_tool("start")
        self.run_tool("kill --signal 9")

        # make sure all nodes are down
        nodes = self.tool.get_tagged('all')
        assert all( not self.tool.is_running(node) for node in nodes )



    def test_stop_start(self):
        """ mlaunch: test stop and then re-starting nodes """

        # start mongo process on free test port
        self.run_tool("init --replicaset")
        self.run_tool("stop")
        time.sleep(1)
        self.run_tool("start")

        # make sure all nodes are running
        nodes = self.tool.get_tagged('all')
        assert all( self.tool.is_running(node) for node in nodes )

    
    @timed(180)
    @attr('slow')
    def test_kill_partial(self):
        """ mlaunch: test killing and restarting tagged groups on different tags """

        # key is tag for command line, value is tag for get_tagged
        tags = ['shard01', 'shard 1', 'mongos', 'mongod 2', 'config 1', str(self.port)] 

        # start large cluster
        self.run_tool("init --sharded 2 --replicaset --config 3 --mongos 3 --authentication")

        # make sure all nodes are running
        nodes = self.tool.get_tagged('all')
        assert all( self.tool.is_running(node) for node in nodes )

        # go through all tags, stop nodes for each tag, confirm only the tagged ones are down, start again
        for tag in tags:
            print "---------", tag
            self.run_tool("kill %s" % tag)
            assert self.tool.get_tagged('down') == self.tool.get_tagged(tag)
            time.sleep(1)

            # short sleep, because travis seems to be sensitive and sometimes fails otherwise
            self.run_tool("start")
            assert len(self.tool.get_tagged('down')) == 0
            time.sleep(1)

        # make sure primaries are running again (we just failed them over above). 
        # while True is ok, because test times out after some time
        while True:
            primaries = self.tool.get_tagged('primary')
            if len(primaries) == 2:
                break
            time.sleep(1)
            self.tool.discover()

        # test for primary, but as the nodes lose their tags, needs to be manual
        self.run_tool("kill primary")
        assert len(self.tool.get_tagged('down')) == 2


    def test_restart_with_unkown_args(self):
        """ mlaunch: test start command with extra unknown arguments """

        # init environment (sharded, single shards ok)
        self.run_tool("init --single")
        
        # get verbosity of mongod, assert it is 0
        mc = MongoClient(port=self.port)
        loglevel = mc.admin.command(SON([('getParameter', 1), ('logLevel', 1)]))
        assert loglevel[u'logLevel'] == 0

        # stop and start nodes but pass in unknown_args
        self.run_tool("stop")

        # short sleep, because travis seems to be sensitive and sometimes fails otherwise
        time.sleep(1)

        self.run_tool("start -vv")

        # compare that the nodes are restarted with the new unknown_args, assert loglevel is now 2
        mc = MongoClient(port=self.port)
        loglevel = mc.admin.command(SON([('getParameter', 1), ('logLevel', 1)]))
        assert loglevel[u'logLevel'] == 2

        # stop and start nodes without unknown args again
        self.run_tool("stop")
        
        # short sleep, because travis seems to be sensitive and sometimes fails otherwise
        time.sleep(1)

        self.run_tool("start")

        # compare that the nodes are restarted with the previous loglevel
        mc = MongoClient(port=self.port)
        loglevel = mc.admin.command(SON([('getParameter', 1), ('logLevel', 1)]))
        assert loglevel[u'logLevel'] == 0


    def test_start_stop_single_repeatedly(self):
        """ mlaunch: test starting and stopping single node in short succession """ 
        # repeatedly start single node
        self.run_tool("init --single")

        for i in range(10):
            self.run_tool("stop")

            # short sleep, because travis seems to be sensitive and sometimes fails otherwise
            time.sleep(1)

            self.run_tool("start")

    
    @raises(SystemExit)
    def test_init_init_replicaset(self):
        """ mlaunch: test calling init a second time on the replica set """

        # init a replica set
        self.run_tool("init --replicaset")

        # now stop and init again, this should work if everything is stopped and identical environment
        self.run_tool("stop")
        self.run_tool("init --replicaset")

        # but another init should fail with a SystemExit
        self.run_tool("init --replicaset")


    def test_start_stop_replicaset_repeatedly(self):
        """ mlaunch: test starting and stopping replica set in short succession """ 
        # repeatedly start replicaset nodes
        self.run_tool("init --replicaset")

        for i in range(10):
            self.run_tool("stop")

            # short sleep, because travis seems to be sensitive and sometimes fails otherwise
            time.sleep(1)

            self.run_tool("start")


    @attr('slow')
    @attr('auth')
    def test_repeat_all_with_auth(self):
        """ this test will repeat all the tests in this class (excluding itself) but with authentication. """
        tests = [t for t in inspect.getmembers(self, predicate=inspect.ismethod) if t[0].startswith('test_') ]

        self.use_authentication = True

        for name, method in tests:
            # don't call any tests that use auth already (tagged with 'auth' attribute), including this method
            if hasattr(method, 'auth'):
                continue

            setattr(method.__func__, 'description', method.__doc__.strip() + ' with authentication.')
            yield ( method, )

        self.use_authentication = False

    # TODO 
    # - test functionality of --binarypath, --verbose, --name

    # All tests that use authentication need to be decorated with @attr('auth')


if __name__ == '__main__':

    # run individual tests with normal print output 
    tml = TestMLaunch()
    tml.setup()
    tml.test_start_stop_replicaset_repeatedly()
    tml.teardown()



