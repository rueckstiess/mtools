import os
import json

import pprint

from mtools.mlaunch.mlaunch import MLaunchTool
from collections import defaultdict
from operator import itemgetter

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


class Cluster(object):

    def __init__(self):
        self.mlaunch_tool = MLaunchTool()
        self.cluster_tree = {}
        self.tags = defaultdict(list)
        self.running = {}

    def discover(self, datadir='./data'):
        
        # replace path with absolute path
        self.dir = os.path.abspath(datadir)

        # let mlaunch_tool read the parameters
        self.mlaunch_tool.dir = self.dir
        if not self.mlaunch_tool.load_parameters():
            raise SystemExit("can't find %s, is this an mlaunch'ed directory?" % os.path.join(self.dir, '.mlaunch_startup'))
        self.args = self.mlaunch_tool.args

        # get shard names
        shard_names = self.mlaunch_tool._getShardNames()

        # determine number of nodes to inspect
        if 'sharded' in self.args and self.args['sharded'] != None:
            num_config = self.args['config']
            num_mongos = self.args['mongos']
            num_shards = len(shard_names)
        else:
            num_shards = 1
            num_config = 0
            num_mongos = 0

        num_nodes_per_shard = self.args['nodes'] if 'replicaset' in self.args and self.args['replicaset'] else 1
        if 'arbiter' in self.args and self.args['arbiter']:
            num_nodes_per_shard += 1

        num_nodes = num_shards * num_nodes_per_shard + num_config + num_mongos

        current_port = self.args['port']

        # tag all nodes with 'all'
        self.tags['all'].extend ( range(current_port, current_port + num_nodes) )

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
            self.tags['mongos'].append( port )
            self.tags['running' if running else 'down'].append( port )
            # add mongos to running map
            self.running[port] = running

        current_port += num_mongos

        # find all mongods (sharded, replicaset or single)
        if shard_names == None:
            shard_names = [ None ]

        for shard in shard_names:
            port_range = range(current_port, current_port + num_nodes_per_shard)

            # all of these are mongod nodes
            self.tags['mongod'].extend( port_range )

            if shard:
                # if this is a shard, store in cluster_tree and tag shard name
                self.cluster_tree.setdefault( 'shard', [] ).append( port_range )
                self.tags[shard].extend( port_range )

            if 'replicaset' in self.args and self.args['replicaset']:
                # treat replica set as a whole
                rs_name = shard if shard else self.args['replset']
                try:
                    mrsc = ReplicaSetConnection( ','.join( 'localhost:%i'%i for i in port_range ), replicaSet=rs_name )
                    # primary, secondaries, arbiters
                    self.tags['primary'].append( mrsc.primary[1] )
                    self.tags['secondary'].extend( map(itemgetter(1), mrsc.secondaries) )
                    self.tags['arbiter'].extend( map(itemgetter(1), mrsc.arbiters) )

                except ConnectionFailure:
                    # none of the nodes of the replica set is running, mark down then next shard
                    self.tags['down'].extend( port_range )
                    continue

            elif 'single' in self.args and self.args['single']:
                self.tags['single'].append( current_port )

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
                self.tags['running' if running else 'down'].append( port )

                # add node to running map
                self.running[port] = running

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
            self.tags['config'].append( port )
            self.tags['running' if running else 'down'].append( port )
            # add config server to running map
            self.running[port] = running

        current_port += num_mongos

        print self.cluster_tree


    def is_running(self, port):
        return self.running[port]


    def get_tagged(self, tags):
        nodes = set(self.tags['all'])

        for tag in tags:
            if type(tag) == tuple:
                # special case for tuple tags: mongos, config, shard. These can contain a number
                tag, number = tag
                assert (tag in ('mongos', 'config', 'shard'))

                branch = self.cluster_tree[tag][number]
                if hasattr(branch, '__iter__'):
                    subset = set(branch)
                else:
                    subset = set([branch])
            else:
                # otherwise use tags dict to get the subset
                subset = set(self.tags[tag])

            nodes = nodes.intersection(subset)

        return nodes



if __name__ == '__main__':
    cluster = Cluster()
    cluster.discover('./data')
    print cluster.get_tagged([('config', 1), 'running'])


