import shutil
import socket
import os

from mtools.mlaunch.mlaunch import MLaunchTool
from pymongo import MongoClient
from pymongo.errors import AutoReconnect
from nose.tools import *


class TestMLaunch(object):

    default_port = 33333
    max_port_range = 100
    data_dir = 'test_mlaunch_data'

    def _port_available(self, port):
        """ check if `port` is available. """
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


    def _find_mongosd_processes(self):
        pnames = ["mongod", "mongos", "mongod.exe", "mongos.exe"]
        processes = [proc for proc in psutil.process_iter() if proc.name in pnames]
        return processes


    def _shutdown_mongosd(self, port):
        mc = MongoClient('localhost:%i' % port)
        try:
            mc.admin.command({'shutdown':1})
        except AutoReconnect: 
            pass
        mc.close()


    def _find_free_port(self):
        port = self.default_port
        # cycle through `max_port_range` ports until a free one is found
        while not self._port_available(port):
            port += 1
            if port >= self.default_port + self.max_port_range:
                raise SystemExit('could not find free port between %i and %i.' % (self.default_port, self.default_port + self.max_port_range))
        return port


    def test_mlaunch_single(self):
        """ Test mlaunching single stand-alone server and tearing down again. """
        tool = MLaunchTool()
        port = self._find_free_port()

        # start mongo process on free test port (don't need journal for this test)
        tool.run("--single --port %i --nojournal %s" % (port, self.data_dir))

        # check if data directory and logfile exist
        assert os.path.exists(os.path.join(self.data_dir, 'data/db'))
        assert os.path.isfile(os.path.join(self.data_dir, 'data/mongod.log'))

        # shutdown again
        self._shutdown_mongosd(port)

        # remove data directory
        shutil.rmtree(self.data_dir)

        



