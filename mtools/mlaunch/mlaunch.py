#!/usr/bin/python

import argparse
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
from mtools.version import __version__

try:
    try:
        from pymongo import MongoClient as Connection
        from pymongo import MongoReplicaSetClient as ReplicaSetConnection
    except ImportError:
        from pymongo import Connection
        from pymongo import ReplicaSetConnection
    from pymongo.errors import ConnectionFailure, AutoReconnect, OperationFailure, ConfigurationError
except ImportError:
    raise ImportError("Can't import pymongo. See http://api.mongodb.org/python/current/ for instructions on how to install pymongo.")


def wait_for_host(host, interval=1, timeout=30, to_start=True):
    """ Ping a mongos or mongod every `interval` seconds until it responds, or `timeout` seconds have passed. If `to_start`
        is set to False, will wait for the node to shut down instead. This function can be called as a separate thread.
    """
    startTime = time.time()
    while True:
        if (time.time() - startTime) > timeout:
            return False
        try:
            # make connection and ping host
            con = Connection(host)
            con.admin.command('ping')
            if to_start:
                return True
            else:
                time.sleep(interval)
        except (ConnectionFailure, AutoReconnect) as e:
            if to_start:
                time.sleep(interval)
            else:
                return True


def shutdown_host(host_port):
    """ send the shutdown command to a mongod or mongos on given port. This function can be called as a separate thread. """
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

    def __init__(self):
        BaseCmdLineTool.__init__(self)

        self.hostname = socket.gethostname()

        # arguments
        self.args = None

        # startup parameters for each port
        self.startup_info = {}

        # data structures for the discovery feature
        self.cluster_tree = {}
        self.cluster_tags = defaultdict(list)
        self.cluster_running = {}

        # config docs for replica sets (key is replica set name)
        self.config_docs = {}

        # shard connection strings
        self.shard_connection_str = []


    def run(self, arguments=None):
        """ This is the main run method, called for all sub-commands and parameters.
            It sets up argument parsing, then calls the sub-command method with the same name.
        """

        # set up argument parsing in run, so that subsequent calls to run can call different sub-commands
        self.argparser = argparse.ArgumentParser()
        self.argparser.add_argument('--version', action='version', version="mtools version %s" % __version__)

        self.argparser.description = 'script to launch MongoDB stand-alone servers, replica sets and shards.'

        # make sure init is default command even when specifying arguments directly
        if arguments and arguments.startswith('-'):
            arguments = 'init ' + arguments
        
        # default sub-command is `init` if none provided
        elif len(sys.argv) > 1 and sys.argv[1].startswith('-') and sys.argv[1] not in ['-h', '--help']:
            sys.argv = sys.argv[0:1] + ['init'] + sys.argv[1:]

        # create command sub-parsers
        subparsers = self.argparser.add_subparsers(dest='command')
        self.argparser._action_groups[0].title = 'commands'
        self.argparser._action_groups[0].description = 'init is the default command and can be omitted. To get help on individual commands, run mlaunch [command] --help'
        
        # init command 
        init_parser = subparsers.add_parser('init', help='initialize and start MongoDB stand-alone instances, replica sets, or sharded clusters.',
            description='initialize and start MongoDB stand-alone instances, replica sets, or sharded clusters')

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

        # verbose, port, auth, binary path
        init_parser.add_argument('--verbose', action='store_true', default=False, help='outputs more verbose information.')
        init_parser.add_argument('--port', action='store', type=int, default=27017, help='port for mongod, start of port range in case of replica set or shards (default=27017)')
        init_parser.add_argument('--authentication', action='store_true', default=False, help='enable authentication and create a key file and admin user (admin/mypassword)')
        init_parser.add_argument('--binarypath', action='store', default=None, metavar='PATH', help='search for mongod/s binaries in the specified PATH.')
        init_parser.add_argument('--dir', action='store', default='./data', help='base directory to create db and log paths (default=./data/)')

        # start command
        start_parser = subparsers.add_parser('start', help='starts existing MongoDB instances. Example: "mlaunch start config" will start all config servers.', 
            description='starts existing MongoDB instances. Example: "mlaunch start config" will start all config servers.')
        start_parser.add_argument('tags', metavar='TAG', action='store', nargs='*', default=[], help='without tags, all non-running nodes will be restarted. Provide additional tags to narrow down the set of nodes to start.')
        start_parser.add_argument('--verbose', action='store_true', default=False, help='outputs more verbose information.')
        start_parser.add_argument('--dir', action='store', default='./data', help='base directory to start nodes (default=./data/)')

        # stop command
        stop_parser = subparsers.add_parser('stop', help='stops running MongoDB instances. Example: "mlaunch stop shard 2 secondary" will stop all secondary nodes of shard 2.',
            description='stops running MongoDB instances. Example: "mlaunch stop shard 2 secondary" will stop all secondary nodes of shard 2.')
        stop_parser.add_argument('tags', metavar='TAG', action='store', nargs='*', default=[], help='without tags, all running nodes will be stopped. Provide additional tags to narrow down the set of nodes to stop.')
        stop_parser.add_argument('--verbose', action='store_true', default=False, help='outputs more verbose information.')
        stop_parser.add_argument('--dir', action='store', default='./data', help='base directory to stop nodes (default=./data/)')
        
        # list command
        list_parser = subparsers.add_parser('list', help='list MongoDB instances for this configuration',
            description='list MongoDB instances for this configuration')
        list_parser.add_argument('--dir', action='store', default='./data', help='base directory to list nodes (default=./data/)')
        list_parser.add_argument('--verbose', action='store_true', default=False, help='outputs more verbose information.')

        # argparser is set up, now call base class run()
        BaseCmdLineTool.run(self, arguments, get_unknowns=True)

        # replace path with absolute path
        self.dir = os.path.abspath(self.args['dir'])

        # branch out in sub-commands
        getattr(self, self.args['command'])()



    # -- below are the main commands: init, start, stop, list


    def init(self):
        """ sub-command init. Branches out to sharded, replicaset or single node methods. """
        
        # check for existing environment. Only allow subsequent 'mlaunch init' if they are identical.
        if self._load_parameters():
            if self.loaded_args != self.args:
                raise SystemExit('A different environment already exists at %s.' % self.dir)

        # check if authentication is enabled, make key file       
        if self.args['authentication']:
            if not os.path.exists(self.dir):
                os.makedirs(self.dir)
            os.system('openssl rand -base64 753 > %s/keyfile'%self.dir)
            os.system('chmod 600 %s/keyfile'%self.dir)

        if self.args['sharded']:
            # construct startup strings
            self._construct_sharded()
            self.discover()

            shard_names = self._get_shard_names(self.args)

            # start mongod (shard and config) nodes and wait
            nodes = self.get_tagged(['mongod', 'down'])
            self._start_on_ports(nodes, wait=True)

            # initiate replica sets
            for shard in shard_names:
                # initiate replica set on first member
                members = sorted(self.get_tagged([shard]))
                self._initiate_replset(members[0], shard)

            # add mongos
            mongos = sorted(self.get_tagged(['mongos', 'down']))
            self._start_on_ports(mongos, wait=True)

            # add shards
            mongos = sorted(self.get_tagged(['mongos']))
            con = Connection('localhost:%i'%mongos[0])

            shards_to_add = len(self.shard_connection_str)
            nshards = con['config']['shards'].count()
            if nshards < shards_to_add:
                if self.args['replicaset']:
                    print "adding shards. can take up to 30 seconds..."
                else:
                    print "adding shards."

            while True:
                try:
                    nshards = con['config']['shards'].count()
                except:
                    nshards = 0
                if nshards >= shards_to_add:
                    break

                for conn_str in self.shard_connection_str:
                    try:
                        res = con['admin'].command({'addShard': conn_str})
                    except Exception as e:
                        if self.args['verbose']:
                            print e, ', will retry in a moment.'
                        continue

                    if res['ok']:
                        if self.args['verbose']:
                            print "shard %s added successfully"%conn_str
                            self.shard_connection_str.remove(conn_str)
                            break
                    else:
                        if self.args['verbose']:
                            print res, '- will retry'

                time.sleep(1)

            # if --mongos 0, kill the dummy mongos
            if self.args['mongos'] == 0:
                host_port = 'localhost:%s'%mongos[0]
                print "shutting down temporary mongos on %s" % host_port
                shutdown_host(host_port)

        
        elif self.args['single']:
            # construct startup string
            self._construct_single(self.dir, self.args['port'])
            self.discover()
            
            # start node
            nodes = self.get_tagged(['single', 'down'])
            self._start_on_ports(nodes, wait=False)

        
        elif self.args['replicaset']:
            # construct startup strings
            self._construct_replset(self.dir, self.args['port'], self.args['name'])
            self.discover()

            # start nodes and wait
            nodes = sorted(self.get_tagged(['mongod', 'down']))
            self._start_on_ports(nodes, wait=True)

            # initiate replica set
            self._initiate_replset(nodes[0], self.args['name'])


        # wait for all nodes to be running
        nodes = self.get_tagged(['all'])
        self.wait_for(nodes)

        # discover again, to get up-to-date info
        self.discover()

        # write out parameters
        if self.args['verbose']:
            print "writing .mlaunch_startup file."
        self._store_parameters()

        if self.args['verbose']:
            print "done."


    def stop(self):
        """ sub-command stop. This method will parse the list of tags and stop the matching nodes.
            Each tag has a set of nodes associated with it, and only the nodes matching all tags (intersection)
            will be shut down.
        """
        self.discover()

        matches = self._get_ports_from_args(self.args, 'running')
        if len(matches) == 0:
            raise SystemExit('no nodes stopped.')

        for port in matches:
            host_port = 'localhost:%i'%port
            if self.args['verbose']:
                print "shutting down %s" % host_port
            shutdown_host(host_port)

        # wait until nodes are all shut down
        self.wait_for(matches, to_start=False)
        print "%i node%s stopped." % (len(matches), '' if len(matches) == 1 else 's')

        # refresh discover
        self.discover()


    def start(self):
        """ sub-command start. TODO """
        self.discover()

        if not self.startup_info:
            # try to start nodes via init if all nodes are down
            if len(self.get_tagged(['down'])) == len(self.get_tagged(['all'])):
                self.args = self.loaded_args
                self.init()
                return 
            else:
                raise SystemExit("These nodes were created with an older version of mlaunch. To use the new 'start' command, kill all nodes manually, then run 'mlaunch start'. You only have to do this once.")

        matches = self._get_ports_from_args(self.args, 'down')
        if len(matches) == 0:
            raise SystemExit('no nodes started.')

        # start mongod and config servers first
        mongod_matches = self.get_tagged(['mongod'])
        mongod_matches = mongod_matches.union(self.get_tagged(['config']))
        mongod_matches = mongod_matches.intersection(matches)
        self._start_on_ports(mongod_matches, wait=True)

        # now start mongos
        mongos_matches = self.get_tagged(['mongos']).intersection(matches)
        self._start_on_ports(mongos_matches)

        # wait for all nodes to be running
        nodes = self.get_tagged(['all'])
        self.wait_for(nodes)

        # refresh discover
        self.discover()


    def list(self):
        """ sub-command list. Takes no further parameters. Will discover the current configuration and
            print a table of all the nodes with status and port.
        """
        self.discover()
        print_docs = []

        # mongos
        for node in sorted(self.get_tagged(['mongos'])):
            doc = {'process':'mongos', 'port':node, 'status': 'running' if self.cluster_running[node] else 'down'}
            print_docs.append( doc )
        
        if len(self.get_tagged(['mongos'])) > 0:
            print_docs.append( None )

        # configs
        for node in sorted(self.get_tagged(['config'])):
            doc = {'process':'config server', 'port':node, 'status': 'running' if self.cluster_running[node] else 'down'}
            print_docs.append( doc )
        
        if len(self.get_tagged(['config'])) > 0:
            print_docs.append( None )

        # mongod
        for shard in self._get_shard_names(self.loaded_args):
            tags = []
            replicaset = 'replicaset' in self.loaded_args and self.loaded_args['replicaset']
            padding = ''

            if shard:
                print_docs.append(shard)
                tags.append(shard)
                padding = '    '

            if replicaset:
                # primary
                primary = self.get_tagged(tags + ['primary', 'running'])
                if len(primary) > 0:
                    node = list(primary)[0]
                    print_docs.append( {'process':padding+'primary', 'port':node, 'status': 'running' if self.cluster_running[node] else 'down'} )
                
                # secondaries
                secondaries = self.get_tagged(tags + ['secondary', 'running'])
                for node in sorted(secondaries):
                    print_docs.append( {'process':padding+'secondary', 'port':node, 'status': 'running' if self.cluster_running[node] else 'down'} )
                
                # data-bearing nodes that are down or not in the replica set yet
                mongods = self.get_tagged(tags + ['mongod'])
                arbiters = self.get_tagged(tags + ['arbiter'])

                nodes = sorted(mongods - primary - secondaries - arbiters)
                for node in nodes:
                    print_docs.append( {'process':padding+'mongod', 'port':node, 'status': 'running' if self.cluster_running[node] else 'down'})

                # arbiters
                for node in arbiters:
                    print_docs.append( {'process':padding+'arbiter', 'port':node, 'status': 'running' if self.cluster_running[node] else 'down'} )

            else:
                nodes = self.get_tagged(tags + ['mongod'])
                if len(nodes) > 0:
                    node = nodes.pop()
                    print_docs.append( {'process':padding+'single', 'port':node, 'status': 'running' if self.cluster_running[node] else 'down'} )
            if shard:
                print_docs.append(None)


        if self.args['verbose']:
            # print tags as well
            for doc in filter(lambda x: type(x) == dict, print_docs):               
                tags = self.get_tags_of_port(doc['port'])
                doc['tags'] = ', '.join(tags)

        print_docs.append( None )   
        print         
        print_table(print_docs)


    
    # --- below are api helper methods, can be called after creating an MLaunchTool() object


    def discover(self):
        """ This method will go out to each of the processes and get their state. It builds the
            self.cluster_tree, self.cluster_tags, self.cluster_running data structures, needed
            for sub-commands start, stop, list.
        """
        if not self.args or not self.args['command']:
            return

        # load .mlaunch_startup file for start, stop, list, use current parameters for init
        if self.args['command'] == 'init':
            self.loaded_args, self.unknown_loaded_args = self.args, self.unknown_args
        else:
            if not self._load_parameters():
                raise SystemExit("can't read %s/.mlaunch_startup, use 'mlaunch init ...' first." % self.dir)

        # reset cluster_* variables
        self.cluster_tree = {}
        self.cluster_tags = defaultdict(list)
        self.cluster_running = {}
        
        # get shard names
        shard_names = self._get_shard_names(self.loaded_args)

        # some shortcut variables
        is_sharded = 'sharded' in self.loaded_args and self.loaded_args['sharded'] != None
        is_replicaset = 'replicaset' in self.loaded_args and self.loaded_args['replicaset']
        is_single = 'single' in self.loaded_args and self.loaded_args['single']
        has_arbiter = 'arbiter' in self.loaded_args and self.loaded_args['arbiter']

        # determine number of nodes to inspect
        if is_sharded:
            num_config = self.loaded_args['config']
            # at least one temp. mongos for adding shards, will be killed later on
            num_mongos = max(1, self.loaded_args['mongos'])
            num_shards = len(shard_names)
        else:
            num_shards = 1
            num_config = 0
            num_mongos = 0

        num_nodes_per_shard = self.loaded_args['nodes'] if is_replicaset else 1
        if has_arbiter:
            num_nodes_per_shard += 1

        num_nodes = num_shards * num_nodes_per_shard + num_config + num_mongos

        current_port = self.loaded_args['port']

        # tag all nodes with 'all'
        self.cluster_tags['all'].extend ( range(current_port, current_port + num_nodes) )

        # tag all nodes with their port number (as string) and whether they are running
        for port in range(current_port, current_port + num_nodes):
            self.cluster_tags[str(port)].append(port)

            running = self.is_running(port)
            self.cluster_running[port] = running
            self.cluster_tags['running' if running else 'down'].append(port)

        
        # find all mongos
        for i in range(num_mongos):
            port = i+current_port

            # add mongos to cluster tree
            self.cluster_tree.setdefault( 'mongos', [] ).append( port )
            # add mongos to tags
            self.cluster_tags['mongos'].append( port )

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

            if is_replicaset:
                # get replica set states
                rs_name = shard if shard else self.loaded_args['name']
                
                try:
                    mrsc = ReplicaSetConnection( ','.join( 'localhost:%i'%i for i in port_range ), replicaSet=rs_name )
                    # primary, secondaries, arbiters
                    if mrsc.primary:
                        self.cluster_tags['primary'].append( mrsc.primary[1] )
                    self.cluster_tags['secondary'].extend( map(itemgetter(1), mrsc.secondaries) )
                    self.cluster_tags['arbiter'].extend( map(itemgetter(1), mrsc.arbiters) )

                    # secondaries in cluster_tree (order is now important)
                    self.cluster_tree.setdefault( 'secondary', [] )
                    for i, secondary in enumerate(sorted(map(itemgetter(1), mrsc.secondaries))):
                        if len(self.cluster_tree['secondary']) <= i:
                            self.cluster_tree['secondary'].append([])
                        self.cluster_tree['secondary'][i].append(secondary)

                except (ConnectionFailure, ConfigurationError):
                    pass

            elif is_single:
                self.cluster_tags['single'].append( current_port )

            # increase current_port
            current_port += num_nodes_per_shard


        # find all config servers
        for i in range(num_config):
            port = i+current_port

            try:
                mc = Connection( 'localhost:%i'%port )
                running = True

            except ConnectionFailure:
                # node not reachable
                running = False

            # add config server to cluster tree
            self.cluster_tree.setdefault( 'config', [] ).append( port )
            # add config server to tags
            self.cluster_tags['config'].append( port )
            self.cluster_tags['mongod'].append( port )

        current_port += num_mongos


    def is_running(self, port):
        """ returns if a host on a specific port is running. """
        try:
            con = Connection('localhost:%s' % port)
            con.admin.command('ping')
            return True
        except (AutoReconnect, ConnectionFailure):
            return False


    def get_tagged(self, tags):
        """ The format for the tags list is tuples for tags: mongos, config, shard, secondary tags
            of the form (tag, number), e.g. ('mongos', 2) which references the second mongos 
            in the list. For all other tags, it is simply the string, e.g. 'primary'.
        """

        # if tags is a simple string, make it a list (note: tuples like ('mongos', 2) must be in a surrounding list)
        if not hasattr(tags, '__iter__') and type(tags) == str:
            tags = [ tags ]

        nodes = set(self.cluster_tags['all'])

        for tag in tags:
            if re.match(r'\w+ \d{1,2}', tag):
                # special case for tuple tags: mongos, config, shard, secondary. These can contain a number
                tag, number = tag.split()

                try:
                    branch = self.cluster_tree[tag][int(number)-1]
                except (IndexError, KeyError):
                    continue

                if hasattr(branch, '__iter__'):
                    subset = set(branch)
                else:
                    subset = set([branch])
            else:
                # otherwise use tags dict to get the subset
                subset = set(self.cluster_tags[tag])

            nodes = nodes.intersection(subset)

        return nodes

    

    def get_tags_of_port(self, port):
        """ get all tags related to a given port (inverse of what is stored in self.cluster_tags) """
        return sorted([tag for tag in self.cluster_tags if port in self.cluster_tags[tag] ])


    def wait_for(self, ports, interval=1.0, timeout=30, to_start=True):
        """ Given a list of ports, spawns up threads that will ping the host on each port concurrently. 
            Returns when all hosts are running (if to_start=True) / shut down (if to_start=False)
        """
        threads = []

        for port in ports:
            threads.append(threading.Thread(target=wait_for_host, args=('localhost:%i'%port, interval, timeout, to_start)))

        if self.args and 'verbose' in self.args and self.args['verbose']:
            print "waiting for nodes %..." % 'to start' if to_start else 'to shutdown'
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()



    # --- below here are internal helper methods, should not be called externally ---


    def _convert_u2b(self, obj):
        """ helper method to convert unicode back to plain text. """
        if isinstance(obj, dict):
            return dict([(self._convert_u2b(key), self._convert_u2b(value)) for key, value in obj.iteritems()])
        elif isinstance(obj, list):
            return [self._convert_u2b(element) for element in obj]
        elif isinstance(obj, unicode):
            return obj.encode('utf-8')
        else:
            return obj


    def _load_parameters(self):
        """ tries to load the .mlaunch_startup file that exists in each datadir. 
            Handles different protocol versions. 
        """
        datapath = self.dir

        startup_file = os.path.join(datapath, '.mlaunch_startup')
        if not os.path.exists(startup_file):
            return False

        in_dict = self._convert_u2b(json.load(open(startup_file, 'r')))

        # handle legacy version without versioned protocol
        if 'protocol_version' not in in_dict:
            in_dict['protocol_version'] = 1
            self.loaded_args = in_dict
            self.startup_info = {}

        elif in_dict['protocol_version'] == 2:
            self.startup_info = in_dict['startup_info']
            self.unknown_loaded_args = in_dict['unknown_args']
            self.loaded_args = in_dict['parsed_args']

        return True


    def _store_parameters(self):
        """ stores the startup parameters and config in the .mlaunch_startup file in the datadir. """
        datapath = self.dir

        out_dict = {
            'protocol_version': 2, 
            'mtools_version':  __version__,
            'parsed_args': self.args,
            'unknown_args': self.unknown_args,
            'startup_info': self.startup_info
        }

        if not os.path.exists(datapath):
            os.makedirs(datapath)
        try:
            json.dump(out_dict, open(os.path.join(datapath, '.mlaunch_startup'), 'w'), -1)
        except Exception:
            pass


    def _create_paths(self, basedir, name=None):
        """ create datadir and subdir paths. """
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


    def _get_ports_from_args(self, args, extra_tag):
        tags = []

        for tag1, tag2 in zip(args['tags'][:-1], args['tags'][1:]):
            if re.match('^\d{1,2}$', tag1):
                print "warning: ignoring numeric value '%s'" % tag1
                continue

            if re.match('^\d{1,2}$', tag2):
                if tag1 in ['mongos', 'shard', 'secondary', 'config']:
                    # combine tag with number, separate by string
                    tags.append( '%s %s' % (tag1, tag2) )
                    continue
                else: 
                    print "warning: ignoring numeric value '%s' after '%s'"  % (tag2, tag1)
            
            tags.append( tag1 )

        if len(args['tags']) > 0:
            tag = args['tags'][-1]
            if not re.match('^\d{1,2}$', tag):
                tags.append(tag)

        tags.append(extra_tag)

        matches = self.get_tagged(tags)
        return matches


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


    def _get_shard_names(self, args):
        """ get the shard names based on the self.args['sharded'] parameter. If it's a number, create
            shard names of type shard##, where ## is a 2-digit number. Returns a list [ None ] if 
            no shards are present.
        """

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


    
    def _start_on_ports(self, ports, wait=False):
        threads = []

        for port in ports:
            command_str = self.startup_info[str(port)]
            ret = subprocess.call([command_str], stderr=subprocess.STDOUT, stdout=subprocess.PIPE, shell=True)
            
            binary = command_str.split()[0]
            if '--configsvr' in command_str:
                binary = 'config server'

            if self.args['verbose']:
                print "launching: %s" % command_str
            else:
                print "launching: %s on port %s" % (binary, port)

            if ret > 0:
                print "can't start process, return code %i."%ret
                print "tried to launch: %s" % command_str
                raise SystemExit

        if wait:
            self.wait_for(ports)


    def _initiate_replset(self, port, name):
        # initiate replica set
        if not self.args['replicaset']:
            return 

        con = Connection('localhost:%i'%port)
        try:
            rs_status = con['admin'].command({'replSetGetStatus': 1})
        except OperationFailure, e:
            con['admin'].command({'replSetInitiate':self.config_docs[name]})
            if self.args['verbose']:
                print "initializing replica set '%s' with configuration: %s" % (name, self.config_docs[name])
            print "replica set '%s' initialized." % name



    # --- below are command line constructor methods, that build the command line strings to be called

    def _construct_sharded(self):
        """ start a sharded cluster. """

        num_mongos = self.args['mongos'] if self.args['mongos'] > 0 else 1
        shard_names = self._get_shard_names(self.args)

        # create shards as stand-alones or replica sets
        nextport = self.args['port'] + num_mongos
        for shard in shard_names:
            if self.args['single']:
                self.shard_connection_str.append( self._construct_single(self.dir, nextport, name=shard) )
                nextport += 1
            elif self.args['replicaset']:
                self.shard_connection_str.append( self._construct_replset(self.dir, nextport, shard) )
                nextport += self.args['nodes']
                if self.args['arbiter']:
                    nextport += 1

        # start up config server(s)
        config_string = []
        config_names = ['config1', 'config2', 'config3'] if self.args['config'] == 3 else ['config']
            
        for name in config_names:
            self._construct_config(self.dir, nextport, name)
            config_string.append('%s:%i'%(self.hostname, nextport))
            nextport += 1
        
        # multiple mongos use <datadir>/mongos/ as subdir for log files
        if num_mongos > 1:
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
            self._construct_mongos(os.path.join(self.dir, mongos_logfile), nextport, ','.join(config_string))

            nextport += 1


    def _construct_replset(self, basedir, portstart, name):
        """ start a replica set, either for sharded cluster or by itself. """

        self.config_docs[name] = {'_id':name, 'members':[]}

        for i in range(self.args['nodes']):
            datapath = self._create_paths(basedir, '%s/rs%i'%(name, i+1))
            self._construct_mongod(os.path.join(datapath, 'db'), os.path.join(datapath, 'mongod.log'), portstart+i, replset=name)
        
            host = '%s:%i'%(self.hostname, portstart+i)
            self.config_docs[name]['members'].append({'_id':len(self.config_docs[name]['members']), 'host':host, 'votes':int(len(self.config_docs[name]['members']) < 7 - int(self.args['arbiter']))})

        # launch arbiter if True
        if self.args['arbiter']:
            datapath = self._create_paths(basedir, '%s/arb'%(name))
            self._construct_mongod(os.path.join(datapath, 'db'), os.path.join(datapath, 'mongod.log'), portstart+self.args['nodes'], replset=name)
            
            host = '%s:%i'%(self.hostname, portstart+self.args['nodes'])
            self.config_docs[name]['members'].append({'_id':len(self.config_docs[name]['members']), 'host':host, 'arbiterOnly': True})

        return name + '/' + ','.join([c['host'] for c in self.config_docs[name]['members']])



    def _construct_config(self, basedir, port, name=None):
        """ start a config server """
        datapath = self._create_paths(basedir, name)
        self._construct_mongod(os.path.join(datapath, 'db'), os.path.join(datapath, 'mongod.log'), port, replset=None, extra='--configsvr')



    def _construct_single(self, basedir, port, name=None):
        """ start a single node, either for shards or as a stand-alone. """
        datapath = self._create_paths(basedir, name)
        self._construct_mongod(os.path.join(datapath, 'db'), os.path.join(datapath, 'mongod.log'), port, replset=None)

        host = '%s:%i'%(self.hostname, port)

        return host


    def _construct_mongod(self, dbpath, logpath, port, replset=None, extra=''):
        """ starts a mongod process. """
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

        # store parameters in startup_info
        self.startup_info[str(port)] = command_str



    def _construct_mongos(self, logpath, port, configdb):
        """ start a mongos process. """
        extra = ''
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

        # store parameters in startup_info
        self.startup_info[str(port)] = command_str



if __name__ == '__main__':
    tool = MLaunchTool()
    tool.run()
