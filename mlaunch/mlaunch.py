#!/usr/bin/python

from pymongo import Connection
from pymongo.errors import ConnectionFailure, AutoReconnect, OperationFailure
import subprocess
import argparse
import threading
import os, time
import socket
import json

def pingMongoDS(host, interval=1, timeout=30):
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


class MongoLauncher(object):

    def __init__(self):

        self.parseArgs()
        self.hostname = socket.gethostname()

        if self.args['restore']:
            self.load_parameters()
        else:
            self.store_parameters()

        self.launch()

    def parseArgs(self):
        # create parser object
        parser = argparse.ArgumentParser(description='script to launch MongoDB stand-alone servers, replica sets, and shards')
        
        # positional argument
        parser.add_argument('dir', action='store', nargs='?', const='.', default='.', help='base directory to create db and log paths')

        # either single or replica set
        me_group = parser.add_mutually_exclusive_group(required=True)
        me_group.add_argument('--single', action='store_true', help='creates a single stand-alone mongod instance')
        me_group.add_argument('--replicaset', action='store_true', help='creates replica set with several mongod instances')
        me_group.add_argument('--restore', action='store_true', help='restores a previously launched existing configuration from the data directory.')

        parser.add_argument('--nodes', action='store', metavar='NUM', type=int, default=3, help='adds NUM data nodes to replica set (requires --replicaset, default: 3)')
        parser.add_argument('--arbiter', action='store_true', default=False, help='adds arbiter to replica set (requires --replicaset)')
        parser.add_argument('--name', action='store', metavar='NAME', default='replset', help='name for replica set (default: replset)')
        
        # sharded or not
        parser.add_argument('--sharded', action='store', nargs='*', metavar='N', help='creates a sharded setup consisting of several singles or replica sets. Provide either list of shard names or number of shards (default: 1)')
        parser.add_argument('--config', action='store', default=1, type=int, metavar='NUM', choices=[1, 3], help='adds NUM config servers to sharded setup (requires --sharded, NUM must be 1 or 3, default: 1)')

        # verbose, port, auth, loglevel
        parser.add_argument('--verbose', action='store_true', default=False, help='outputs information about the launch')
        parser.add_argument('--port', action='store', type=int, default=27017, help='port for mongod, start of port range in case of replica set or shards (default: 27017)')
        parser.add_argument('--authentication', action='store_true', default=False, help='enable authentication and create a key file and admin user (admin/mypassword)')
        parser.add_argument('--loglevel', action='store', default=False, type=int, help='increase loglevel to LOGLEVEL (default: 0)')
        parser.add_argument('--rest', action='store_true', default=False, help='enable REST interface on mongod processes')
        parser.add_argument('--local', action='store_true', default=False, help='run mongod/s process from local directory, i.e. "./mongod"')
        self.args = vars(parser.parse_args())
        if self.args['verbose']:
            print "parameters:", self.args


    def launch(self):
        datapath = os.path.join(self.args['dir'], 'data')
        
        # check if authentication is enabled        
        if self.args['authentication']:
            if not os.path.exists(datapath):
                os.makedirs(datapath)
            os.system('openssl rand -base64 753 > %s/keyfile'%datapath)
            os.system('chmod 600 %s/keyfile'%datapath)

        if self.args['sharded']:
            self._launchSharded()
        elif self.args['single']:
            self._launchSingle(self.args['dir'], self.args['port'], verbose=self.args['verbose'])
        elif self.args['replicaset']:
            self._launchReplSet(self.args['dir'], self.args['port'], self.args['name'], self.args['nodes'], self.args['arbiter'], self.args['verbose'])


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
        datapath = os.path.join(self.args['dir'], 'data')

        startup_file = os.path.join(datapath, '.mlaunch_startup')
        if os.path.exists(startup_file):
            self.args = self.convert_u2b(json.load(open(startup_file, 'r')))


    def store_parameters(self):
        datapath = os.path.join(self.args['dir'], 'data')

        if not os.path.exists(datapath):
            os.makedirs(datapath)
        try:
            json.dump(self.args, open(os.path.join(datapath, '.mlaunch_startup'), 'w'), -1)
        except Exception:
            pass

    def _createPaths(self, basedir, name=None, verbose=False):
        if name:
            datapath = os.path.join(basedir, 'data', name)
        else:
            datapath = os.path.join(basedir, 'data')

        dbpath = os.path.join(datapath, 'db')
        if not os.path.exists(dbpath):
            os.makedirs(dbpath)
        if verbose:
            print 'creating directory: %s'%dbpath
        
        return datapath


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
                shard_names[p] = self._launchSingle(self.args['dir'], nextport, name=shard, verbose=self.args['verbose'])
                nextport += 1
            elif self.args['replicaset']:
                shard_names[p] = self._launchReplSet(self.args['dir'], nextport, shard, self.args['nodes'], self.args['arbiter'], self.args['verbose'])
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
            self._launchConfig(self.args['dir'], nextport, name, verbose=self.args['verbose'])
            config_string.append('%s:%i'%(self.hostname, nextport))
            nextport += 1
        
        # start up mongos
        self._launchMongoS(os.path.join(self.args['dir'], 'data', 'mongos.log'), nextport, ','.join(config_string), auth=self.args['authentication'], loglevel=self.args['loglevel'], verbose=self.args['verbose'])
        self.mongos_host = '%s:%i'%(self.hostname, nextport)

        # add shards
        print "adding shards (can take a few seconds) ..."

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




    def _launchReplSet(self, basedir, portstart, name, numdata, arbiter, verbose=False):
        threads = []
        configDoc = {'_id':name, 'members':[]}

        for i in range(numdata):
            datapath = self._createPaths(basedir, '%s/rs%i'%(name, i+1), verbose)
            self._launchMongoD(os.path.join(datapath, 'db'), os.path.join(datapath, 'mongod.log'), portstart+i, replset=name, auth=self.args['authentication'], loglevel=self.args['loglevel'], verbose=verbose)
        
            host = '%s:%i'%(self.hostname, portstart+i)
            configDoc['members'].append({'_id':len(configDoc['members']), 'host':host})
            threads.append(threading.Thread(target=pingMongoDS, args=(host, 1.0, 30)))
            if verbose:
                print "waiting for mongod at %s to start up..."%host

        # launch arbiter if True
        if arbiter:
            datapath = self._createPaths(basedir, '%s/arb'%(name), verbose)
            self._launchMongoD(os.path.join(datapath, 'db'), os.path.join(datapath, 'mongod.log'), portstart+numdata, replset=name, auth=self.args['authentication'], loglevel=self.args['loglevel'], verbose=verbose)
            
            host = '%s:%i'%(self.hostname, portstart+numdata)
            configDoc['members'].append({'_id':len(configDoc['members']), 'host':host, 'arbiterOnly': True})
            threads.append(threading.Thread(target=pingMongoDS, args=(host, 1.0, 30)))
            if verbose:
                print "waiting for mongod at %s to start up..."%host

        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join()

        print "all mongod processes for replica set '%s' running."%name

        # initiate replica set
        con = Connection('localhost:%i'%portstart)

        try:
            rs_status = con['admin'].command({'replSetGetStatus': 1})
        except OperationFailure, e:
            con['admin'].command({'replSetInitiate':configDoc})
            if verbose:
                print "replica set configured."

        return name + '/' + ','.join([c['host'] for c in configDoc['members']])


    def _launchConfig(self, basedir, port, name=None, verbose=False):
        datapath = self._createPaths(basedir, name, verbose)
        self._launchMongoD(os.path.join(datapath, 'db'), os.path.join(datapath, 'mongod.log'), port, replset=None, verbose=verbose, auth=self.args['authentication'], loglevel=self.args['loglevel'], extra='--configsvr')

        host = '%s:%i'%(self.hostname, port)
        t = threading.Thread(target=pingMongoDS, args=(host, 1.0, 30))
        t.start()
        if verbose:
            print "waiting for mongod config server to start up..."
        t.join()
        print "mongod config server at %s running."%host


    def _launchSingle(self, basedir, port, name=None, verbose=False):
        datapath = self._createPaths(basedir, name, verbose)
        self._launchMongoD(os.path.join(datapath, 'db'), os.path.join(datapath, 'mongod.log'), port, replset=None, auth=self.args['authentication'], loglevel=self.args['loglevel'], verbose=verbose)

        host = '%s:%i'%(self.hostname, port)
        t = threading.Thread(target=pingMongoDS, args=(host, 1.0, 30))
        t.start()
        if verbose:
            print "waiting for mongod to start up..."
        t.join()
        print "mongod at %s running."%host

        return host


    def _launchMongoD(self, dbpath, logpath, port, replset=None, verbose=False, auth=False, loglevel=False, extra=''):
        rs_param = ''
        if replset:
            rs_param = '--replSet %s'%replset

        auth_param = ''
        if auth:
            key_path = os.path.abspath(os.path.join(self.args['dir'], 'data/keyfile'))
            auth_param = '--keyFile %s'%key_path

        log_param = ''
        if loglevel:
            log_param = '-' + ''.join(['v']*loglevel)

        if self.args['rest']:
            extra = '--rest ' + extra

        local = ''
        if self.args['local']:
            local = "./"

        ret = subprocess.call(['%smongod %s --dbpath %s --logpath %s --port %i --logappend %s %s %s --fork'%(local, rs_param, dbpath, logpath, port, auth_param, log_param, extra)], stderr=subprocess.STDOUT, stdout=subprocess.PIPE, shell=True)
        if verbose:
            print 'launching: %smongod %s --dbpath %s --logpath %s --port %i --logappend %s %s %s --fork'%(local, rs_param, dbpath, logpath, port, auth_param, log_param, extra)

        return ret


    def _launchMongoS(self, logpath, port, configdb, auth=False, loglevel=False, verbose=False):
        out = subprocess.PIPE
        if verbose:
            out = None

        auth_param = ''
        if auth:
            key_path = os.path.abspath(os.path.join(self.args['dir'], 'data/keyfile'))
            auth_param = '--keyFile %s'%key_path

        log_param = ''
        if loglevel:
            log_param = '-' + ''.join(['v']*loglevel)

        local = ''
        if self.args['local']:
            local = "./"

        ret = subprocess.call(['%smongos --logpath %s --port %i --configdb %s --logappend %s %s --fork'%(local, logpath, port, configdb, auth_param, log_param)], stderr=subprocess.STDOUT, stdout=subprocess.PIPE, shell=True)
        if verbose:
            print 'launching: %smongos --logpath %s --port %i --configdb %s --logappend %s %s --fork'%(local, logpath, port, configdb, auth_param, log_param)
        
        host = '%s:%i'%(self.hostname, port)
        t = threading.Thread(target=pingMongoDS, args=(host, 1.0, 30))
        t.start()
        if verbose:
            print "waiting for mongos to start up..."
        t.join()
        print "mongos at %s running."%host



if __name__ == '__main__':
    mongoLauncher = MongoLauncher()

