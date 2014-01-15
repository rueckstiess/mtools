#!/usr/bin/python

import subprocess
import threading
import os, time, sys, re
import socket
import json
import re

from collections import defaultdict
from operator import itemgetter

from mtools.util.cmdlinetool import BaseCmdLineTool
from mtools.util.print_table import print_table

try:
    try:
        from pymongo import MongoClient as Connection
        from pymongo import MongoReplicaSetClient as ReplicaSetConnection
    except ImportError:
        from pymongo import Connection
        from pymongo import ReplicaSetConnection
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


def shutdownMongoDS(host_port):
    """ send the shutdown command to a mongod or mongos on given port. """
    try:
        mc = Connection(host_port)
        try:
            mc.admin.command('shutdown', force=True)
        except AutoReconnect:
            pass
    except ConnectionFailure:
        pass
    else:
        mc.close()


class MLaunchTool(BaseCmdLineTool):

    # additional arguments that can be passed on to mongos, all others will only go to mongod
    mongos_arguments = ['quiet', 'logappend', 'pidfilepath', 'keyFile', 'nounixsocket', 'syslog', \
                        'nohttpinterface', 'test', 'upgrade', 'ipv6', 'jsonp', 'noscripting']

    def __init__(self):
        BaseCmdLineTool.__init__(self)

        self.hostname = socket.gethostname()
        
        self.startup_info = {}

        # data structures for the discovery feature
        self.cluster_tree = {}
        self.cluster_tags = defaultdict(list)
        self.cluster_running = {}


        self.argparser.description = 'script to launch MongoDB stand-alone servers, replica sets and shards. You must specify either --single or --replicaset. \
            In addition to the optional arguments below, you can specify any mongos and mongod argument, which will be passed on, if the process accepts it.'

        # default sub-command is `start` if not provided
        if len(sys.argv) > 1 and sys.argv[1].startswith('-') and sys.argv[1] not in ['-h', '--help']:
            # not sub command given, redirect all options to main parser
            init_redirected = True
            init_parser = self.argparser
            init_parser.add_argument('--command', action='store_const', const='init', default='init')
        else:
            # create sub-parser for the command `start`
            init_redirected = False
            subparsers = self.argparser.add_subparsers(dest='command')
            init_parser = subparsers.add_parser('init', help='initialize and start MongoDB stand-alone instances, replica sets, or sharded clusters')

        # general argparser arguments
        self.argparser.add_argument('--dir', action='store', default='./data', help='base directory to create db and log paths (default=./data/)')


        # --- start command ---

        # either single or replica set
        me_group = init_parser.add_mutually_exclusive_group(required=True)
        me_group.add_argument('--single', action='store_true', help='creates a single stand-alone mongod instance')
        me_group.add_argument('--replicaset', action='store_true', help='creates replica set with several mongod instances')

        # replica set arguments
        init_parser.add_argument('--nodes', action='store', metavar='NUM', type=int, default=3, help='adds NUM data nodes to replica set (requires --replicaset, default=3)')
        init_parser.add_argument('--arbiter', action='store_true', default=False, help='adds arbiter to replica set (requires --replicaset)')
        init_parser.add_argument('--name', action='store', metavar='NAME', default='replset', help='name for replica set (default=replset)')
        
        # sharded clusters
        init_parser.add_argument('--sharded', action='store', nargs='*', metavar='N', help='creates a sharded setup consisting of several singles or replica sets. Provide either list of shard names or number of shards (default=1)')
        init_parser.add_argument('--config', action='store', default=1, type=int, metavar='NUM', choices=[1, 3], help='adds NUM config servers to sharded setup (requires --sharded, NUM must be 1 or 3, default=1)')
        init_parser.add_argument('--mongos', action='store', default=1, type=int, metavar='NUM', help='starts NUM mongos processes (requires --sharded, default=1)')

        # dir, verbose, port, auth
        init_parser.add_argument('--verbose', action='store_true', default=False, help='outputs information about the launch')
        init_parser.add_argument('--port', action='store', type=int, default=27017, help='port for mongod, start of port range in case of replica set or shards (default=27017)')
        init_parser.add_argument('--authentication', action='store_true', default=False, help='enable authentication and create a key file and admin user (admin/mypassword)')
        init_parser.add_argument('--binarypath', action='store', default=None, metavar='PATH', help='search for mongod/s binaries in the specified PATH.')

        if not init_redirected:
            # start command
            start_parser = subparsers.add_parser('start', help='start existing MongoDB instances')
            start_parser.add_argument('tags', action='store', nargs='*', default=[])

            # stop command
            stop_parser = subparsers.add_parser('stop', help='stop running MongoDB instances')
            stop_parser.add_argument('tags', action='store', nargs='*', default=[])

            # list command
            list_parser = subparsers.add_parser('list', help='list MongoDB instances')



    def run(self, arguments=None):
        BaseCmdLineTool.run(self, arguments, get_unknowns=True)

        # replace path with absolute path
        self.dir = os.path.abspath(self.args['dir'])

        # branch out in sub-commands
        getattr(self, self.args['command'])()


    def stop(self):
        self.params = self.load_parameters()
        if not self.params:
            raise SystemExit("can't read %s/.mlaunch_startup. Is this an mlaunch'ed cluster?" % self.dir)

        self.discover()

        tags = []

        for tag1, tag2 in zip(self.args['tags'][:-1], self.args['tags'][1:]):
            print tag1, tag2
            if re.match('^\d+$', tag1):
                continue

            if re.match('^\d+$', tag2):
                if tag1 in ['mongos', 'shard', 'secondary', 'mongod', 'config']:
                    tags.append( (tag1, int(tag2)-1) )
                    continue
            
            tags.append( tag1 )

        if len(self.args['tags']) > 0:
            tag = self.args['tags'][-1]
            if not re.match('^\d+$', tag):
                tags.append(tag)

        tags.append('running')

        matches = self.get_tagged(tags)

        print tags, matches

        for port in matches:
            host_port = 'localhost:%i'%port
            shutdownMongoDS(host_port)


    def start(self):
        self.load_parameters()
        # todo


    def list(self):

        self.params = self.load_parameters()
        if not self.params:
            raise SystemExit("can't read %s/.mlaunch_startup. Is this an mlaunch'ed cluster?" % self.dir)

        self.discover()
        print_docs = []
        # mongos
        for node in self.get_tagged(['mongos']):
            doc = {'process':'mongos', 'port':node, 'status': 'running' if self.is_running(node) else 'down'}
            print_docs.append( doc )
        
        if len(self.get_tagged(['mongos'])) > 0:
            print_docs.append( None )

        # mongod
        for shard in self._getShardNames(self.params):
            tags = []
            replicaset = 'replicaset' in self.params and self.params['replicaset']
            padding = ''

            if shard:
                print_docs.append(shard)
                tags.append(shard)
                padding = '   '

            if replicaset:
                # primary
                nodes = self.get_tagged(tags + ['primary'])
                if len(nodes) > 0:
                    node = nodes.pop()
                    print_docs.append( {'process':padding+'primary', 'port':node, 'status': 'running' if self.is_running(node) else 'down'} )
                
                # secondaries
                nodes = self.get_tagged(tags + ['secondary'])
                for node in nodes:
                    print_docs.append( {'process':padding+'secondary', 'port':node, 'status': 'running' if self.is_running(node) else 'down'} )
                
                # arbiters
                nodes = self.get_tagged(tags + ['arbiter'])
                for node in nodes:
                    print_docs.append( {'process':padding+'arbiter', 'port':node, 'status': 'running' if self.is_running(node) else 'down'} )

                # replica set members that are down
                nodes = self.get_tagged(tags + ['mongod', 'down'])
                for node in nodes:
                    print_docs.append( {'process':padding+'mongod', 'port':node, 'status': 'down'})

            else:
                nodes = self.get_tagged(tags + ['mongod'])
                if len(nodes) > 0:
                    node = nodes.pop()
                    print_docs.append( {'process':padding+'single', 'port':node, 'status': 'running' if self.is_running(node) else 'down'} )
            if shard:
                print_docs.append(None)

        # configs
        for node in self.get_tagged(['config']):
            doc = {'process':'config server', 'port':node, 'status': 'running' if self.is_running(node) else 'down'}
            print_docs.append( doc )
        
        if len(self.get_tagged(['config'])) > 0:
            print_docs.append( None )

        print_docs.append( None )            
        print_table(print_docs)


    def init(self):
        # check if authentication is enabled, make key file       
        if self.args['authentication']:
            if not os.path.exists(self.dir):
                os.makedirs(self.dir)
            os.system('openssl rand -base64 753 > %s/keyfile'%self.dir)
            os.system('chmod 600 %s/keyfile'%self.dir)

        if self.args['sharded']:
            self._launchSharded()
        elif self.args['single']:
            self._launchSingle(self.dir, self.args['port'])
        elif self.args['replicaset']:
            self._launchReplSet(self.dir, self.args['port'], self.args['name'])

        # write out parameters
        self.store_parameters()


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
        datapath = self.dir

        startup_file = os.path.join(datapath, '.mlaunch_startup')
        if os.path.exists(startup_file):
            return self.convert_u2b(json.load(open(startup_file, 'r')))
        else: 
            return False


    def store_parameters(self):
        datapath = self.dir

        if not os.path.exists(datapath):
            os.makedirs(datapath)
        try:
            json.dump(self.args, open(os.path.join(datapath, '.mlaunch_startup'), 'w'), -1)
        except Exception:
            pass

    def check_port_availability(self, port, binary):
        if pingMongoDS('%s:%i' % (self.hostname, port), 1, 1) is True:
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



    def discover(self):
        
        # get shard names
        shard_names = self._getShardNames(self.params)

        # determine number of nodes to inspect
        if 'sharded' in self.params and self.params['sharded'] != None:
            num_config = self.params['config']
            num_mongos = self.params['mongos']
            num_shards = len(shard_names)
        else:
            num_shards = 1
            num_config = 0
            num_mongos = 0

        num_nodes_per_shard = self.params['nodes'] if 'replicaset' in self.params and self.params['replicaset'] else 1
        if 'arbiter' in self.params and self.params['arbiter']:
            num_nodes_per_shard += 1

        num_nodes = num_shards * num_nodes_per_shard + num_config + num_mongos

        current_port = self.params['port']

        # tag all nodes with 'all'
        self.cluster_tags['all'].extend ( range(current_port, current_port + num_nodes) )

        # tag all nodes with their port number
        for port in range(current_port, current_port + num_nodes):
            self.cluster_tags['%s'%port].append(port)

        # find all mongos
        for i in range(num_mongos):
            port = i+current_port

            try:
                mc = Connection( 'localhost:%i'%port )
                # if this is not a mongos, something went wrong, fail
                assert (mc.is_mongos)
                running = True

            except ConnectionFailure:
                # node not reachable
                running = False

            # add mongos to cluster tree
            self.cluster_tree.setdefault( 'mongos', [] ).append( port )
            # add mongos to tags
            self.cluster_tags['mongos'].append( port )
            self.cluster_tags['running' if running else 'down'].append( port )
            # add mongos to running map
            self.cluster_running[port] = running

        current_port += num_mongos

        # find all mongods (sharded, replicaset or single)
        if shard_names == None:
            shard_names = [ None ]

        for shard in shard_names:
            port_range = range(current_port, current_port + num_nodes_per_shard)

            # all of these are mongod nodes
            self.cluster_tags['mongod'].extend( port_range )

            if shard:
                # if this is a shard, store in cluster_tree and tag shard name
                self.cluster_tree.setdefault( 'shard', [] ).append( port_range )
                self.cluster_tags[shard].extend( port_range )

            if 'replicaset' in self.params and self.params['replicaset']:
                # treat replica set as a whole
                rs_name = shard if shard else self.params['name']
                try:
                    mrsc = ReplicaSetConnection( ','.join( 'localhost:%i'%i for i in port_range ), replicaSet=rs_name )
                    # primary, secondaries, arbiters
                    if mrsc.primary:
                        self.cluster_tags['primary'].append( mrsc.primary[1] )
                    self.cluster_tags['secondary'].extend( map(itemgetter(1), mrsc.secondaries) )
                    self.cluster_tags['arbiter'].extend( map(itemgetter(1), mrsc.arbiters) )

                    # split by secondary position
                    self.cluster_tree.setdefault( 'secondary', [] )
                    for i, secondary in enumerate(map(itemgetter(1), mrsc.secondaries)):
                        if len(self.cluster_tree['secondary']) <= i:
                            self.cluster_tree['secondary'].append([])
                        self.cluster_tree['secondary'][i].append(secondary)

                except ConnectionFailure:
                    # none of the nodes of the replica set is running, mark down then next shard
                    self.cluster_tags['down'].extend( port_range )
                    current_port += num_nodes_per_shard
                    continue

            elif 'single' in self.params and self.params['single']:
                self.cluster_tags['single'].append( current_port )

            # now determine which nodes are running / down
            for i in range(num_nodes_per_shard):
                port = i+current_port
                
                try:
                    mc = Connection( 'localhost:%i'% port )
                    running = True

                except ConnectionFailure:
                    # node not reachable
                    running = False

                # add mongod to tags
                self.cluster_tags['running' if running else 'down'].append( port )

                # add node to running map
                self.cluster_running[port] = running

            # increase current_port
            current_port += num_nodes_per_shard


        # find all config servers
        for i in range(num_config):
            port = i+current_port

            try:
                mc = Connection( 'localhost:%i'%port )
                # if this is not a config server, something went wrong, fail
                assert (u'config' in mc.database_names())
                running = True

            except ConnectionFailure:
                # node not reachable
                running = False

            # add config server to cluster tree
            self.cluster_tree.setdefault( 'config', [] ).append( port )
            # add config server to tags
            self.cluster_tags['config'].append( port )
            self.cluster_tags['running' if running else 'down'].append( port )
            # add config server to running map
            self.cluster_running[port] = running

        current_port += num_mongos



    def is_running(self, port):
        return self.cluster_running[port]


    def get_tagged(self, tags):
        """ The format for the tags list is tuples for tags: mongos, config, shard, secondary tags
            of the form (tag, number), e.g. ('mongos', 2) which references the second mongos 
            in the list. For all other tags, it is simply the string, e.g. 'primary'.
        """

        nodes = set(self.cluster_tags['all'])

        for tag in tags:
            if type(tag) == tuple:
                # special case for tuple tags: mongos, config, shard, secondary. These can contain a number
                tag, number = tag
                assert (tag in ('mongos', 'config', 'shard', 'secondary'))

                branch = self.cluster_tree[tag][number]
                if hasattr(branch, '__iter__'):
                    subset = set(branch)
                else:
                    subset = set([branch])
            else:
                # otherwise use tags dict to get the subset
                subset = set(self.cluster_tags[tag])

            nodes = nodes.intersection(subset)

        return nodes



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


    def _getShardNames(self, args):
        # start up shards
        if 'sharded' in args and args['sharded'] and len(args['sharded']) == 1:
            try:
                # --sharded was a number, name shards shard01, shard02, ... (only works with replica sets)
                n_shards = int(args['sharded'][0])
                shard_names = ['shard%.2i'%(i+1) for i in range(n_shards)]
            except ValueError, e:
                # --sharded was a string, use it as name for the one shard 
                shard_names = args['sharded']
        else:
            shard_names = [ None ]
        return shard_names


    def _launchSharded(self):

        if self.args['mongos'] == 0:
            # start a temporary mongos and kill it again later
            num_mongos = 1
            kill_mongos = True
        else:
            num_mongos = self.args['mongos']
            kill_mongos = False

        shard_names = self._getShardNames(self.args)


        # create shards as stand-alones or replica sets
        nextport = self.args['port'] + num_mongos
        for p, shard in enumerate(shard_names):
            if self.args['single']:
                shard_names[p] = self._launchSingle(self.dir, nextport, name=shard)
                nextport += 1
            elif self.args['replicaset']:
                shard_names[p] = self._launchReplSet(self.dir, nextport, shard)
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
            self._launchConfig(self.dir, nextport, name)
            config_string.append('%s:%i'%(self.hostname, nextport))
            nextport += 1
        
        # multiple mongos use <datadir>/mongos/ as subdir for log files
        if self.args['mongos'] > 1:
            mongosdir = os.path.join(self.dir, 'mongos')
            if not os.path.exists(mongosdir):
                os.makedirs(mongosdir) 


        # start up mongos, but put them to the front of the port range
        nextport = self.args['port']
        for i in range(num_mongos):
            if num_mongos > 1:
                mongos_logfile = 'mongos/mongos_%i.log' % nextport
            else:
                mongos_logfile = 'mongos.log'
            self._launchMongoS(os.path.join(self.dir, mongos_logfile), nextport, ','.join(config_string))
            if i == 0: 
                # store host/port of first mongos (use localhost)
                self.mongos_host = 'localhost:%i' % nextport

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

        # if mongos was temporary, kill it again
        if kill_mongos:
            print "shutting down temporary mongos on %s" % self.mongos_host
            shutdownMongoDS(self.mongos_host)


    def _launchReplSet(self, basedir, portstart, name):
        threads = []
        configDoc = {'_id':name, 'members':[]}

        for i in range(self.args['nodes']):
            datapath = self._createPaths(basedir, '%s/rs%i'%(name, i+1))
            self._launchMongoD(os.path.join(datapath, 'db'), os.path.join(datapath, 'mongod.log'), portstart+i, replset=name)
        
            host = '%s:%i'%(self.hostname, portstart+i)
            configDoc['members'].append({'_id':len(configDoc['members']), 'host':host, 'votes':int(len(configDoc['members']) < 7 - int(self.args['arbiter']))})
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
            key_path = os.path.abspath(os.path.join(self.dir, 'keyfile'))
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
            key_path = os.path.abspath(os.path.join(self.dir, 'keyfile'))
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
