import shutil
import socket
import time
import os

from mtools.mlaunch.mlaunch import MLaunchTool
from pymongo import MongoClient
from pymongo.errors import AutoReconnect
from nose.tools import *


class TestMLaunch(object):
    """ This class tests functionality around the mlaunch tool. It has some
        additional methods that are helpful for the tests, as well as a setUp
        and tearDown method for all tests.
    """

    default_port = 33333
    max_port_range = 100
    data_dir = 'test_mlaunch_data'


    def setUp(self):
        """ start up method to create mlaunch tool and find free port. """
        self.tool = MLaunchTool()
        self.port = self._find_free_port()


    def tearDown(self):
        """ tear down method after each test, removes data directory. """
        shutil.rmtree(self.data_dir)


    def _port_available(self, port):
        """ check if `port` is available and returns True or False. """
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            s.bind(('', port))
            s.close()
        except socket.error as e:
            if e.errno == socket.errno.EADDRINUSE:
                # socket already in use, return False
                return False
            else:
                # different error, raise Exception
                raise e
        # port free, return True
        return True


    # def _find_mongosd_processes(self):
    #     pnames = ["mongod", "mongos", "mongod.exe", "mongos.exe"]
    #     processes = [proc for proc in psutil.process_iter() if proc.name in pnames]
    #     return processes


    def _shutdown_mongosd(self, port):
        """ send the shutdown command to a mongod or mongos on given port. """
        mc = MongoClient('localhost:%i' % port)
        try:
            mc.admin.command({'shutdown':1})
        except AutoReconnect: 
            pass
        mc.close()


    def _find_free_port(self):
        """ iterate over ports opening a socket on that port until a free port is found, which is returned. """
        port = self.default_port
        # cycle through `max_port_range` ports until a free one is found
        while not self._port_available(port):
            port += 1
            if port >= self.default_port + self.max_port_range:
                raise SystemExit('could not find free port between %i and %i.' % (self.default_port, self.default_port + self.max_port_range))
        return port


    def test_mlaunch_single(self):
        """ mlaunch: start stand-alone server and tear down again. """

        # start mongo process on free test port (don't need journal for this test)
        self.tool.run("--single --port %i --nojournal --dir %s" % (self.port, self.data_dir))

        # check if data directory and logfile exist
        assert os.path.exists(os.path.join(self.data_dir, 'db'))
        assert os.path.isfile(os.path.join(self.data_dir, 'mongod.log'))

        # shutdown again
        self._shutdown_mongosd(self.port)


    def test_mlaunch_replicaset_conf(self):
        """ mlaunch: start replica set of 2 nodes + arbiter, compare rs.conf(). """

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

        # shutdown again
        for p in range(self.port, self.port+3):
            self._shutdown_mongosd(p)


    @timed(60)
    def test_mlaunch_replicaset_ismaster(self):
        """ mlaunch: start replica set and verify that first node becomes primary. 
            Test must complete in 60 seconds.
        """

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

        # shutdown again
        for p in range(self.port, self.port+3):
            self._shutdown_mongosd(p)


    def test_mlaunch_sharded_status(self):
        """ mlaunch: start cluster with 2 shards of single nodes, 1 config server. """

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

        # shutdown again
        for p in range(self.port, self.port+4):
            self._shutdown_mongosd(p)


        
    # mark slow tests
    test_mlaunch_replicaset_ismaster.slow = 1


