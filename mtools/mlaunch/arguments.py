#!/usr/bin/env python3
"""Argument parser for mlaunch."""

import argparse
import os
import re
import sys

from packaging import version

from mtools.version import __version__


class _ConfigCountOrFile(argparse.Action):
    """``--config`` is a config-server count or a server config file.

    A value of only digits is the number of config servers. Any other
    value is a mongod or mongos config file. The count then stays at 1,
    and the file is passed through as ``--config``.
    """

    def __call__(self, parser, namespace, values, option_string=None):
        if re.fullmatch(r'\d+', values):
            setattr(namespace, self.dest, int(values))
            setattr(namespace, 'server_config', None)
        else:
            setattr(namespace, 'server_config', values)
            setattr(namespace, self.dest, 1)


class ArgumentsMixin(object):
    """Build the mlaunch command line parser."""

    def _build_argument_parser(self, arguments=None):
        """Create sub-commands and return arguments with the init default."""
        # set up argument parsing in run, so that subsequent calls
        # to run can call different sub-commands
        self.argparser = argparse.ArgumentParser()
        self.argparser.add_argument(
            '--version', action='version',
            version=(f'mtools version {__version__} || '
                     f'Python {sys.version}'))
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
             '--storageEngine, --logappend, or --slowms.')

        # init command
        helptext = ('initialize a new MongoDB environment and start '
                    'stand-alone instances, replica sets, or sharded '
                    'clusters.')
        desc = ('Initialize a new MongoDB environment and start stand-alone '
                'instances, replica sets, or sharded clusters. Command line '
                'arguments which are not handled by mlaunch will be passed '
                'through to mongod/mongos if those options are listed in the '
                '--help output for the current binary. For example: '
                '--storageEngine, --logappend, or --slowms.')
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
        init_parser.add_argument('--config', action=_ConfigCountOrFile,
                                 default=1, metavar='NUM|FILE',
                                 help=('number of config servers in a sharded '
                                       'setup (default=1). A non-numeric value '
                                       'is a mongod/mongos config file passed '
                                       'as --config, and the count stays 1. '
                                       '-f FILE is the short form of that '
                                       'server option and still passes a file '
                                       'through, including with a count'))
        init_parser.set_defaults(server_config=None)

        # As of MongoDB 3.6, all config servers must be CSRS
        init_parser.add_argument('--csrs', default=True, action='store_true',
                                 help=argparse.SUPPRESS)

        init_parser.add_argument('--mongos', action='store', default=1,
                                 type=int, metavar='NUM',
                                 help=('starts NUM mongos processes (requires '
                                       '--sharded, default=1)'))

        # verbose, port, binary path
        init_parser.add_argument('--verbose', action='store_true',
                                 default=False,
                                 help=('outputs more verbose information, and '
                                       'passes -v to mongod/mongos unless -v '
                                       'is already given.'))
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
        init_parser.add_argument('--auth-role-docs', action='store_true',
                                 default=False,
                                 help='auth-roles are JSON documents')
        init_parser.add_argument('--no-initial-user', action='store_false',
                                 default=True, dest='initial-user',
                                 help=('Do not create an initial user if auth '
                                       'is enabled'))

        def is_file(arg):
            if not os.path.exists(os.path.expanduser(arg)):
                init_parser.error("The file [%s] does not exist" % arg)
            return arg

        # MongoDB 4.2 adds TLS options to replace the corresponding SSL options
        # https://docs.mongodb.com/manual/release-notes/4.2/#new-tls-options
        if (version.parse(self.current_version) >= version.parse("4.2.0")):
            # tls
            tls_args = init_parser.add_argument_group('TLS options')
            tls_args.add_argument('--tlsCAFile',
                                  help='Certificate Authority file for TLS',
                                  type=is_file)
            tls_args.add_argument('--tlsCRLFile',
                                  help='Certificate Revocation List file for TLS',
                                  type=is_file)
            tls_args.add_argument('--tlsAllowInvalidHostnames',
                                  action='store_true',
                                  help=('allow client and server certificates to '
                                        'provide non-matching hostnames'))
            tls_args.add_argument('--tlsAllowInvalidCertificates',
                                  action='store_true',
                                  help=('allow client or server connections with '
                                        'invalid certificates'))

            tls_server_args = init_parser.add_argument_group('Server TLS options')
            tls_server_args.add_argument('--tlsMode',
                                         help='set the TLS operation mode',
                                         choices=('disabled allowTLS preferTLS '
                                                  'requireTLS'.split()))
            tls_server_args.add_argument('--tlsCertificateKeyFile',
                                         help='PEM file for TLS', type=is_file)
            tls_server_args.add_argument('--tlsCertificateKeyFilePassword',
                                         help='PEM file password')
            tls_server_args.add_argument('--tlsClusterFile',
                                         help=('key file for internal TLS '
                                               'authentication'), type=is_file)
            tls_server_args.add_argument('--tlsClusterPassword',
                                         help=('internal authentication key '
                                               'file password'))
            tls_server_args.add_argument('--tlsDisabledProtocols',
                                         help=('comma separated list of TLS '
                                               'protocols to disable '
                                               '[TLS1_0,TLS1_1,TLS1_2,TLS1_3]'))
            tls_server_args.add_argument('--tlsAllowConnectionsWithoutCertificates',
                                         action='store_true',
                                         help=('allow client to connect without '
                                               'presenting a certificate'))
            tls_server_args.add_argument('--tlsFIPSMode', action='store_true',
                                         help='activate FIPS 140-2 mode')

            tls_client_args = init_parser.add_argument_group('Client TLS options')
            tls_client_args.add_argument('--tlsClientCertificateKeyFile',
                                         help='client certificate cert and key file for TLS',
                                         type=is_file)
            tls_client_args.add_argument('--tlsClientCertificateKeyFilePassword',
                                         help='client certificate key file password')

            self.tls_args = tls_args
            self.tls_client_args = tls_client_args
            self.tls_server_args = tls_server_args

        # ssl options were aliased to tls, but are still available in
        # server versions through MongoDB 6.0
        ssl_args = init_parser.add_argument_group('TLS/SSL options')
        ssl_args.add_argument(
            '--sslCAFile',
            help='Certificate Authority file for TLS/SSL',
            type=is_file)
        ssl_args.add_argument(
            '--sslCRLFile',
            help='Certificate Revocation List file for TLS/SSL',
            type=is_file)
        ssl_args.add_argument(
            '--sslAllowInvalidHostnames',
            action='store_true',
            help=('allow client and server certificates to '
                  'provide non-matching hostnames'))
        ssl_args.add_argument(
            '--sslAllowInvalidCertificates',
            action='store_true',
            help=('allow client or server connections with '
                  'invalid certificates'))

        ssl_server_args = init_parser.add_argument_group(
            'Server TLS/SSL options')
        ssl_server_args.add_argument(
            '--sslMode',
            help='set the TLS/SSL operation mode',
            choices=('disabled allowSSL preferSSL '
                     'requireSSL'.split()))
        ssl_server_args.add_argument(
            '--sslPEMKeyFile',
            help='PEM file for TLS/SSL', type=is_file)
        ssl_server_args.add_argument(
            '--sslPEMKeyPassword',
            help='PEM file password')
        ssl_server_args.add_argument(
            '--sslClusterFile',
            help=('key file for internal TLS/SSL '
                  'authentication'), type=is_file)
        ssl_server_args.add_argument(
            '--sslClusterPassword',
            help=('internal authentication key '
                  'file password'))
        ssl_server_args.add_argument(
            '--sslDisabledProtocols',
            help=('comma separated list of TLS '
                  'protocols to disable '
                  '[TLS1_0,TLS1_1,TLS1_2]'))
        ssl_server_args.add_argument(
            '--sslAllowConnectionsWithoutCertificates',
            action='store_true',
            help=('allow client to connect without '
                  'presenting a certificate'))
        ssl_server_args.add_argument(
            '--sslFIPSMode', action='store_true',
            help='activate FIPS 140-2 mode')
        ssl_server_args.add_argument(
            '--sslOnNormalPorts', action='store_true',
            help='deprecated alias of --tlsOnNormalPorts')
        ssl_server_args.add_argument(
            '--sslWeakCertificateValidation', action='store_true',
            help=('allow connections that use weak '
                  'certificate validation'))

        ssl_client_args = init_parser.add_argument_group(
            'Client TLS/SSL options')
        ssl_client_args.add_argument(
            '--sslClientCertificate',
            help='client certificate file for TLS/SSL',
            type=is_file)
        ssl_client_args.add_argument(
            '--sslClientPEMKeyFile',
            help='client PEM file for TLS/SSL',
            type=is_file)
        ssl_client_args.add_argument(
            '--sslClientPEMKeyPassword',
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
        list_parser.add_argument('--json', action='store_true', default=False,
                                 help=('output in JSON format '))
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
        return arguments
