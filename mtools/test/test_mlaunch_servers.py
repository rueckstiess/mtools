import shutil
import socket
import time
import os
import json

from mtools.mlaunch.mlaunch import MLaunchTool
from pymongo import MongoClient
from pymongo.errors import AutoReconnect, ConnectionFailure
from nose.tools import *


class TestMLaunch(object):
    """ This class tests functionality around the mlaunch tool. It has some
        additional methods that are helpful for the tests, as well as a setUp
        and tearDown method for all tests.
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
            self._shutdown_mongosd(self.port + p)

        # if the test data path exists, remove it
        if os.path.exists(self.data_dir):
            shutil.rmtree(self.data_dir)


    def _shutdown_mongosd(self, port):
        """ send the shutdown command to a mongod or mongos on given port. """
        try:
            mc = MongoClient('localhost:%i' % port)
            try:
                mc.admin.command({'shutdown':1})
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

        # start mongo process on free test port (don't need journal for this test)
        self.tool.run("--single --port %i --nojournal --dir %s" % (self.port, self.data_dir))

        # shutdown 1 process at teardown
        self.n_processes_started = 1

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

        # start mongo process on free test port (don't need journal for this test)
        self.tool.run("--single --port %i --nojournal --dir %s" % (self.port, self.data_dir))

        # check if data directory and logfile exist
        assert os.path.exists(os.path.join(self.data_dir, 'db'))
        assert os.path.isfile(os.path.join(self.data_dir, 'mongod.log'))


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

        # get rs.conf() and check for 3 members, last one is arbiter        
        conf = mc['local']['system.replset'].find_one()
        assert len(conf['members']) == 3
        assert conf['members'][2]['arbiterOnly'] == True


    @timed(60)
    def test_replicaset_ismaster(self):
        """ mlaunch: start replica set and verify that first node becomes primary (slow)
            Test must complete in 60 seconds.
        """

        # get ports for processes during this test
        self._reserve_ports(3)

        # start mongo process on free test port (don't need journal for this test)
        self.tool.run("--replicaset --port %i --nojournal --dir %s" % (self.port, self.data_dir))

        # create mongo client
        mc = MongoClient('localhost:%i' % self.port)

        # test if first node becomes primary after some time
        while True:
            ismaster = mc.admin.command({'ismaster': 1})
            if ismaster['ismaster']:
                break
            time.sleep(1)


    def test_sharded_status(self):
        """ mlaunch: start cluster with 2 shards of single nodes, 1 config server """

        # get ports for processes during this test
        self._reserve_ports(4)

        # start mongo process on free test port (don't need journal for this test)
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


    def test_filter_valid_arguments(self):
        """ mlaunch: check arguments unknown to mlaunch against mongos and mongod """

        # filter against mongod
        result = self.tool._filter_valid_arguments("--slowms 500 -vvv --configdb localhost:27017 --foobar".split(), "mongod")
        assert result == "--slowms 500 -vvv"

        # filter against mongos
        result = self.tool._filter_valid_arguments("--slowms 500 -vvv --configdb localhost:27017 --foobar".split(), "mongos")
        assert result == "-vvv --configdb localhost:27017"


    # TODO: --binarypath, --authentication, --verbose, --mongos, --name, --restart


    # mark slow tests
    test_replicaset_ismaster.slow = 1
    test_sharded_status.slow = 1


