import shutil
import socket
import time
import os
import json
import sys

from mtools.mlaunch.mlaunch import MLaunchTool
from pymongo import MongoClient
from pymongo.errors import AutoReconnect, ConnectionFailure
from nose.tools import *


class TestMLaunch(object):
    """ This class tests functionality around the mlaunch tool. It has some
        additional methods that are helpful for the tests, as well as a setup
        and teardown method for all tests.
    """

    static_port = 33333
    max_port_range = 100
    data_dir = 'test_mlaunch_data'


    def __init__(self):
        """ Constructor. """
        self.n_processes_started = 0
        self.port = TestMLaunch.static_port


    def _reserve_ports(self, number):
        self.n_processes_started = number
        self.port = TestMLaunch.static_port
        TestMLaunch.static_port += number
        

    def setup(self):
        """ start up method to create mlaunch tool and find free port. """
        self.tool = MLaunchTool()
        # self.port = self._find_free_port(self.port)
        self.n_processes_started = 0

        # if the test data path exists, remove it
        if os.path.exists(self.data_dir):
            shutil.rmtree(self.data_dir)


    def teardown(self):
        """ tear down method after each test, removes data directory. """

        # shutdown as many processes as the test required
        for p in range(self.n_processes_started):
            print "shutting", self.port + p
            self._shutdown_mongosd(self.port + p)

        # if the test data path exists, remove it
        if os.path.exists(self.data_dir):
            shutil.rmtree(self.data_dir)


    def _shutdown_mongosd(self, port):
        """ send the shutdown command to a mongod or mongos on given port. """
        try:
            mc = MongoClient('localhost:%i' % port)
            try:
                mc.admin.command('shutdown', force=True)
            except AutoReconnect:
                pass
        except ConnectionFailure:
            pass
        else:
            mc.close()


    @raises(ConnectionFailure)
    def test_test(self):
        """ TestMLaunch setup and teardown test """

        # test that variable is reset
        assert self.n_processes_started == 0

        # test that data dir does not exist
        assert not os.path.exists(self.data_dir)

        # get ports for processes during this test
        self._reserve_ports(1)

        # start mongo process on free test port
        self.tool.run("--single --port %i --nojournal --dir %s" % (self.port, self.data_dir))

        # call teardown method within this test
        self.teardown()

        # test that data dir does not exist anymore
        assert not os.path.exists(self.data_dir)

        # no processes need to be killed anymore for the real teardown
        self.n_processes_started = 0

        # test that mongod is not running on this port anymore (raises ConnectionFailure)
        mc = MongoClient('localhost:%i' % self.port)


    def test_single(self):
        """ mlaunch: start stand-alone server and tear down again """

        # get ports for processes during this test
        self._reserve_ports(1)

        # start mongo process on free test port 
        self.tool.run("--single --port %i --nojournal --dir %s" % (self.port, self.data_dir))

        # check if data directory and logfile exist
        assert os.path.exists(os.path.join(self.data_dir, 'db'))
        assert os.path.isfile(os.path.join(self.data_dir, 'mongod.log'))


    @raises(SystemExit)
    def test_single_on_existing_port(self):
        """ mlaunch: using already existing port fails """

        # get ports for processes during this test
        self._reserve_ports(1)

        # start mongo process on free test port
        self.tool.run("--single --port %i --nojournal --dir %s" % (self.port, self.data_dir))

        # start mongo process on same port, should raise SystemExit
        self.tool.run("--single --port %i --nojournal --dir %s" % (self.port, self.data_dir))


    def test_replicaset_conf(self):
        """ mlaunch: start replica set of 2 nodes + arbiter and compare rs.conf() """

        # get ports for processes during this test
        self._reserve_ports(3)

        # start mongo process on free test port (don't need journal for this test)
        self.tool.run("--replicaset --nodes 2 --arbiter --port %i --nojournal --dir %s" % (self.port, self.data_dir))

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


    def test_restart(self):
        """ mlaunch: --restart brings up the same configuration """

        # get ports for processes during this test
        self._reserve_ports(3)

        # start mongo process on free test port 
        self.tool.run("--replicaset --nodes 2 --arbiter --port %i --nojournal --dir %s" % (self.port, self.data_dir))

        self.teardown()

        # start mongo process on free test port 
        self.tool.run("--restart --dir %s" % self.data_dir)

        # repeat test on replica set with restarted set
        self.test_replicaset_conf()


    @timed(60)
    def test_replicaset_ismaster(self):
        """ mlaunch: start replica set and verify that first node becomes primary (slow)
            Test must complete in 60 seconds.
        """

        # get ports for processes during this test
        self._reserve_ports(3)

        # start mongo process on free test port
        self.tool.run("--replicaset --port %i --nojournal --dir %s" % (self.port, self.data_dir))

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

        # get ports for processes during this test
        self._reserve_ports(4)

        # start mongo process on free test port 
        self.tool.run("--sharded 2 --single --port %i --nojournal --dir %s" % (self.port, self.data_dir))
    
        # check if data directories and logfile exist
        assert os.path.exists(os.path.join(self.data_dir, 'shard01/db'))
        assert os.path.exists(os.path.join(self.data_dir, 'shard02/db'))
        assert os.path.exists(os.path.join(self.data_dir, 'config/db'))
        assert os.path.isfile(os.path.join(self.data_dir, 'mongos.log'))

        # create mongo client
        mc = MongoClient('localhost:%i' % (self.port+3))

        # check for 2 shards and 1 mongos
        assert mc['config']['shards'].count() == 2
        assert mc['config']['mongos'].count() == 1


    def test_startup_file(self):
        """ mlaunch: create .mlaunch_startup file in data path
            Also tests utf-8 to byte conversion and json import.
        """
        # get ports for processes during this test
        self._reserve_ports(1)

        self.tool.run("--single --port %i --nojournal --dir %s" % (self.port, self.data_dir))

        # check if the startup file exists
        startup_file = os.path.join(self.data_dir, '.mlaunch_startup')
        assert os.path.isfile(startup_file)

        # compare content of startup file with tool.args
        file_args = self.tool.convert_u2b(json.load(open(startup_file, 'r')))
        assert file_args == self.tool.args


    @raises(SystemExit)
    def test_check_port_availability(self):
        """ mlaunch: test check_port_availability() method """
        
        # get ports for processes during this test
        self._reserve_ports(1)

        # start mongod
        self.tool.run("--single --port %i --nojournal --dir %s" % (self.port, self.data_dir))

        # make sure port is not available for another launch on that port
        self.tool.check_port_availability(self.port, "mongod")


    def test_single_mongos_explicit(self):
        """ mlaunch: test if single mongos creates <datadir>/mongos.log """
        self._reserve_ports(4)

        # start 2 shards, 1 config server, 1 mongos
        self.tool.run("--sharded 2 --single --config 1 --mongos 1 --port %i --nojournal --dir %s" % (self.port, self.data_dir))

        # check if mongos log files exist on correct ports
        assert os.path.exists(os.path.join(self.data_dir, 'mongos.log'))


    def test_multiple_mongos(self):
        """ mlaunch: test if multiple mongos use separate log files in 'mongos' subdir """
        self._reserve_ports(5)

        # start 2 shards, 1 config server, 2 mongos
        self.tool.run("--sharded 2 --single --config 1 --mongos 2 --port %i --nojournal --dir %s" % (self.port, self.data_dir))

        assert os.path.exists(os.path.join(self.data_dir, 'mongos', 'mongos_%i.log' % (self.port + 3)))
        assert os.path.exists(os.path.join(self.data_dir, 'mongos', 'mongos_%i.log' % (self.port + 4)))


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

        # get ports for processes during this test
        self._reserve_ports(12)

        # start mongo process on free test port (don't need journal for this test)
        self.tool.run("--replicaset --nodes 11 --arbiter --port %i --nojournal --dir %s" % (self.port, self.data_dir))

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


    def test_large_replicaset_noarbiter(self):
        """ mlaunch: start large replica set of 12 nodes without arbiter """

        # get ports for processes during this test
        self._reserve_ports(12)

        # start mongo process on free test port (don't need journal for this test)
        self.tool.run("--replicaset --nodes 12 --port %i --nojournal --dir %s" % (self.port, self.data_dir))

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


    # TODO: test functionality of --binarypath, --authentication, --verbose, --name


    # mark slow tests
    test_replicaset_ismaster.slow = 1
    test_sharded_status.slow = 1
