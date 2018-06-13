#!/usr/bin/env python

from __future__ import print_function

import argparse
import json
import os
import re
import signal
import socket
import ssl
import subprocess
import sys
import threading
import time
import warnings
from collections import defaultdict
from operator import itemgetter

import psutil
from mtools.util import OrderedDict
from mtools.util.cmdlinetool import BaseCmdLineTool
from mtools.util.print_table import print_table
from mtools.version import __version__

try:
    import Queue
except ImportError:
    import queue as Queue

try:
    try:
        from pymongo import MongoClient as Connection
        from pymongo import version_tuple as pymongo_version
        from bson import SON
        from io import BytesIO
        from distutils.version import LooseVersion
    except ImportError:
        from pymongo import Connection
        from pymongo import version_tuple as pymongo_version
        from bson import SON

    from pymongo.errors import ConnectionFailure, AutoReconnect
    from pymongo.errors import OperationFailure, ConfigurationError
except ImportError:
    raise ImportError("Can't import pymongo. See "
                      "http://api.mongodb.org/python/current/ for "
                      "instructions on how to install pymongo.")


class MongoConnection(Connection):
    """
    MongoConnection class.

    Wrapper around Connection (itself conditionally a MongoClient or
    pymongo.Connection) to specify timeout if pymongo >= 3.0.
    """

    def __init__(self, *args, **kwargs):
        if pymongo_version[0] >= 3:
            if 'serverSelectionTimeoutMS' not in kwargs:
                kwargs['serverSelectionTimeoutMS'] = 1
        else:
            if 'serverSelectionTimeoutMS' in kwargs:
                kwargs.remove('serverSelectionTimeoutMS')

        Connection.__init__(self, *args, **kwargs)


def wait_for_host(port, interval=1, timeout=30, to_start=True, queue=None,
                  ssl_pymongo_options=None):
    """
    Ping server and wait for response.

    Ping a mongod or mongos every `interval` seconds until it responds, or
    `timeout` seconds have passed. If `to_start` is set to False, will wait for
    the node to shut down instead. This function can be called as a separate
    thread.

    If queue is provided, it will place the results in the message queue and
    return, otherwise it will just return the result directly.
    """
    host = 'localhost:%i' % port
    start_time = time.time()
    while True:
        if (time.time() - start_time) > timeout:
            if queue:
                queue.put_nowait((port, False))
            return False
        try:
            # make connection and ping host
            con = MongoConnection(host, **(ssl_pymongo_options or {}))
            con.admin.command('ping')

            if to_start:
                if queue:
                    queue.put_nowait((port, True))
                return True
            else:
                time.sleep(interval)
        except Exception:
            if to_start:
                time.sleep(interval)
            else:
                if queue:
                    queue.put_nowait((port, True))
                return True


def shutdown_host(port, username=None, password=None, authdb=None):
    """
    Send the shutdown command to a mongod or mongos on given port.

    This function can be called as a separate thread.
    """
    host = 'localhost:%i' % port
    try:
        mc = MongoConnection(host)
        try:
            if username and password and authdb:
                if authdb != "admin":
                    raise RuntimeError("given username/password is not for "
                                       "admin database")
                else:
                    try:
                        mc.admin.authenticate(name=username, password=password)
                    except OperationFailure:
                        # perhaps auth is not required
                        pass

            mc.admin.command('shutdown', force=True)
        except AutoReconnect:
            pass
        except OperationFailure:
            print("Error: cannot authenticate to shut down %s." % host)
            return

    except ConnectionFailure:
        pass
    else:
        mc.close()


