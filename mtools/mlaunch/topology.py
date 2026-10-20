#!/usr/bin/env python3
"""Topology builders for mlaunch."""

import os
import time

from packaging import version
from pymongo.errors import OperationFailure


class TopologyMixin(object):
    """Build command lines for single nodes, replica sets, and shards."""

    def _initiate_replset(self, port, name, maxwait=30):
        """Initiate replica set."""
        if not self.args['replicaset'] and name != 'configRepl':
            if self.args['verbose']:
                print('Skipping replica set initialization for %s' % name)
            return

        con = self.client(self._node_address(port), directConnection=True)
        try:
            rs_status = con['admin'].command({'replSetGetStatus': 1})
            return rs_status
        except OperationFailure:
            # not initiated yet

            if self.args['verbose']:
                print("initializing replica set '%s' with configuration: %s"
                      % (name, self.config_docs[name]))

            initiated = False
            for i in range(maxwait):
                try:
                    con['admin'].command({'replSetInitiate':
                                          self.config_docs[name]})
                    initiated = True
                    break
                except OperationFailure as e:
                    print('Replica set initialization failed: %s - will retry' % e)
                    time.sleep(1)

            if initiated:
                print(f"replica set '{name}' initialized.")
            else:
                raise SystemExit(f"replica set '{name}' failed to initialize.")

    def _add_user(self, port, name, password, database, roles):
        con = self.client(self._node_address(port),
                          serverSelectionTimeoutMS=10000)

        if database == "$external":
            password = None

        try:
            con[database].command("createUser", name, pwd=password, roles=roles)
        except OperationFailure as e:
            raise e

    def _construct_cmdlines(self):
        """
        Top-level _construct_* method.

        From here, it will branch out to the different cases:
        _construct_sharded, _construct_replicaset, _construct_single. These can
        themselves call each other (for example sharded needs to create the
        shards with either replicaset or single node). At the lowest level, the
        construct_mongod, _mongos, _config will create the actual command line
        strings and store them in self.startup_info.
        """
        if self.args['sharded']:
            # construct startup string for sharded environments
            self._construct_sharded()

        elif self.args['single']:
            # construct startup string for single node environment
            self._construct_single(self.dir, self.args['port'])

        elif self.args['replicaset']:
            # construct startup strings for a non-sharded replica set
            self._construct_replset(self.dir, self.args['port'],
                                    self.args['name'],
                                    list(range(self.args['nodes'])),
                                    self.args['arbiter'])

        # discover current setup
        self.discover()

    def _construct_sharded(self):
        """Construct command line strings for a sharded cluster."""

        num_mongos = self.args['mongos'] if self.args['mongos'] > 0 else 1
        shard_names = self._get_shard_names(self.args)

        # create shards as stand-alones or replica sets
        nextport = self.args['port'] + num_mongos
        for shard in shard_names:
            if self.args['single']:
                errmsg = " \n * In MongoDB 3.6 and above a Shard must be " \
                         "made up of a replica set. Please use --replicaset " \
                         "option when starting a sharded cluster.*"
                raise SystemExit(errmsg)
            elif self.args['replicaset']:
                self.shard_connection_str.append(
                    self._construct_replset(
                        self.dir, nextport, shard,
                        num_nodes=list(range(self.args['nodes'])),
                        arbiter=self.args['arbiter'], extra='--shardsvr'))
                nextport += self.args['nodes']
                if self.args['arbiter']:
                    nextport += 1

        # start up config server(s)
        config_string = []

        # CSRS config servers (MongoDB >=3.1.0)
        config_string.append(
            self._construct_config(self.dir, nextport, "configRepl", True))

        # multiple mongos use <datadir>/mongos/ as subdir for log files
        if num_mongos > 1:
            mongosdir = os.path.join(self.dir, 'mongos')
            if not os.path.exists(mongosdir):
                if self.args['verbose']:
                    print("creating directory: %s" % mongosdir)
                os.makedirs(mongosdir)

        # start up mongos, but put them to the front of the port range
        nextport = self.args['port']
        for i in range(num_mongos):
            if num_mongos > 1:
                mongos_logfile = 'mongos/mongos_%i.log' % nextport
            else:
                mongos_logfile = 'mongos.log'
            self._construct_mongos(os.path.join(self.dir, mongos_logfile),
                                   nextport, ','.join(config_string))

            nextport += 1

    def _construct_replset(self, basedir, portstart, name, num_nodes,
                           arbiter, extra=''):
        """
        Construct command line strings for a replicaset.

        Handles single set or sharded cluster.
        """
        self.config_docs[name] = {'_id': name, 'members': []}

        # Construct individual replica set nodes
        for i in num_nodes:
            datapath = self._create_paths(basedir, '%s/rs%i' % (name, i + 1))
            self._construct_mongod(os.path.join(datapath, 'db'),
                                   os.path.join(datapath, 'mongod.log'),
                                   portstart + i, replset=name, extra=extra)

            host = '%s:%i' % (self.args['hostname'], portstart + i)
            member_config = {
                '_id': len(self.config_docs[name]['members']),
                'host': host,
            }

            # First node gets increased priority.
            if i == 0 and self.args['priority']:
                member_config['priority'] = 10

            if i >= 7:
                member_config['votes'] = 0
                member_config['priority'] = 0

            self.config_docs[name]['members'].append(member_config)

        # launch arbiter if True
        if arbiter:
            datapath = self._create_paths(basedir, '%s/arb' % (name))
            self._construct_mongod(os.path.join(datapath, 'db'),
                                   os.path.join(datapath, 'mongod.log'),
                                   portstart + self.args['nodes'],
                                   replset=name)

            host = '%s:%i' % (self.args['hostname'],
                              portstart + self.args['nodes'])
            (self.config_docs[name]['members']
             .append({'_id': len(self.config_docs[name]['members']),
                      'host': host,
                      'arbiterOnly': True}))

        return (name + '/' +
                ','.join([c['host']
                          for c in self.config_docs[name]['members']]))

    def _construct_config(self, basedir, port, name=None, isreplset=False):
        """Construct command line strings for a config server."""
        if isreplset:
            return self._construct_replset(basedir=basedir, portstart=port,
                                           name=name,
                                           num_nodes=list(range(
                                               self.args['config'])),
                                           arbiter=False, extra='--configsvr')
        else:
            datapath = self._create_paths(basedir, name)
            self._construct_mongod(os.path.join(datapath, 'db'),
                                   os.path.join(datapath, 'mongod.log'),
                                   port, replset=None, extra='--configsvr')

    def _construct_single(self, basedir, port, name=None, extra=''):
        """
        Construct command line strings for a single node.

        Handles shards and stand-alones.
        """
        datapath = self._create_paths(basedir, name)
        self._construct_mongod(os.path.join(datapath, 'db'),
                               os.path.join(datapath, 'mongod.log'), port,
                               replset=None, extra=extra)

        host = '%s:%i' % (self.args['hostname'], port)

        return host

    def _oplog_min_retention_supported(self):
        """True when this mongod accepts ``--oplogMinRetentionHours``.

        The option arrived in MongoDB 4.4. An undetected version is
        reported as ``0.0.0``, which mlaunch treats as current.
        """
        current = getattr(self, 'current_version', None)
        if not current:
            return False
        parsed = version.parse(current)
        return (parsed == version.parse('0.0.0') or
                parsed >= version.parse('4.4.0'))

    def _construct_mongod(self, dbpath, logpath, port, replset=None, extra=''):
        """Construct command line strings for mongod process."""
        rs_param = ''
        if replset:
            rs_param = '--replSet %s' % replset

        auth_param = ''
        if self.args['auth']:
            auth_param = ''
            if '--keyFile' not in self.unknown_args:
                key_path = os.path.abspath(os.path.join(self.dir, 'keyfile'))
                auth_param = f'{auth_param} --keyFile "{key_path}"'

        if self.unknown_args:
            config = '--configsvr' in extra
            owned = self._owned_server_args('mongod', extra=extra,
                                            replset=replset)
            extra = self._filter_valid_arguments(
                self.unknown_args, "mongod", config=config, owned=owned
            ) + ' ' + extra

        # 0.5 GB leaves room for several mongods on one machine.
        # A cache percent is an alternative to the GB size.
        if ('--wiredTigerCacheSizeGB' not in extra and
                '--wiredTigerCacheSizePct' not in extra and
                self._filter_valid_arguments(['--wiredTigerCacheSizeGB'],
                                             'mongod')):
            extra += ' --wiredTigerCacheSizeGB 0.5 '

        # MongoDB 4.4 keeps an oplog entry until the oplog has reached its
        # maximum size and the entry is older than this many hours. The
        # oplog can grow past that size to satisfy the window.
        if ('--oplogMinRetentionHours' not in extra and
                self._oplog_min_retention_supported()):
            extra += ' --oplogMinRetentionHours 1 '

        # Exit with error if hostname is specified but not bind_ip options
        if (self.args['hostname'] != 'localhost'
                and version.parse(self.current_version) >= version.parse("3.6.0")
                and (self.args['sharded'] or self.args['replicaset'])
                and '--bind_ip' not in extra):
            os.removedirs(dbpath)
            errmsg = " \n * If hostname is specified, please include "\
                "'--bind_ip_all' or '--bind_ip' options when deploying "\
                "replica sets or sharded cluster with MongoDB version 3.6.0 "\
                "or greater"
            raise SystemExit(errmsg)

        extra += self._get_ssl_server_args()
        extra += self._get_tls_server_args()

        path = self.args['binarypath'] or ''
        if os.name == 'nt':
            newdbpath = dbpath.replace('\\', '\\\\')
            newlogpath = logpath.replace('\\', '\\\\')
            command_str = ("start /b \"\" \"%s\" %s --dbpath \"%s\" "
                           " --logpath \"%s\" --port %i "
                           "%s %s" % (os.path.join(path, 'mongod.exe'),
                                      rs_param, newdbpath, newlogpath, port,
                                      auth_param, extra))
        else:
            # 8.2+ on macOS rejects --fork. Omit it and let _start_on_ports
            # detach the process and wait until it is listening.
            fork_param = '' if self._macos_fork_unsupported() else '--fork '
            command_str = ("\"%s\" %s --dbpath \"%s\" --logpath \"%s\" "
                           "--port %i %s"
                           "%s %s" % (os.path.join(path, 'mongod'), rs_param,
                                      dbpath, logpath, port, fork_param,
                                      auth_param, extra))

        # store parameters in startup_info
        self.startup_info[str(port)] = command_str

    def _construct_mongos(self, logpath, port, configdb):
        """Construct command line strings for a mongos process."""
        extra = ''

        auth_param = ''
        if self.args['auth']:
            auth_param = ''
            if '--keyFile' not in self.unknown_args:
                key_path = os.path.abspath(os.path.join(self.dir, 'keyfile'))
                auth_param = f'{auth_param} --keyFile "{key_path}"'

        if self.unknown_args:
            owned = self._owned_server_args('mongos', extra=extra)
            extra = self._filter_valid_arguments(
                self.unknown_args, "mongos", owned=owned) + extra

        extra += ' ' + self._get_ssl_server_args()
        extra += ' ' + self._get_tls_server_args()

        path = self.args['binarypath'] or ''
        if os.name == 'nt':
            newlogpath = logpath.replace('\\', '\\\\')
            command_str = ("start /b %s --logpath \"%s\" --port %i --configdb %s "
                           "%s %s " % (os.path.join(path, 'mongos'),
                                       newlogpath, port, configdb,
                                       auth_param, extra))
        else:
            fork_param = '' if self._macos_fork_unsupported() else ' --fork'
            command_str = ("%s --logpath \"%s\" --port %i --configdb %s %s %s%s"
                           % (os.path.join(path, 'mongos'), logpath,
                              port, configdb, auth_param, extra, fork_param))

        # store parameters in startup_info
        self.startup_info[str(port)] = command_str
