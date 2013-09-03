#!/usr/bin/python

import subprocess
import argparse
import threading
import os, time
import socket
import json
import re

from mtools.util.cmdlinetool import BaseCmdLineTool

try:
    try:
        from pymongo import MongoClient as Connection
    except ImportError:
        from pymongo import Connection
    from pymongo.errors import ConnectionFailure, AutoReconnect, OperationFailure
except ImportError:
    raise ImportError("Can't import pymongo. See http://api.mongodb.org/python/current/ for instructions on how to install pymongo.")


def pingMongoDS(host, interval=1, timeout=30):
    """ Ping a mongos or mongod every `interval` seconds until it responds, or `timeout` seconds have passed. """
    con = None
    startTime = time.time()
    while not con:
        if (time.time() - startTime) > timeout:
            return False
        try:
            con = Connection(host)
            return True
        except (ConnectionFailure, AutoReconnect) as e:
            time.sleep(interval)


class MLaunchTool(BaseCmdLineTool):

    # additional arguments that can be passed on to mongos, all others will only go to mongod
    mongos_arguments = ['quiet', 'logappend', 'pidfilepath', 'keyFile', 'nounixsocket', 'syslog', \
                        'nohttpinterface', 'test', 'upgrade', 'ipv6', 'jsonp', 'noscripting']

    def __init__(self):
        BaseCmdLineTool.__init__(self)
        self.argparser.description = 'script to launch MongoDB stand-alone servers, replica sets and shards. You must specify either --single or --replicaset. \
            In addition to the optional arguments below, you can specify any mongos and mongod argument, which will be passed on, if the process accepts it.'

        # either single or replica set
        me_group = self.argparser.add_mutually_exclusive_group(required=True)
        me_group.add_argument('--single', action='store_true', help='creates a single stand-alone mongod instance')
        me_group.add_argument('--replicaset', action='store_true', help='creates replica set with several mongod instances')
        me_group.add_argument('--restart', '--restore', action='store_true', help='restarts a previously launched existing configuration from the data directory.')

        # replica set arguments
        self.argparser.add_argument('--nodes', action='store', metavar='NUM', type=int, default=3, help='adds NUM data nodes to replica set (requires --replicaset, default=3)')
        self.argparser.add_argument('--arbiter', action='store_true', default=False, help='adds arbiter to replica set (requires --replicaset)')
        self.argparser.add_argument('--name', action='store', metavar='NAME', default='replset', help='name for replica set (default=replset)')
        
        # sharded clusters
        self.argparser.add_argument('--sharded', action='store', nargs='*', metavar='N', help='creates a sharded setup consisting of several singles or replica sets. Provide either list of shard names or number of shards (default=1)')
        self.argparser.add_argument('--config', action='store', default=1, type=int, metavar='NUM', choices=[1, 3], help='adds NUM config servers to sharded setup (requires --sharded, NUM must be 1 or 3, default=1)')
        self.argparser.add_argument('--mongos', action='store', default=1, type=int, metavar='NUM', help='starts NUM mongos processes (requires --sharded, default=1)')

        # dir, verbose, port, auth
        self.argparser.add_argument('--dir', action='store', default='./data', help='base directory to create db and log paths (default=./data/)')
        self.argparser.add_argument('--verbose', action='store_true', default=False, help='outputs information about the launch')
        self.argparser.add_argument('--port', action='store', type=int, default=27017, help='port for mongod, start of port range in case of replica set or shards (default=27017)')
        self.argparser.add_argument('--authentication', action='store_true', default=False, help='enable authentication and create a key file and admin user (admin/mypassword)')
        self.argparser.add_argument('--binarypath', action='store', default=None, metavar='PATH', help='search for mongod/s binaries in the specified PATH.')

        self.hostname = socket.gethostname()


    def run(self, arguments=None):
        BaseCmdLineTool.run(self, arguments, get_unknowns=True)

        # load or store parameters
        if self.args['restart']:
            self.load_parameters()
        else:
            self.store_parameters()

        
        # check if authentication is enabled        
        if self.args['authentication']:
            if not os.path.exists(self.args['dir']):
                os.makedirs(self.args['dir'])
            os.system('openssl rand -base64 753 > %s/keyfile'%self.args['dir'])
            os.system('chmod 600 %s/keyfile'%self.args['dir'])

        if self.args['sharded']:
            self._launchSharded()
        elif self.args['single']:
            self._launchSingle(self.args['dir'], self.args['port'])
        elif self.args['replicaset']:
            self._launchReplSet(self.args['dir'], self.args['port'], self.args['name'])


    def convert_u2b(self, obj):
        if isinstance(obj, dict):
            return dict([(self.convert_u2b(key), self.convert_u2b(value)) for key, value in obj.iteritems()])
        elif isinstance(obj, list):
            return [self.convert_u2b(element) for element in obj]
        elif isinstance(obj, unicode):
            return obj.encode('utf-8')
        else:
            return obj


    def load_parameters(self):
        datapath = self.args['dir']

        startup_file = os.path.join(datapath, '.mlaunch_startup')
        if os.path.exists(startup_file):
            self.args = self.convert_u2b(json.load(open(startup_file, 'r')))


    def store_parameters(self):
        datapath = self.args['dir']

        if not os.path.exists(datapath):
            os.makedirs(datapath)
        try:
            json.dump(self.args, open(os.path.join(datapath, '.mlaunch_startup'), 'w'), -1)
        except Exception:
            pass

    
    def check_port_availability(self, port, binary):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            s.bind(('', port))
            s.close()
        except:
            raise SystemExit("Can't start " + binary + ", port " + str(port) + " is already being used")

    
    def _createPaths(self, basedir, name=None):
        if name:
            datapath = os.path.join(basedir, name)
        else:
            datapath = basedir

        dbpath = os.path.join(datapath, 'db')
        if not os.path.exists(dbpath):
            os.makedirs(dbpath)
        if self.args['verbose']:
            print 'creating directory: %s'%dbpath
        
        return datapath


    def _filter_valid_arguments(self, arguments, binary="mongod"):
        """ check which of the list of arguments is accepted by the specified binary (mongod, mongos). 
            returns a list of accepted arguments. If an argument does not start with '-' but its preceding
            argument was accepted, then it is accepted as well. Example ['--slowms', '1000'] both arguments
            would be accepted for a mongod.
        """
        # get the help list of the binary
        ret = subprocess.Popen(['%s --help'%binary], stderr=subprocess.STDOUT, stdout=subprocess.PIPE, shell=True)
        out, err = ret.communicate()

        accepted_arguments = []

        # extract all arguments starting with a '-'
        for line in [option for option in out.split('\n')]:
            line = line.lstrip()
            if line.startswith('-'):
                accepted_arguments.append(line.split()[0])

        # filter valid arguments
        result = []
        for i, arg in enumerate(arguments):
            if arg.startswith('-'):
                # check if the binary accepts this argument or special case -vvv for any number of v
                if arg in accepted_arguments or re.match(r'-v+', arg):
                    result.append(arg)
            elif i > 0 and arguments[i-1] in result:
                # if it doesn't start with a '-', it could be the value of the last argument, e.g. `--slowms 1000`
                result.append(arg)

        # return valid arguments as joined string
        return ' '.join(result)


    def _launchSharded(self):
        # start up shards
        if len(self.args['sharded']) == 1:
            try:
                # --sharded was a number, name shards shard01, shard02, ... (only works with replica sets)
                n_shards = int(self.args['sharded'][0])
                shard_names = ['shard%.2i'%(i+1) for i in range(n_shards)]
            except ValueError, e:
                # --sharded was a string, use it as name for the one shard 
                shard_names = self.args['sharded']
        else:
            shard_names = self.args['sharded']


        # create shards as stand-alones or replica sets
        nextport = self.args['port']
        for p, shard in enumerate(shard_names):
            if self.args['single']:
                shard_names[p] = self._launchSingle(self.args['dir'], nextport, name=shard)
                nextport += 1
            elif self.args['replicaset']:
                shard_names[p] = self._launchReplSet(self.args['dir'], nextport, shard)
                nextport += self.args['nodes']
                if self.args['arbiter']:
                    nextport += 1

        
        # start up config server(s)
        config_string = []
        if self.args['config'] == 1:
            config_names = ['config']
        else:
            config_names = ['config1', 'config2', 'config3']
            
        for name in config_names:
            self._launchConfig(self.args['dir'], nextport, name)
            config_string.append('%s:%i'%(self.hostname, nextport))
            nextport += 1
        
        # start up mongos (at least 1)
        for i in range(max(1, self.args['mongos'])):
            self._launchMongoS(os.path.join(self.args['dir'], 'mongos.log'), nextport, ','.join(config_string))
            if i == 0: 
                # store host/port of first mongos (use localhost)
                self.mongos_host = '%s:%i'%(self.hostname, nextport)
                if self.args['authentication']:
                    self.mongos_host = 'localhost:%i'%(nextport)
            nextport += 1

        # add shards
        print "adding shards (can take a few seconds, grab a snickers) ..."

        con = Connection(self.mongos_host)

        shards_to_add = len(shard_names)

        while True:
            try:
                nshards = con['config']['shards'].count()
            except:
                nshards = 0
            if nshards >= shards_to_add:
                break

            for shard in shard_names:
                try:
                    res = con['admin'].command({'addShard':shard})
                except Exception as e:
                    if self.args['verbose']:
                        print e, '- will retry.'
                    continue

                if res['ok']:
                    if self.args['verbose']:
                        print "shard %s added successfully"%shard
                        shard_names.remove(shard)
                        break
                else:
                    if self.args['verbose']:
                        print res, '- will retry.'

            time.sleep(1)


    def _launchReplSet(self, basedir, portstart, name):
        threads = []
        configDoc = {'_id':name, 'members':[]}

        for i in range(self.args['nodes']):
            datapath = self._createPaths(basedir, '%s/rs%i'%(name, i+1))
            self._launchMongoD(os.path.join(datapath, 'db'), os.path.join(datapath, 'mongod.log'), portstart+i, replset=name)
        
            host = '%s:%i'%(self.hostname, portstart+i)
            configDoc['members'].append({'_id':len(configDoc['members']), 'host':host})
            threads.append(threading.Thread(target=pingMongoDS, args=(host, 1.0, 30)))
            if self.args['verbose']:
                print "waiting for mongod at %s to start up..."%host

            print "mongod at %s running." % host

        # launch arbiter if True
        if self.args['arbiter']:
            datapath = self._createPaths(basedir, '%s/arb'%(name))
            self._launchMongoD(os.path.join(datapath, 'db'), os.path.join(datapath, 'mongod.log'), portstart+self.args['nodes'], replset=name)
            
            host = '%s:%i'%(self.hostname, portstart+self.args['nodes'])
            configDoc['members'].append({'_id':len(configDoc['members']), 'host':host, 'arbiterOnly': True})
            threads.append(threading.Thread(target=pingMongoDS, args=(host, 1.0, 30)))
            if self.args['verbose']:
                print "waiting for mongod at %s to start up..."%host

            print "arbiter at %s running." % host

        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join()

        # initiate replica set
        con = Connection('localhost:%i'%portstart)

        try:
            rs_status = con['admin'].command({'replSetGetStatus': 1})
        except OperationFailure, e:
            con['admin'].command({'replSetInitiate':configDoc})
            if self.args['verbose']:
                print "replica set configured."

        return name + '/' + ','.join([c['host'] for c in configDoc['members']])


    def _launchConfig(self, basedir, port, name=None):
        datapath = self._createPaths(basedir, name)
        self._launchMongoD(os.path.join(datapath, 'db'), os.path.join(datapath, 'mongod.log'), port, replset=None, extra='--configsvr')

        host = '%s:%i'%(self.hostname, port)
        t = threading.Thread(target=pingMongoDS, args=(host, 1.0, 30))
        t.start()
        if self.args['verbose']:
            print "waiting for mongod config server at %s to start up..."%host
        t.join()
        print "mongod config server at %s running."%host


    def _launchSingle(self, basedir, port, name=None):
        datapath = self._createPaths(basedir, name)
        self._launchMongoD(os.path.join(datapath, 'db'), os.path.join(datapath, 'mongod.log'), port, replset=None)

        host = '%s:%i'%(self.hostname, port)
        t = threading.Thread(target=pingMongoDS, args=(host, 1.0, 30))
        t.start()
        if self.args['verbose']:
            print "waiting for mongod at %s to start up..."%host
        t.join()
        print "mongod at %s running."%host

        return host


    def _launchMongoD(self, dbpath, logpath, port, replset=None, extra=''):
        self.check_port_availability(port, "mongod")

        rs_param = ''
        if replset:
            rs_param = '--replSet %s'%replset

        auth_param = ''
        if self.args['authentication']:
            key_path = os.path.abspath(os.path.join(self.args['dir'], 'keyfile'))
            auth_param = '--keyFile %s'%key_path

        if self.unknown_args:
            extra = self._filter_valid_arguments(self.unknown_args, "mongod") + ' ' + extra

        path = self.args['binarypath'] or ''

        command_str = "%s %s --dbpath %s --logpath %s --port %i --logappend %s %s --fork"%(os.path.join(path, 'mongod'), rs_param, dbpath, logpath, port, auth_param, extra)

        ret = subprocess.call([command_str], stderr=subprocess.STDOUT, stdout=subprocess.PIPE, shell=True)
        if ret > 0:
            print "can't start mongod, return code %i."%ret
            print "tried to start: %s"%command_str
            raise SystemExit

        if self.args['verbose']:
            print 'launching: %s'%command_str

        return ret


    def _launchMongoS(self, logpath, port, configdb):
        extra = ''
        self.check_port_availability(port, "mongos")

        out = subprocess.PIPE
        if self.args['verbose']:
            out = None

        auth_param = ''
        if self.args['authentication']:
            key_path = os.path.abspath(os.path.join(self.args['dir'], 'keyfile'))
            auth_param = '--keyFile %s'%key_path

        if self.unknown_args:
            extra = self._filter_valid_arguments(self.unknown_args, "mongos") + extra

        path = self.args['binarypath'] or ''

        command_str = "%s --logpath %s --port %i --configdb %s --logappend %s %s --fork"%(os.path.join(path, 'mongos'), logpath, port, configdb, auth_param, extra)

        ret = subprocess.call([command_str], stderr=subprocess.STDOUT, stdout=subprocess.PIPE, shell=True)

        if ret > 0:
            print "can't start mongos, return code %i."%ret
            print "tried to start: %s"%command_str
            raise SystemExit

        if self.args['verbose']:
            print 'launching: %s'%command_str
        
        host = '%s:%i'%(self.hostname, port)
        t = threading.Thread(target=pingMongoDS, args=(host, 1.0, 30))
        t.start()
        if self.args['verbose']:
            print "waiting for mongos to start up..."
        t.join()
        print "mongos at %s running."%host



if __name__ == '__main__':
    tool = MLaunchTool()
    tool.run()