class MLaunchTool(BaseCmdLineTool):
    UNDOCUMENTED_MONGOD_ARGS = ['--nopreallocj']

    def __init__(self, test=False):
        BaseCmdLineTool.__init__(self)

        # arguments
        self.args = None

        # startup parameters for each port
        self.startup_info = {}

        # data structures for the discovery feature
        self.cluster_tree = {}
        self.cluster_tags = defaultdict(list)
        self.cluster_running = {}

        # memoize ignored arguments passed to different binaries
        self.ignored_arguments = {}

        # config docs for replica sets (key is replica set name)
        self.config_docs = {}

        # shard connection strings
        self.shard_connection_str = []

        # ssl configuration to start mongod or mongos, or create a MongoClient
        self.ssl_server_args = ''
        self.ssl_pymongo_options = {}

        # indicate if running in testing mode
        self.test = test

    def run(self, arguments=None):
        """
        Main run method.

        Called for all sub-commands and parameters. It sets up argument
        parsing, then calls the sub-command method with the same name.
        """
        # set up argument parsing in run, so that subsequent calls
        # to run can call different sub-commands
        self.argparser = argparse.ArgumentParser()
        self.argparser.add_argument('--version', action='version',
                                    version="mtools version {0} || Python {1}".format(
                                        __version__, sys.version))
        self.argparser.add_argument('--no-progressbar', action='store_true',
                                    default=False,
                                    help='disables progress bar')

        self.argparser.description = ('script to launch MongoDB stand-alone '
                                      'servers, replica sets and shards.')

        # make sure init is default command even when specifying
        # arguments directly
        if arguments and arguments.startswith('-'):
            arguments = 'init ' + arguments

        # default sub-command is `init` if none provided
        elif (len(sys.argv) > 1 and sys.argv[1].startswith('-') and
                sys.argv[1] not in ['-h', '--help', '--version']):
            sys.argv = sys.argv[0:1] + ['init'] + sys.argv[1:]

        # create command sub-parsers
        subparsers = self.argparser.add_subparsers(dest='command')
        self.argparser._action_groups[0].title = 'commands'
        self.argparser._action_groups[0].description = \
            ('init is the default command and can be omitted. To get help on '
             'individual commands, run mlaunch <command> --help. Command line '
             'arguments which are not handled by mlaunch will be passed '
             'through to mongod/mongos if those options are listed in the '
             '--help output for the current binary. For example: '
             '--storageEngine, --logappend, or --config.')

        # init command
        helptext = ('initialize a new MongoDB environment and start '
                    'stand-alone instances, replica sets, or sharded '
                    'clusters.')
        desc = ('Initialize a new MongoDB environment and start stand-alone '
                'instances, replica sets, or sharded clusters. Command line '
                'arguments which are not handled by mlaunch will be passed '
                'through to mongod/mongos if those options are listed in the '
                '--help output for the current binary. For example: '
                '--storageEngine, --logappend, or --config.')
        init_parser = subparsers.add_parser('init', help=helptext,
                                            description=desc)

        # either single or replica set
        me_group = init_parser.add_mutually_exclusive_group(required=True)
        me_group.add_argument('--single', action='store_true',
                              help=('creates a single stand-alone mongod '
                                    'instance'))
        me_group.add_argument('--replicaset', action='store_true',
                              help=('creates replica set with several mongod '
                                    'instances'))

        # replica set arguments
        init_parser.add_argument('--nodes', action='store', metavar='NUM',
                                 type=int, default=3,
                                 help=('adds NUM data nodes to replica set '
                                       '(requires --replicaset, default=3)'))
        init_parser.add_argument('--arbiter', action='store_true',
                                 default=False,
                                 help=('adds arbiter to replica set '
                                       '(requires --replicaset)'))
        init_parser.add_argument('--name', action='store', metavar='NAME',
                                 default='replset',
                                 help='name for replica set (default=replset)')
        init_parser.add_argument('--priority', action='store_true',
                                 default=False,
                                 help='make lowest-port member primary')

        # sharded clusters
        init_parser.add_argument('--sharded', '--shards', action='store',
                                 nargs='+', metavar='N',
                                 help=('creates a sharded setup consisting of '
                                       'several singles or replica sets. '
                                       'Provide either list of shard names or '
                                       'number of shards.'))
        init_parser.add_argument('--config', action='store', default=-1,
                                 type=int, metavar='NUM',
                                 help=('adds NUM config servers to sharded '
                                       'setup (requires --sharded, default=1, '
                                       'with --csrs default=3)'))
        init_parser.add_argument('--csrs', default=False, action='store_true',
                                 help=('deploy config servers as a replica '
                                       'set (requires MongoDB >= 3.2.0)'))
        init_parser.add_argument('--mongos', action='store', default=1,
                                 type=int, metavar='NUM',
                                 help=('starts NUM mongos processes (requires '
                                       '--sharded, default=1)'))

        # verbose, port, binary path
        init_parser.add_argument('--verbose', action='store_true',
                                 default=False,
                                 help='outputs more verbose information.')
        init_parser.add_argument('--port', action='store', type=int,
                                 default=27017,
                                 help=('port for mongod, start of port range '
                                       'in case of replica set or shards '
                                       '(default=27017)'))
        init_parser.add_argument('--binarypath', action='store', default=None,
                                 metavar='PATH',
                                 help=('search for mongod/s binaries in the '
                                       'specified PATH.'))
        init_parser.add_argument('--dir', action='store', default='./data',
                                 help=('base directory to create db and log '
                                       'paths (default=./data/)'))
        init_parser.add_argument('--hostname', action='store',
                                 default='localhost',
                                 help=('override hostname for replica set '
                                       'configuration'))

        # authentication, users, roles
        self._default_auth_roles = ['dbAdminAnyDatabase',
                                    'readWriteAnyDatabase',
                                    'userAdminAnyDatabase',
                                    'clusterAdmin']
        init_parser.add_argument('--auth', action='store_true', default=False,
                                 help=('enable authentication and create a '
                                       'key file and admin user '
                                       '(default=user/password)'))
        init_parser.add_argument('--username', action='store', type=str,
                                 default='user',
                                 help=('username to add (requires --auth, '
                                       'default=user)'))
        init_parser.add_argument('--password', action='store', type=str,
                                 default='password',
                                 help=('password for given username (requires '
                                       '--auth, default=password)'))
        init_parser.add_argument('--auth-db', action='store', type=str,
                                 default='admin', metavar='DB',
                                 help=('database where user will be added '
                                       '(requires --auth, default=admin)'))
        init_parser.add_argument('--auth-roles', action='store',
                                 default=self._default_auth_roles,
                                 metavar='ROLE', nargs='*',
                                 help=('admin user''s privilege roles; note'
                                       'that the clusterAdmin role is '
                                       'required to run the stop command '
                                       '(requires --auth, default="%s")'
                                       % ' '.join(self._default_auth_roles)))
        init_parser.add_argument('--no-initial-user', action='store_false',
                                 default=True, dest='initial-user',
                                 help=('create an initial user if auth is '
                                       'enabled (default=true)'))

        # ssl
        def is_file(arg):
            if not os.path.exists(os.path.expanduser(arg)):
                init_parser.error("The file [%s] does not exist" % arg)
            return arg

        ssl_args = init_parser.add_argument_group('SSL Options')
        ssl_args.add_argument('--sslCAFile',
                              help='Certificate Authority file for SSL',
                              type=is_file)
        ssl_args.add_argument('--sslCRLFile',
                              help='Certificate Revocation List file for SSL',
                              type=is_file)
        ssl_args.add_argument('--sslAllowInvalidHostnames',
                              action='store_true',
                              help=('allow client and server certificates to '
                                    'provide non-matching hostnames'))
        ssl_args.add_argument('--sslAllowInvalidCertificates',
                              action='store_true',
                              help=('allow client or server connections with '
                                    'invalid certificates'))

        ssl_server_args = init_parser.add_argument_group('Server SSL Options')
        ssl_server_args.add_argument('--sslOnNormalPorts', action='store_true',
                                     help='use ssl on configured ports')
        ssl_server_args.add_argument('--sslMode',
                                     help='set the SSL operation mode',
                                     choices=('disabled allowSSL preferSSL '
                                              'requireSSL'.split()))
        ssl_server_args.add_argument('--sslPEMKeyFile',
                                     help='PEM file for ssl', type=is_file)
        ssl_server_args.add_argument('--sslPEMKeyPassword',
                                     help='PEM file password')
        ssl_server_args.add_argument('--sslClusterFile',
                                     help=('key file for internal SSL '
                                           'authentication'), type=is_file)
        ssl_server_args.add_argument('--sslClusterPassword',
                                     help=('internal authentication key '
                                           'file password'))
        ssl_server_args.add_argument('--sslDisabledProtocols',
                                     help=('comma separated list of TLS '
                                           'protocols to disable '
                                           '[TLS1_0,TLS1_1,TLS1_2]'))
        ssl_server_args.add_argument('--sslWeakCertificateValidation',
                                     action='store_true',
                                     help=('allow client to connect without '
                                           'presenting a certificate'))
        ssl_server_args.add_argument(('--sslAllowConnectionsWithout'
                                      'Certificates'), action='store_true',
                                     help=('allow client to connect without '
                                           'presenting a certificate'))
        ssl_server_args.add_argument('--sslFIPSMode', action='store_true',
                                     help='activate FIPS 140-2 mode')

        ssl_client_args = init_parser.add_argument_group('Client SSL Options')
        ssl_client_args.add_argument('--sslClientCertificate',
                                     help='client certificate file for ssl',
                                     type=is_file)
        ssl_client_args.add_argument('--sslClientPEMKeyFile',
                                     help='client PEM file for ssl',
                                     type=is_file)
        ssl_client_args.add_argument('--sslClientPEMKeyPassword',
                                     help='client PEM file password')

        self.ssl_args = ssl_args
        self.ssl_client_args = ssl_client_args
        self.ssl_server_args = ssl_server_args

        # start command
        start_parser = subparsers.add_parser('start',
                                             help=('starts existing MongoDB '
                                                   'instances. Example: '
                                                   '"mlaunch start config" '
                                                   'will start all config '
                                                   'servers.'),
                                             description=('starts existing '
                                                          'MongoDB instances. '
                                                          'Example: "mlaunch '
                                                          'start config" will '
                                                          'start all config '
                                                          'servers.'))
        start_parser.add_argument('tags', metavar='TAG', action='store',
                                  nargs='*', default=[],
                                  help=('without tags, all non-running nodes '
                                        'will be restarted. Provide '
                                        'additional tags to narrow down the '
                                        'set of nodes to start.'))
        start_parser.add_argument('--verbose', action='store_true',
                                  default=False,
                                  help='outputs more verbose information.')
        start_parser.add_argument('--dir', action='store', default='./data',
                                  help=('base directory to start nodes '
                                        '(default=./data/)'))
        start_parser.add_argument('--binarypath', action='store',
                                  default=None, metavar='PATH',
                                  help=('search for mongod/s binaries in the '
                                        'specified PATH.'))

        # stop command
        helptext = ('stops running MongoDB instances. Example: "mlaunch stop '
                    'shard 2 secondary" will stop all secondary nodes '
                    'of shard 2.')
        desc = ('stops running MongoDB instances with the shutdown command. '
                'Example: "mlaunch stop shard 2 secondary" will stop all '
                'secondary nodes of shard 2.')
        stop_parser = subparsers.add_parser('stop',
                                            help=helptext,
                                            description=desc)
        helptext = ('without tags, all running nodes will be stopped. '
                    'Provide additional tags to narrow down the set of '
                    'nodes to stop.')
        stop_parser.add_argument('tags', metavar='TAG', action='store',
                                 nargs='*', default=[], help=helptext)
        stop_parser.add_argument('--verbose', action='store_true',
                                 default=False,
                                 help='outputs more verbose information.')
        stop_parser.add_argument('--dir', action='store', default='./data',
                                 help=('base directory to stop nodes '
                                       '(default=./data/)'))

        # restart command
        desc = ('stops running MongoDB instances with the shutdown command. '
                'Then restarts the stopped instances.')
        restart_parser = subparsers.add_parser('restart',
                                               help=('stops, then restarts '
                                                     'MongoDB instances.'),
                                               description=desc)
        restart_parser.add_argument('tags', metavar='TAG', action='store',
                                    nargs='*', default=[],
                                    help=('without tags, all non-running '
                                          'nodes will be restarted. Provide '
                                          'additional tags to narrow down the '
                                          'set of nodes to start.'))
        restart_parser.add_argument('--verbose', action='store_true',
                                    default=False,
                                    help='outputs more verbose information.')
        restart_parser.add_argument('--dir', action='store', default='./data',
                                    help=('base directory to restart nodes '
                                          '(default=./data/)'))
        restart_parser.add_argument('--binarypath', action='store',
                                    default=None, metavar='PATH',
                                    help=('search for mongod/s binaries in '
                                          'the specified PATH.'))

        # list command
        list_parser = subparsers.add_parser('list',
                                            help=('list MongoDB instances of '
                                                  'this environment.'),
                                            description=('list MongoDB '
                                                         'instances of this '
                                                         'environment.'))
        list_parser.add_argument('--dir', action='store', default='./data',
                                 help=('base directory to list nodes '
                                       '(default=./data/)'))
        list_parser.add_argument('--tags', action='store_true', default=False,
                                 help=('outputs the tags for each instance. '
                                       'Tags can be used to target instances '
                                       'for start/stop/kill.'))
        list_parser.add_argument('--startup', action='store_true',
                                 default=False,
                                 help=('outputs the startup command lines for '
                                       'each instance.'))
        list_parser.add_argument('--verbose', action='store_true',
                                 default=False, help='alias for --tags.')

        # list command
        helptext = ('kills (or sends another signal to) MongoDB instances '
                    'of this environment.')
        desc = ('kills (or sends another signal to) MongoDB instances '
                'of this environment.')
        kill_parser = subparsers.add_parser('kill', help=helptext,
                                            description=desc)
        kill_parser.add_argument('tags', metavar='TAG', action='store',
                                 nargs='*', default=[],
                                 help=('without tags, all running nodes will '
                                       'be killed. Provide additional tags to '
                                       'narrow down the set of nodes to '
                                       'kill.'))
        kill_parser.add_argument('--dir', action='store', default='./data',
                                 help=('base directory to kill nodes '
                                       '(default=./data/)'))
        kill_parser.add_argument('--signal', action='store', default=15,
                                 help=('signal to send to processes, '
                                       'default=15 (SIGTERM)'))
        kill_parser.add_argument('--verbose', action='store_true',
                                 default=False,
                                 help='outputs more verbose information.')

        # argparser is set up, now call base class run()
        BaseCmdLineTool.run(self, arguments, get_unknowns=True)

        # conditions on argument combinations
        if (self.args['command'] == 'init' and
                'single' in self.args and self.args['single']):
            if self.args['arbiter']:
                self.argparser.error("can't specify --arbiter for "
                                     "single nodes.")

        # replace path with absolute path, but store relative path as well
        self.relative_dir = self.args['dir']
        self.dir = os.path.abspath(self.args['dir'])
        self.args['dir'] = self.dir

        # branch out in sub-commands
        getattr(self, self.args['command'])()

    # -- below are the main commands: init, start, stop, list, kill
    def init(self):
        """
        Sub-command init.

        Branches out to sharded, replicaset or single node methods.
        """
        # check for existing environment. Only allow subsequent
        # 'mlaunch init' if they are identical.
        if self._load_parameters():
            if self.loaded_args != self.args:
                raise SystemExit('A different environment already exists '
                                 'at %s.' % self.dir)
            first_init = False
        else:
            first_init = True

        self.ssl_pymongo_options = self._get_ssl_pymongo_options(self.args)

        if (self._get_ssl_server_args() and not
                self.args['sslAllowConnectionsWithoutCertificates'] and not
                self.args['sslClientCertificate'] and not
                self.args['sslClientPEMKeyFile']):
            sys.stderr.write('warning: server requires certificates but no'
                             ' --sslClientCertificate provided\n')

        # number of default config servers
        if self.args['config'] == -1:
            self.args['config'] = 1

        # Check if config replicaset is applicable to this version
        current_version = self.getMongoDVersion()

        # Exit with error if --csrs is set and MongoDB < 3.1.0
        if (self.args['csrs'] and
                LooseVersion(current_version) < LooseVersion("3.1.0") and
                LooseVersion(current_version) != LooseVersion("0.0.0")):
            errmsg = (" \n * The '--csrs' option requires MongoDB version "
                      "3.2.0 or greater, the current version is %s.\n"
                      % current_version)
            raise SystemExit(errmsg)

        # add the 'csrs' parameter as default for MongoDB >= 3.3.0
        if (LooseVersion(current_version) >= LooseVersion("3.3.0") or
            LooseVersion(current_version) == LooseVersion("0.0.0")):
            self.args['csrs'] = True

        # construct startup strings
        self._construct_cmdlines()

        # write out parameters
        if self.args['verbose']:
            print("writing .mlaunch_startup file.")
        self._store_parameters()

        # exit if running in testing mode
        if self.test:
            sys.exit(0)

        # check if authentication is enabled, make key file
        if self.args['auth'] and first_init:
            if not os.path.exists(self.dir):
                os.makedirs(self.dir)
            keyfile = os.path.join(self.dir, "keyfile")
            os.system('openssl rand -base64 753 > %s' % keyfile)
            if os.name != 'nt':
                os.system('chmod 600 %s' % keyfile)

        # if not all ports are free, complain and suggest alternatives.
        all_ports = self.get_tagged(['all'])
        ports_avail = self.wait_for(all_ports, 1, 1, to_start=False)

        if not all(map(itemgetter(1), ports_avail)):
            dir_addon = (' --dir %s' % self.relative_dir
                         if self.relative_dir != './data' else '')
            errmsg = ('\nThe following ports are not available: %s\n\n'
                      % ', '.join([str(p[0])
                                   for p in ports_avail if not p[1]]))
            errmsg += (" * If you want to restart nodes from this "
                       "environment, use 'mlaunch start%s' instead.\n"
                       % dir_addon)
            errmsg += (" * If the ports are used by a different mlaunch "
                       "environment, stop those first with 'mlaunch stop "
                       "--dir <env>'.\n")
            errmsg += (" * You can also specify a different port range with "
                       "an additional '--port <startport>'\n")
            raise SystemExit(errmsg)

        if self.args['sharded']:

            shard_names = self._get_shard_names(self.args)

            # start mongod (shard and config) nodes and wait
            nodes = self.get_tagged(['mongod', 'down'])
            self._start_on_ports(nodes, wait=True, override_auth=True)

            # initiate replica sets if init is called for the first time
            if first_init:
                if self.args['csrs']:
                    # Initiate config servers in a replicaset
                    if self.args['verbose']:
                        print('Initiating config server replica set.')
                    members = sorted(self.get_tagged(["config"]))
                    self._initiate_replset(members[0], "configRepl")
                for shard in shard_names:
                    # initiate replica set on first member
                    if self.args['verbose']:
                        print('Initiating shard replica set %s.' % shard)
                    members = sorted(self.get_tagged([shard]))
                    self._initiate_replset(members[0], shard)

            # add mongos
            mongos = sorted(self.get_tagged(['mongos', 'down']))
            self._start_on_ports(mongos, wait=True, override_auth=True)

            if first_init:
                # add shards
                mongos = sorted(self.get_tagged(['mongos']))
                con = self.client('localhost:%i' % mongos[0])

                shards_to_add = len(self.shard_connection_str)
                nshards = con['config']['shards'].count()
                if nshards < shards_to_add:
                    if self.args['replicaset']:
                        print("adding shards. can take up to 30 seconds...")
                    else:
                        print("adding shards.")

                shard_conns_and_names = list(zip(self.shard_connection_str,
                                            shard_names))
                while True:
                    try:
                        nshards = con['config']['shards'].count()
                    except Exception:
                        nshards = 0
                    if nshards >= shards_to_add:
                        break

                    for conn_str, name in shard_conns_and_names:
                        try:
                            res = con['admin'].command(SON([('addShard',
                                                             conn_str),
                                                       ('name', name)]))
                        except Exception as e:
                            if self.args['verbose']:
                                print('%s will retry in a moment.' % e)
                            continue

                        if res['ok']:
                            if self.args['verbose']:
                                print("shard %s added successfully" % conn_str)
                                shard_conns_and_names.remove((conn_str, name))
                                break
                        else:
                            if self.args['verbose']:
                                print(res + ' - will retry')

                    time.sleep(1)

        elif self.args['single']:
            # just start node
            nodes = self.get_tagged(['single', 'down'])
            self._start_on_ports(nodes, wait=False)

        elif self.args['replicaset']:
            # start nodes and wait
            nodes = sorted(self.get_tagged(['mongod', 'down']))
            self._start_on_ports(nodes, wait=True)

            # initiate replica set
            if first_init:
                self._initiate_replset(nodes[0], self.args['name'])

        # wait for all nodes to be running
        nodes = self.get_tagged(['all'])
        self.wait_for(nodes)

        # now that nodes are running, add admin user if authentication enabled
        if self.args['auth'] and self.args['initial-user'] and first_init:
            self.discover()
            nodes = []

            if self.args['sharded']:
                nodes = self.get_tagged(['mongos', 'running'])
            elif self.args['single']:
                nodes = self.get_tagged(['single', 'running'])
            elif self.args['replicaset']:
                print("waiting for primary to add a user.")
                if self._wait_for_primary():
                    nodes = self.get_tagged(['primary', 'running'])
                else:
                    raise RuntimeError("failed to find a primary, so adding "
                                       "admin user isn't possible")

            if not nodes:
                raise RuntimeError("can't connect to server, so adding admin "
                                   "user isn't possible")

            if "clusterAdmin" not in self.args['auth_roles']:
                warnings.warn("the stop command will not work with auth "
                              "because the user does not have the "
                              "clusterAdmin role")

            self._add_user(sorted(nodes)[0], name=self.args['username'],
                           password=self.args['password'],
                           database=self.args['auth_db'],
                           roles=self.args['auth_roles'])

            if self.args['verbose']:
                print("added user %s on %s database" % (self.args['username'],
                                                        self.args['auth_db']))

        # in sharded env, if --mongos 0, kill the dummy mongos
        if self.args['sharded'] and self.args['mongos'] == 0:
            port = self.args['port']
            print("shutting down temporary mongos on localhost:%s" % port)
            username = self.args['username'] if self.args['auth'] else None
            password = self.args['password'] if self.args['auth'] else None
            authdb = self.args['auth_db'] if self.args['auth'] else None
            shutdown_host(port, username, password, authdb)

        # discover again, to get up-to-date info
        self.discover()

        # for sharded authenticated clusters, restart after first_init
        # to enable auth
        if self.args['sharded'] and self.args['auth'] and first_init:
            if self.args['verbose']:
                print("restarting cluster to enable auth...")
            self.restart()

        if self.args['auth'] and self.args['initial-user']:
            print('Username "%s", password "%s"'
                  % (self.args['username'], self.args['password']))

        if self.args['verbose']:
            print("done.")

    # Get the "mongod" version, useful for checking for support or
    # non-support of features.
    # Normally we expect to get back something like "db version v3.4.0",
    # but with release candidates we get abck something like
    # "db version v3.4.0-rc2". This code exact the "major.minor.revision"
    # part of the string
    def getMongoDVersion(self):
        binary = "mongod"
        if self.args and self.args.get('binarypath'):
            binary = os.path.join(self.args['binarypath'], binary)
        try:
            ret = subprocess.Popen(['%s' % binary, '--version'],
                                   stderr=subprocess.STDOUT,
                                   stdout=subprocess.PIPE, shell=False)
        except OSError as e:
            print('Failed to launch %s' % binary)
            raise e

        out, err = ret.communicate()
        if ret.returncode:
            raise OSError(out or err)

        buf = BytesIO(out)
        current_version = buf.readline().strip().decode('utf-8')
        # remove prefix "db version v"
        if current_version.rindex('v') > 0:
            current_version = current_version.rpartition('v')[2]

        # remove suffix making assumption that all release candidates
        # equal revision 0
        try:
            if current_version.rindex('-') > 0:  # release candidate?
                current_version = current_version.rpartition('-')[0]
        except Exception:
            pass

        if self.args['verbose']:
            print("Detected mongod version: %s" % current_version)
        return current_version

    def client(self, host_and_port, **kwargs):
        kwargs.update(self.ssl_pymongo_options)
        return MongoConnection(host_and_port, **kwargs)

    def stop(self):
        """
        Sub-command stop.

        Parse the list of tags and stop the matching nodes. Each tag has a set
        of nodes associated with it, and only the nodes matching all tags
        (intersection) will be shut down.

        Currently this is an alias for kill()
        """
        self.kill()

    def start(self):
        """Sub-command start."""
        self.discover()

        # startup_info only gets loaded from protocol version 2 on,
        # check if it's loaded
        if not self.startup_info:
            # hack to make environment startable with older protocol
            # versions < 2: try to start nodes via init if all nodes are down
            if len(self.get_tagged(['down'])) == len(self.get_tagged(['all'])):
                self.args = self.loaded_args
                print("upgrading mlaunch environment meta-data.")
                return self.init()
            else:
                raise SystemExit("These nodes were created with an older "
                                 "version of mlaunch (v1.1.1 or below). To "
                                 "upgrade this environment and make use of "
                                 "the start/stop/list commands, stop all "
                                 "nodes manually, then run 'mlaunch start' "
                                 "again. You only have to do this once.")

        # if new unknown_args are present, compare them with loaded ones
        # (here we can be certain of protocol v2+)
        if (self.args['binarypath'] is not None or
                (self.unknown_args and
                 set(self.unknown_args) != set(self.loaded_unknown_args))):

            # store current args, use self.args from file (self.loaded_args)
            start_args = self.args
            self.args = self.loaded_args

            self.args['binarypath'] = start_args['binarypath']
            # construct new startup strings with updated unknown args.
            # They are for this start only and will not be persisted in
            # the .mlaunch_startup file
            self._construct_cmdlines()

            # reset to original args for this start command
            self.args = start_args

        matches = self._get_ports_from_args(self.args, 'down')
        if len(matches) == 0:
            raise SystemExit('no nodes started.')

        # start config servers first
        config_matches = self.get_tagged(['config']).intersection(matches)
        self._start_on_ports(config_matches, wait=True)

        # start shards next
        mongod_matches = (self.get_tagged(['mongod']) -
                          self.get_tagged(['config']))
        mongod_matches = mongod_matches.intersection(matches)
        self._start_on_ports(mongod_matches, wait=True)

        # now start mongos
        mongos_matches = self.get_tagged(['mongos']).intersection(matches)
        self._start_on_ports(mongos_matches)

        # wait for all matched nodes to be running
        self.wait_for(matches)

        # refresh discover
        self.discover()

    def list(self):
        """
        Sub-command list.

        Takes no further parameters. Will discover the current configuration
        and print a table of all the nodes with status and port.
        """
        self.discover()
        print_docs = []

        # mongos
        for node in sorted(self.get_tagged(['mongos'])):
            doc = OrderedDict([('process', 'mongos'), ('port', node),
                              ('status', 'running'
                               if self.cluster_running[node] else 'down')])
            print_docs.append(doc)

        if len(self.get_tagged(['mongos'])) > 0:
            print_docs.append(None)

        # configs
        for node in sorted(self.get_tagged(['config'])):
            doc = OrderedDict([('process', 'config server'),
                              ('port', node),
                              ('status', 'running'
                               if self.cluster_running[node] else 'down')])
            print_docs.append(doc)

        if len(self.get_tagged(['config'])) > 0:
            print_docs.append(None)

        # mongod
        for shard in self._get_shard_names(self.loaded_args):
            tags = []
            replicaset = ('replicaset' in self.loaded_args and
                          self.loaded_args['replicaset'])
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
                    print_docs.append(OrderedDict
                                      ([('process', padding + 'primary'),
                                        ('port', node),
                                        ('status', 'running'
                                         if self.cluster_running[node]
                                         else 'down')]))

                # secondaries
                secondaries = self.get_tagged(tags + ['secondary', 'running'])
                for node in sorted(secondaries):
                    print_docs.append(OrderedDict
                                      ([('process', padding + 'secondary'),
                                        ('port', node),
                                        ('status', 'running'
                                         if self.cluster_running[node]
                                         else 'down')]))

                # data-bearing nodes that are down or not in the
                # replica set yet
                mongods = self.get_tagged(tags + ['mongod'])
                arbiters = self.get_tagged(tags + ['arbiter'])

                nodes = sorted(mongods - primary - secondaries - arbiters)
                for node in nodes:
                    print_docs.append(OrderedDict
                                      ([('process', padding + 'mongod'),
                                        ('port', node),
                                        ('status', 'running'
                                         if self.cluster_running[node]
                                         else 'down')]))

                # arbiters
                for node in arbiters:
                    print_docs.append(OrderedDict
                                      ([('process', padding + 'arbiter'),
                                        ('port', node),
                                        ('status', 'running'
                                         if self.cluster_running[node]
                                         else 'down')]))

            else:
                nodes = self.get_tagged(tags + ['mongod'])
                if len(nodes) > 0:
                    node = nodes.pop()
                    print_docs.append(OrderedDict
                                      ([('process', padding + 'single'),
                                        ('port', node),
                                        ('status', 'running'
                                         if self.cluster_running[node]
                                         else 'down')]))
            if shard:
                print_docs.append(None)

        processes = self._get_processes()
        startup = self.startup_info

        # print tags as well
        for doc in [x for x in print_docs if type(x) == OrderedDict]:
            try:
                doc['pid'] = processes[doc['port']].pid
            except KeyError:
                doc['pid'] = '-'

            if self.args['verbose'] or self.args['tags']:
                tags = self.get_tags_of_port(doc['port'])
                doc['tags'] = ', '.join(tags)

            if self.args['startup']:
                try:
                    # first try running process (startup may be modified
                    # via start command)
                    doc['startup command'] = ' '.join(processes[doc['port']]
                                                      .cmdline())
                except KeyError:
                    # if not running, use stored startup_info
                    doc['startup command'] = startup[str(doc['port'])]

        print_docs.append(None)
        print()
        print_table(print_docs)
        if self.loaded_args.get('auth'):
            print('\tauth: "%s:%s"' % (self.loaded_args.get('username'),
                                       self.loaded_args.get('password')))

    def kill(self):
        self.discover()

        # get matching tags, can only send signals to running nodes
        matches = self._get_ports_from_args(self.args, 'running')
        processes = self._get_processes()

        # convert signal to int, default is SIGTERM for graceful shutdown
        sig = self.args.get('signal') or 'SIGTERM'
        if os.name == 'nt':
            sig = signal.CTRL_BREAK_EVENT
        if type(sig) == int:
            pass
        elif isinstance(sig, str):
            try:
                sig = int(sig)
            except ValueError:
                try:
                    sig = getattr(signal, sig)
                except AttributeError:
                    raise SystemExit("can't parse signal '%s', use integer or "
                                     "signal name (SIGxxx)." % sig)
        for port in processes:
            # only send signal to matching processes
            if port in matches:
                p = processes[port]
                p.send_signal(sig)
                if self.args['verbose']:
                    print(" %s on port %i, pid=%i" % (p.name, port, p.pid))

        print("sent signal %s to %i process%s."
              % (sig, len(matches), '' if len(matches) == 1 else 'es'))

        # there is a very brief period in which nodes are not reachable
        # anymore, but the port is not torn down fully yet and an immediate
        # start command would fail. This very short sleep prevents that case,
        # and it is practically not noticable by users.
        time.sleep(0.1)

        # refresh discover
        self.discover()

    def restart(self):

        # get all running processes
        processes = self._get_processes()
        procs = [processes[k] for k in list(processes.keys())]

        # stop nodes via stop command
        self.stop()

        # wait until all processes terminate
        psutil.wait_procs(procs)

        # start nodes again via start command
        self.start()

    # --- below are api helper methods, can be called after creating an
    # MLaunchTool() object

    def discover(self):
        """
        Fetch state for each processes.

        Build the self.cluster_tree, self.cluster_tags, self.cluster_running
        data structures, needed for sub-commands start, stop, list.
        """
        # need self.args['command'] so fail if it's not available
        if (not self.args or 'command' not in self.args or not
                self.args['command']):
            return

        # load .mlaunch_startup file for start, stop, list, use current
        # parameters for init
        if self.args['command'] == 'init':
            self.loaded_args = self.args
            self.loaded_unknown_args = self.unknown_args
        else:
            if not self._load_parameters():
                startup_file = os.path.join(self.dir, ".mlaunch_startup")
                raise SystemExit("Can't read %s, use 'mlaunch init ...' first."
                                 % startup_file)

        self.ssl_pymongo_options = self._get_ssl_pymongo_options(
            self.loaded_args)

        # reset cluster_* variables
        self.cluster_tree = {}
        self.cluster_tags = defaultdict(list)
        self.cluster_running = {}

        # get shard names
        shard_names = self._get_shard_names(self.loaded_args)

        # some shortcut variables
        is_sharded = ('sharded' in self.loaded_args and
                      self.loaded_args['sharded'] is not None)
        is_replicaset = ('replicaset' in self.loaded_args and
                         self.loaded_args['replicaset'])
        is_single = 'single' in self.loaded_args and self.loaded_args['single']
        has_arbiter = ('arbiter' in self.loaded_args and
                       self.loaded_args['arbiter'])

        # determine number of nodes to inspect
        if is_sharded:
            num_config = self.loaded_args['config']
            # at least one temp. mongos for adding shards, will be
            # killed later on
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
        self.cluster_tags['all'].extend(list(range(current_port,
                                              current_port + num_nodes)))

        # tag all nodes with their port number (as string) and whether
        # they are running
        for port in range(current_port, current_port + num_nodes):
            self.cluster_tags[str(port)].append(port)

            running = self.is_running(port)
            self.cluster_running[port] = running
            self.cluster_tags['running' if running else 'down'].append(port)

        # find all mongos
        for i in range(num_mongos):
            port = i + current_port

            # add mongos to cluster tree
            self.cluster_tree.setdefault('mongos', []).append(port)
            # add mongos to tags
            self.cluster_tags['mongos'].append(port)

        current_port += num_mongos

        # find all mongods (sharded, replicaset or single)
        if shard_names is None:
            shard_names = [None]

        for shard in shard_names:
            port_range = list(range(current_port, current_port +
                               num_nodes_per_shard))

            # all of these are mongod nodes
            self.cluster_tags['mongod'].extend(port_range)

            if shard:
                # if this is a shard, store in cluster_tree and tag shard name
                self.cluster_tree.setdefault('shard', []).append(port_range)
                self.cluster_tags[shard].extend(port_range)

            if is_replicaset:
                # get replica set states
                rs_name = shard if shard else self.loaded_args['name']

                try:
                    mrsc = self.client(
                        ','.join('localhost:%i' % i for i in port_range),
                        replicaSet=rs_name)

                    # primary, secondaries, arbiters
                    # @todo: this is no longer working because MongoClient
                    # is now non-blocking
                    if mrsc.primary:
                        self.cluster_tags['primary'].append(mrsc.primary[1])
                    self.cluster_tags['secondary'].extend(list(map
                                                          (itemgetter(1),
                                                           mrsc.secondaries)))
                    self.cluster_tags['arbiter'].extend(list(map(itemgetter(1),
                                                            mrsc.arbiters)))

                    # secondaries in cluster_tree (order is now important)
                    self.cluster_tree.setdefault('secondary', [])
                    for i, secondary in enumerate(sorted(map
                                                         (itemgetter(1),
                                                          mrsc.secondaries))):
                        if len(self.cluster_tree['secondary']) <= i:
                            self.cluster_tree['secondary'].append([])
                        self.cluster_tree['secondary'][i].append(secondary)

                except (ConnectionFailure, ConfigurationError):
                    pass

            elif is_single:
                self.cluster_tags['single'].append(current_port)

            # increase current_port
            current_port += num_nodes_per_shard

        # add config server to cluster tree
        self.cluster_tree.setdefault('config', []).append(port)

        # If not CSRS, set the number of config servers to be 1 or 3
        # This is needed, otherwise `mlaunch init --sharded 2 --replicaset
        # --config 2` on <3.3.0 will crash
        if not self.args.get('csrs') and self.args['command'] == 'init':
            if num_config >= 3:
                num_config = 3
            else:
                num_config = 1

        for i in range(num_config):
            port = i + current_port

            try:
                mc = self.client('localhost:%i' % port)
                mc.admin.command('ping')
                running = True

            except ConnectionFailure:
                # node not reachable
                running = False

            # add config server to cluster tree
            self.cluster_tree.setdefault('config', []).append(port)
            # add config server to tags
            self.cluster_tags['config'].append(port)
            self.cluster_tags['mongod'].append(port)

        current_port += num_mongos

    def is_running(self, port):
        """Return True if a host on a specific port is running."""
        try:
            con = self.client('localhost:%s' % port)
            con.admin.command('ping')
            return True
        except (AutoReconnect, ConnectionFailure, OperationFailure):
            # Catch OperationFailure to work around SERVER-31916.
            return False

    def get_tagged(self, tags):
        """
        Tag format.

        The format for the tags list is tuples for tags: mongos, config, shard,
        secondary tags of the form (tag, number), e.g. ('mongos', 2) which
        references the second mongos in the list. For all other tags, it is
        simply the string, e.g. 'primary'.
        """
        # if tags is a simple string, make it a list (note: tuples like
        # ('mongos', 2) must be in a surrounding list)
        if not hasattr(tags, '__iter__') and type(tags) == str:
            tags = [tags]

        nodes = set(self.cluster_tags['all'])

        for tag in tags:
            if re.match(r"\w+ \d{1,2}", tag):
                # special case for tuple tags: mongos, config, shard,
                # secondary. These can contain a number
                tag, number = tag.split()

                try:
                    branch = self.cluster_tree[tag][int(number) - 1]
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
        """
        Get all tags related to a given port.

        This is the inverse of what is stored in self.cluster_tags).
        """
        return(sorted([tag for tag in self.cluster_tags
                       if port in self.cluster_tags[tag]]))

    def wait_for(self, ports, interval=1.0, timeout=30, to_start=True):
        """
        Spawn threads to ping host using a list of ports.

        Returns when all hosts are running (if to_start=True) / shut down (if
        to_start=False).
        """
        threads = []
        queue = Queue.Queue()

        for port in ports:
            threads.append(threading.Thread(target=wait_for_host, args=(
                port, interval, timeout, to_start, queue,
                self.ssl_pymongo_options)))

        if self.args and 'verbose' in self.args and self.args['verbose']:
            print("waiting for nodes %s..."
                  % ('to start' if to_start else 'to shutdown'))

        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join()

        # get all results back and return tuple
        return tuple(queue.get_nowait() for _ in ports)

    # --- below here are internal helper methods, do not call externally ---

    def _load_parameters(self):
        """
        Load the .mlaunch_startup file that exists in each datadir.

        Handles different protocol versions.
        """
        datapath = self.dir

        startup_file = os.path.join(datapath, '.mlaunch_startup')
        if not os.path.exists(startup_file):
            return False

        in_dict = json.load(open(startup_file, 'rb'))

        # handle legacy version without versioned protocol
        if 'protocol_version' not in in_dict:
            in_dict['protocol_version'] = 1
            self.loaded_args = in_dict
            self.startup_info = {}
            # hostname was added recently
            self.loaded_args['hostname'] = socket.gethostname()

        elif in_dict['protocol_version'] == 2:
            self.startup_info = in_dict['startup_info']
            self.loaded_unknown_args = in_dict['unknown_args']
            self.loaded_args = in_dict['parsed_args']

        # changed 'authentication' to 'auth', if present (from old env) rename
        if 'authentication' in self.loaded_args:
            self.loaded_args['auth'] = self.loaded_args['authentication']
            del self.loaded_args['authentication']

        return True

    def _store_parameters(self):
        """Store startup params and config in datadir/.mlaunch_startup."""
        datapath = self.dir

        out_dict = {
            'protocol_version': 2,
            'mtools_version': __version__,
            'parsed_args': self.args,
            'unknown_args': self.unknown_args,
            'startup_info': self.startup_info
        }

        if not os.path.exists(datapath):
            os.makedirs(datapath)
        try:
            json.dump(out_dict,
                      open(os.path.join(datapath,
                                        '.mlaunch_startup'), 'w'), indent=-1)
        except Exception as ex:
            print("ERROR STORING Parameters:", ex)

    def _create_paths(self, basedir, name=None):
        """Create datadir and subdir paths."""
        if name:
            datapath = os.path.join(basedir, name)
        else:
            datapath = basedir

        dbpath = os.path.join(datapath, 'db')
        if not os.path.exists(dbpath):
            os.makedirs(dbpath)
        if self.args['verbose']:
            print('creating directory: %s' % dbpath)

        return datapath

    def _get_ports_from_args(self, args, extra_tag):
        tags = []
        if 'tags' not in args:
            args['tags'] = []

        for tag1, tag2 in zip(args['tags'][:-1], args['tags'][1:]):
            if re.match('^\d{1,2}$', tag1):
                print("warning: ignoring numeric value '%s'" % tag1)
                continue

            if re.match('^\d{1,2}$', tag2):
                if tag1 in ['mongos', 'shard', 'secondary', 'config']:
                    # combine tag with number, separate by string
                    tags.append('%s %s' % (tag1, tag2))
                    continue
                else:
                    print("warning: ignoring numeric value '%s' after '%s'"
                          % (tag2, tag1))

            tags.append(tag1)

        if len(args['tags']) > 0:
            tag = args['tags'][-1]
            if not re.match('^\d{1,2}$', tag):
                tags.append(tag)

        tags.append(extra_tag)

        matches = self.get_tagged(tags)
        return matches

    def _filter_valid_arguments(self, arguments, binary="mongod",
                                config=False):
        """
        Return a list of accepted arguments.

        Check which arguments in list are accepted by the specified binary
        (mongod, mongos). If an argument does not start with '-' but its
        preceding argument was accepted, then it is accepted as well. Example
        ['--slowms', '1000'] both arguments would be accepted for a mongod.
        """
        # get the help list of the binary
        if self.args and self.args['binarypath']:
            binary = os.path.join(self.args['binarypath'], binary)
        ret = (subprocess.Popen(['%s' % binary, '--help'],
               stderr=subprocess.STDOUT, stdout=subprocess.PIPE, shell=False))

        out, err = ret.communicate()
        accepted_arguments = []
        # extract all arguments starting with a '-'
        for line in [option for option in out.decode('utf-8').split('\n')]:
            line = line.lstrip()
            if line.startswith('-'):
                argument = line.split()[0]
                # exception: don't allow unsupported config server arguments
                if config and argument in ['--oplogSize', '--storageEngine',
                                           '--smallfiles', '--nojournal']:
                    continue
                accepted_arguments.append(argument)

        # add undocumented options
        accepted_arguments.append('--setParameter')
        if binary == "mongod":
            accepted_arguments.append('--wiredTigerEngineConfigString')

        # filter valid arguments
        result = []
        for i, arg in enumerate(arguments):
            if arg.startswith('-'):
                # check if the binary accepts this argument or special case -vvv for any number of v
                if arg in accepted_arguments or re.match(r'-v+', arg):
                    result.append(arg)
                elif binary.endswith('mongod') and arg in self.UNDOCUMENTED_MONGOD_ARGS:
                    result.append(arg)
                elif self.ignored_arguments.get(binary + arg) is None:
                    # warn once for each combination of binary and unknown arg
                    self.ignored_arguments[binary + arg] = True
                    print("warning: ignoring unknown argument %s for %s" % (arg, binary))
            elif i > 0 and arguments[i - 1] in result:
                # if it doesn't start with a '-', it could be the value of
                # the last argument, e.g. `--slowms 1000`
                result.append(arg)


        # return valid arguments as joined string
        return ' '.join(result)

    def _get_ssl_server_args(self):
        s = ''
        for parser in self.ssl_args, self.ssl_server_args:
            for action in parser._group_actions:
                name = action.dest
                value = self.args.get(name)
                if value:
                    if value is True:
                        s += ' --%s' % (name,)
                    else:
                        s += ' --%s "%s"' % (name, value)

        return s

    def _get_ssl_pymongo_options(self, args):
        opts = {}
        for parser in self.ssl_args, self.ssl_client_args:
            for action in parser._group_actions:
                name = action.dest
                value = args.get(name)
                if value:
                    opts['ssl'] = True

                    if name == 'sslClientCertificate':
                        opts['ssl_certfile'] = value
                    elif name == 'sslClientPEMKeyFile':
                        opts['ssl_keyfile'] = value
                    elif name == 'sslClientPEMKeyPassword':
                        opts['ssl_pem_passphrase'] = value
                    elif name == 'sslAllowInvalidCertificates':
                        opts['ssl_cert_reqs'] = ssl.CERT_OPTIONAL
                    elif name == 'sslAllowInvalidHostnames':
                        opts['ssl_match_hostname'] = False
                    elif name == 'sslCAFile':
                        opts['ssl_ca_certs'] = value
                    elif name == 'sslCRLFile':
                        opts['ssl_crlfile'] = value

        return opts

    def _get_shard_names(self, args):
        """
        Get the shard names based on the self.args['sharded'] parameter.

        If it's a number, create shard names of type shard##, where ## is a
        2-digit number. Returns a list [None] if no shards are present.
        """
        if 'sharded' in args and args['sharded']:
            if len(args['sharded']) == 1:
                try:
                    # --sharded was a number, name shards shard01, shard02,
                    # ... (only works with replica sets)
                    n_shards = int(args['sharded'][0])
                    shard_names = ['shard%.2i'
                                   % (i + 1) for i in range(n_shards)]
                except ValueError:
                    # --sharded was a string, use it as name for the one shard
                    shard_names = args['sharded']
            else:
                shard_names = args['sharded']
        else:
            shard_names = [None]
        return shard_names

    def _get_last_error_log(self, command_str):
        logpath = re.search(r'--logpath ([^\s]+)', command_str)
        loglines = ''
        try:
            with open(logpath.group(1), 'rb') as logfile:
                for line in logfile:
                    if not line.startswith('----- BEGIN BACKTRACE -----'):
                        loglines += line
                    else:
                        break
        except IOError:
            pass
        return loglines

    def _start_on_ports(self, ports, wait=False, override_auth=False):
        if override_auth and self.args['verbose']:
            print("creating cluster without auth for setup, "
                  "will enable auth at the end...")

        for port in ports:
            command_str = self.startup_info[str(port)]

            if override_auth:
                # this is to set up sharded clusters without auth first,
                # then relaunch with auth
                command_str = re.sub(r'--keyFile \S+', '', command_str)

            try:
                if os.name == 'nt':
                    ret = subprocess.check_call(command_str,
                                                shell=True)
                    # create sub process on windows doesn't wait for output,
                    # wait a few seconds for mongod instance up
                    time.sleep(5)
                else:
                    ret = subprocess.check_output([command_str],
                                                  stderr=subprocess.STDOUT,
                                                  shell=True)


                binary = command_str.split()[0]
                if '--configsvr' in command_str:
                    binary = 'config server'

                if self.args['verbose']:
                    print("launching: %s" % command_str)
                else:
                    print("launching: %s on port %s" % (binary, port))

            except subprocess.CalledProcessError as e:
                print(e.output)
                print(self._get_last_error_log(command_str), file=sys.stderr)
                raise SystemExit("can't start process, return code %i. "
                                 "tried to launch: %s"
                                 % (e.returncode, command_str))

        if wait:
            self.wait_for(ports)


    def _initiate_replset(self, port, name, maxwait=30):
        """Initiate replica set."""
        if not self.args['replicaset'] and name != 'configRepl':
            if self.args['verbose']:
                print('Skipping replica set initialization for %s' % name)
            return

        con = self.client('localhost:%i' % port)
        try:
            rs_status = con['admin'].command({'replSetGetStatus': 1})
            return rs_status
        except OperationFailure as e:
            # not initiated yet
            for i in range(maxwait):
                try:
                    con['admin'].command({'replSetInitiate':
                                          self.config_docs[name]})
                    break
                except OperationFailure as e:
                    print(e.message + " - will retry")
                    time.sleep(1)

            if self.args['verbose']:
                print("initializing replica set '%s' with configuration: %s"
                      % (name, self.config_docs[name]))
            print("replica set '%s' initialized." % name)

    def _add_user(self, port, name, password, database, roles):
        con = self.client('localhost:%i'%port)
        v = con['admin'].command('isMaster').get('maxWireVersion', 0)
        if v >= 7:
            # Until drivers have implemented SCRAM-SHA-256, use old mechanism.
            opts = {'mechanisms': ['SCRAM-SHA-1']}
        else:
            opts = {}

        try:
            con[database].add_user(name, password=password, roles=roles, **opts)
        except OperationFailure as e:
            raise e
        except TypeError as e:
            if pymongo_version < (2, 5, 0):
                con[database].add_user(name, password=password, **opts)
                warnings.warn("Your pymongo version is too old to support "
                              "auth roles. Added a legacy user with root "
                              "access. To support roles, you need to upgrade "
                              "to pymongo >= 2.5.0")
            else:
                raise e

    def _get_processes(self):
        all_ports = self.get_tagged(['running'])

        process_dict = {}

        for p in psutil.process_iter():
            # deal with zombie process errors in OSX
            try:
                name = p.name()
            except psutil.NoSuchProcess:
                continue

            # skip all but mongod / mongos
            if os.name == 'nt':
                if name not in ['mongos.exe', 'mongod.exe']:
                    continue
            else:
                if name not in ['mongos', 'mongod']:
                    continue

            port = None
            for possible_port in self.startup_info:
                # compare ports based on command line argument
                startup = self.startup_info[possible_port].split()
                try:
                    p_port = p.cmdline()[p.cmdline().index('--port') + 1]
                    startup_port = startup[startup.index('--port') + 1]
                except ValueError:
                    continue

                if str(p_port) == str(startup_port):
                    port = int(possible_port)
                    break

            # only consider processes belonging to this environment
            if port in all_ports:
                process_dict[port] = p

        return process_dict

    def _wait_for_primary(self):

        hosts = ([x['host']
                  for x in self.config_docs[self.args['name']]['members']])
        rs_name = self.config_docs[self.args['name']]['_id']
        mrsc = self.client(hosts, replicaSet=rs_name,
                           serverSelectionTimeoutMS=30000)

        if mrsc.is_primary:
            # update cluster tags now that we have a primary
            self.cluster_tags['primary'].append(mrsc.primary[1])
            self.cluster_tags['secondary'].extend(list(map(itemgetter(1),
                                                      mrsc.secondaries)))
            self.cluster_tags['arbiter'].extend(list(map(itemgetter(1),
                                                    mrsc.arbiters)))

            # secondaries in cluster_tree (order is now important)
            self.cluster_tree.setdefault('secondary', [])
            for i, secondary in enumerate(sorted(map(itemgetter(1),
                                                     mrsc.secondaries))):
                if len(self.cluster_tree['secondary']) <= i:
                    self.cluster_tree['secondary'].append([])
                self.cluster_tree['secondary'][i].append(secondary)
            return True

        return False

    # --- below are command line constructor methods, that build the command
    # --- line strings to be called

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

        current_version = self.getMongoDVersion()

        num_mongos = self.args['mongos'] if self.args['mongos'] > 0 else 1
        shard_names = self._get_shard_names(self.args)

        # create shards as stand-alones or replica sets
        nextport = self.args['port'] + num_mongos
        for shard in shard_names:
            if (self.args['single']
                and LooseVersion(current_version) >= LooseVersion("3.6.0")):
                errmsg = " \n * In MongoDB 3.6 and above a Shard must be made up of a replica set. Please use --replicaset option when starting a sharded cluster.*"
                raise SystemExit(errmsg)

            elif (self.args['single']
                  and LooseVersion(current_version) < LooseVersion("3.6.0")):
                self.shard_connection_str.append(
                    self._construct_single(self.dir, nextport, name=shard, extra='--shardsvr'))
                nextport += 1
            elif self.args['replicaset']:
                self.shard_connection_str.append(
                    self._construct_replset(self.dir, nextport, shard, num_nodes=list(range(self.args['nodes'])),
                                            arbiter=self.args['arbiter'], extra='--shardsvr'))
                nextport += self.args['nodes']
                if self.args['arbiter']:
                    nextport += 1

        # start up config server(s)
        config_string = []

        # SCCC config servers (MongoDB <3.3.0)
        if not self.args['csrs'] and self.args['config'] >= 3:
            config_names = ['config1', 'config2', 'config3']
        else:
            config_names = ['config']

        # CSRS config servers (MongoDB >=3.1.0)
        if self.args['csrs']:
            config_string.append(self._construct_config(self.dir, nextport,
                                                        "configRepl", True))
        else:
            for name in config_names:
                self._construct_config(self.dir, nextport, name)
                config_string.append('%s:%i' % (self.args['hostname'],
                                                nextport))
                nextport += 1

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

        return(name + '/' +
               ','.join([c['host']
                         for c in self.config_docs[name]['members']]))

    def _construct_config(self, basedir, port, name=None, isreplset=False):
        """Construct command line strings for a config server."""
        if isreplset:
            return self._construct_replset(basedir=basedir, portstart=port,
                                           name=name,
                                           num_nodes=list(range(self
                                                           .args['config'])),
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

    def _construct_mongod(self, dbpath, logpath, port, replset=None, extra=''):
        """Construct command line strings for mongod process."""
        rs_param = ''
        if replset:
            rs_param = '--replSet %s' % replset

        auth_param = ''
        if self.args['auth']:
            key_path = os.path.abspath(os.path.join(self.dir, 'keyfile'))
            auth_param = '--keyFile %s' % key_path

        if self.unknown_args:
            config = '--configsvr' in extra
            extra = self._filter_valid_arguments(self.unknown_args, "mongod",
                                                 config=config) + ' ' + extra

        # set WiredTiger cache size to 1 GB by default
        if ('--wiredTigerCacheSizeGB' not in extra and
                self._filter_valid_arguments(['--wiredTigerCacheSizeGB'],
                                             'mongod')):
            extra += ' --wiredTigerCacheSizeGB 1 '

        current_version = self.getMongoDVersion()

        # Exit with error if hostname is specified but not bind_ip options
        if (self.args['hostname'] != 'localhost'
                and LooseVersion(current_version) >= LooseVersion("3.6.0")
                and (self.args['sharded'] or self.args['replicaset'])
                and '--bind_ip' not in extra):
            os.removedirs(dbpath)
            errmsg = " \n * If hostname is specified, please include '--bind_ip_all' or '--bind_ip' options when deploying replica sets or sharded cluster with MongoDB version 3.6.0 or greater"
            raise SystemExit(errmsg)

        extra += self._get_ssl_server_args()

        path = self.args['binarypath'] or ''
        if os.name == 'nt':
            newdbpath = dbpath.replace('\\', '\\\\')
            newlogpath = logpath.replace('\\', '\\\\')
            command_str = ("start /b \"\" \"%s\" %s --dbpath \"%s\" --logpath \"%s\" --port %i "
                           "%s %s" % (os.path.join(path, 'mongod.exe'),
                                      rs_param, newdbpath, newlogpath, port,
                                      auth_param, extra))
        else:
            command_str = ("\"%s\" %s --dbpath \"%s\" --logpath \"%s\" --port %i --fork "
                           "%s %s" % (os.path.join(path, 'mongod'), rs_param,
                                      dbpath, logpath, port, auth_param,
                                      extra))

        # store parameters in startup_info
        self.startup_info[str(port)] = command_str

    def _construct_mongos(self, logpath, port, configdb):
        """Construct command line strings for a mongos process."""
        extra = ''

        auth_param = ''
        if self.args['auth']:
            key_path = os.path.abspath(os.path.join(self.dir, 'keyfile'))
            auth_param = '--keyFile %s' % key_path

        if self.unknown_args:
            extra = self._filter_valid_arguments(self.unknown_args,
                                                 "mongos") + extra

        extra += ' ' + self._get_ssl_server_args()

        path = self.args['binarypath'] or ''
        if os.name == 'nt':
            newlogpath = logpath.replace('\\', '\\\\')
            command_str = ("start /b %s --logpath %s --port %i --configdb %s "
                           "%s %s " % (os.path.join(path, 'mongos'),
                                       newlogpath, port, configdb,
                                       auth_param, extra))
        else:
            command_str = ("%s --logpath %s --port %i --configdb %s %s %s "
                           "--fork" % (os.path.join(path, 'mongos'), logpath,
                                       port, configdb, auth_param, extra))

        # store parameters in startup_info
        self.startup_info[str(port)] = command_str

    def _read_key_file(self):
        with open(os.path.join(self.dir, 'keyfile'), 'rb') as f:
            return ''.join(f.readlines())


def main():
    tool = MLaunchTool()
    tool.run()


if __name__ == '__main__':
    sys.exit(main())
