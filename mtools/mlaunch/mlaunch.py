#!/usr/bin/env python3

import argparse
import functools
import ipaddress
import json
import os
import queue as Queue
import re
import shlex
import signal
import socket
import ssl
import subprocess
import sys
import tempfile
import threading
import time
import warnings
from collections import defaultdict
from urllib.parse import quote, quote_plus
from operator import itemgetter

import psutil
from mtools.mlaunch.arguments import ArgumentsMixin
from mtools.mlaunch.process import ProcessMixin, shutdown_host, wait_for_host
from mtools.mlaunch.tls_args import TlsArgsMixin
from mtools.mlaunch.topology import TopologyMixin
from mtools.util import OrderedDict
from mtools.util.cmdlinetool import BaseCmdLineTool
from mtools.util.print_table import print_table
from mtools.version import __version__

try:
    from pymongo import MongoClient as Connection
    from pymongo import version_tuple as pymongo_version
    from bson import SON
    from io import BytesIO
    from packaging import version

    from pymongo.errors import ConnectionFailure, AutoReconnect
    from pymongo.errors import OperationFailure, ConfigurationError
except ImportError as e:
    raise ImportError(f"Can't import pymongo: {str(e)}\n\n"
                       "For instructions on how to install pymongo, see:\n"
                       "   https://www.mongodb.com/docs/drivers/pymongo/#installation")


class MongoConnection(Connection):
    """
    MongoConnection class.

    Wrapper around Connection (itself conditionally a MongoClient or
    pymongo.Connection) to specify timeout and directConnection.
    """

    def __init__(self, *args, **kwargs):
        kwargs.setdefault('serverSelectionTimeoutMS', 1)

        # Set client application name for MongoDB 3.4+ servers
        kwargs['appName'] = f'''mlaunch v{__version__}'''

        Connection.__init__(self, *args, **kwargs)


def _parse_bind_ips(argv):
    """Return addresses from ``--bind_ip`` in a mongod argument list."""
    if not argv:
        return []
    addresses = []
    index = 0
    while index < len(argv):
        arg = argv[index]
        if arg == '--bind_ip' and index + 1 < len(argv):
            addresses.extend(_split_bind_ip(argv[index + 1]))
            index += 2
            continue
        if arg.startswith('--bind_ip='):
            addresses.extend(_split_bind_ip(arg.split('=', 1)[1]))
        index += 1
    return addresses


def _split_bind_ip(value):
    parts = []
    for part in value.split(','):
        part = part.strip().strip('"').strip("'")
        if len(part) >= 2 and part[0] == '[' and part[-1] == ']':
            part = part[1:-1]
        if part:
            parts.append(part)
    return parts


def _ip_address(value):
    try:
        return ipaddress.ip_address(value)
    except ValueError:
        return None


def format_node_address(host, port):
    """Return ``host:port``, with brackets when host is an IPv6 address."""
    if isinstance(_ip_address(host), ipaddress.IPv6Address):
        return '[%s]:%s' % (host, port)
    return '%s:%s' % (host, port)


def dial_host(hostname, argv):
    """Host that reaches a node mlaunch started.

    PyMongo resolves ``localhost`` as IPv4 only. A node bound only to an
    IPv6 address has to be dialed at that address. ``--bind_ip ::`` listens
    on every IPv6 interface, so the dial address is the loopback ``::1``.
    """
    ipv4 = []
    ipv6 = []
    for address in _parse_bind_ips(argv):
        ip = _ip_address(address)
        if isinstance(ip, ipaddress.IPv4Address):
            ipv4.append(address)
        elif isinstance(ip, ipaddress.IPv6Address):
            ipv6.append(address)
    if ipv6 and not ipv4:
        # "::" is every IPv6 interface, which is not a dial target.
        if _ip_address(ipv6[0]) == ipaddress.ip_address('::'):
            return '::1'
        return ipv6[0]
    return hostname or 'localhost'


@functools.lru_cache()
def check_mongo_server_output(binary, argument, fatal = True):
    """Call mongo[d|s] with arguments such as --help or --version.

    This is used only to check the server's output. We expect the server to
    exit immediately.
    """
    try:
        proc = subprocess.Popen(['%s' % binary, argument],
                                stderr=subprocess.STDOUT,
                                stdout=subprocess.PIPE, shell=False)
    except OSError as exc:
        if fatal:
            print(f"Fatal error: failed to launch [{binary}].\n"
                "Please ensure this binary is found in your $PATH "
                "or specified with --binarypath.\n")
            raise SystemExit(exc)

    out, err = proc.communicate()
    if proc.returncode:
        raise OSError(out or err)

    return out


def _normalize_command(command):
    """Collapse whitespace outside quotes and strip the ends.

    Spaces inside single or double quotes stay, including paths that
    contain spaces. An empty ``""`` token stays, so a Windows
    ``start /b "" "mongod.exe"`` prefix is unchanged.
    """
    if not command:
        return command
    # only ASCII shell whitespace; a no-break space in a path is literal
    blanks = ' \t\r\n'
    out = []
    quote = None
    escaped = False
    prev_space = False
    started = False
    for ch in command.strip(blanks):
        if quote:
            out.append(ch)
            if escaped:
                escaped = False
            elif ch == '\\' and quote == '"':
                # backslash escapes the next character inside double quotes
                escaped = True
            elif ch == quote:
                quote = None
            prev_space = False
            continue
        if ch in ('"', "'"):
            quote = ch
            out.append(ch)
            prev_space = False
            started = True
            continue
        if ch in blanks:
            if started and not prev_space:
                out.append(' ')
            prev_space = True
            continue
        out.append(ch)
        prev_space = False
        started = True
    return ''.join(out).rstrip(blanks)


_SERVER_VERSION_RE = re.compile(r'(\d+\.\d+\.\d+)')


def _extract_server_version(text):
    """Return the first X.Y.Z version found in text, or None.

    Handles output such as "db version v7.0.14", release candidates
    ("v8.0.0-rc2") and dev builds ("v8.3.0-alpha6-261-g43a317d-patch"),
    which all map to the plain X.Y.Z release version.
    """
    if not text:
        return None
    match = _SERVER_VERSION_RE.search(text)
    return match.group(1) if match else None


class MLaunchTool(ArgumentsMixin, TopologyMixin, ProcessMixin, TlsArgsMixin,
                  BaseCmdLineTool):
    # These repeat options the constructed command already contains.
    OWNED_FLAG_REASONS = {
        '--dbpath': 'mlaunch sets it from --dir',
        '--logpath': 'mlaunch sets it from --dir',
        '--port': 'mlaunch sets it from --port',
        '--fork': 'mlaunch adds it when it starts the process',
        '--replSet': 'mlaunch sets it from the replica set name',
        '--configsvr': 'mlaunch sets it for this node',
        '--shardsvr': 'mlaunch sets it for this node',
        '--configdb': 'mlaunch sets it from the config servers',
    }
    OWNED_FLAGS_WITHOUT_VALUE = frozenset({
        '--fork', '--configsvr', '--shardsvr',
    })

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

        # tls configuration to start mongod or mongos, or create a MongoClient
        self.tls_server_args = ''
        self.tls_pymongo_options = {}

        # indicate if running in testing mode
        self.test = test

        # find mongod version to determine avail options for arg parser in run()
        # consider --binarypath if set
        for i in range(1,len(sys.argv)):
            if (sys.argv[i] == "--binarypath") and (i+1 < len(sys.argv)):
                self.args = dict()
                self.args['binarypath'] = sys.argv[i+1]
                break
        self.current_version = self.getMongoDVersion(False)

    def run(self, arguments=None):
        """
        Main run method.

        Called for all sub-commands and parameters. It sets up argument
        parsing, then calls the sub-command method with the same name.
        """
        arguments = self._build_argument_parser(arguments)

        # argparser is set up, now call base class run()
        BaseCmdLineTool.run(self, arguments, get_unknowns=True)

        # conditions on argument combinations
        if (self.args['command'] == 'init' and
                'single' in self.args and self.args['single']):
            if self.args['arbiter']:
                self.argparser.error("can't specify --arbiter for "
                                     "single nodes.")

        # replace path with absolute path, but store relative path as well
        if ('dir' in self.args and self.args['dir']):
            self.relative_dir = self.args['dir']
            self.dir = os.path.abspath(self.args['dir'])
            self.args['dir'] = self.dir

        if (self.args['command'] is None):
            self.argparser.print_help()
            self.argparser.exit()
        else:
            # branch out in sub-commands
            getattr(self, self.args['command'])()

    def connection_string(self):
        """Return the MongoDB URI for the cluster ``init`` provisions."""
        hostname = self.args.get('hostname') or 'localhost'
        port = int(self.args.get('port') or 27017)
        options = []

        if self.args.get('sharded'):
            mongos = self.args.get('mongos')
            if mongos is None:
                mongos = 1
            if mongos > 0:
                hosts = [self._join_host(hostname, port + i)
                         for i in range(mongos)]
            else:
                return '\n'.join(self._shard_uris())
        elif self.args.get('replicaset'):
            name = self.args.get('name') or 'replset'
            members = self.config_docs.get(name, {}).get('members', [])
            hosts = [self._format_hostport(member['host'])
                     for member in members]
            if not hosts:
                hosts = [self._join_host(hostname, port)]
            options.append('replicaSet=%s' % quote_plus(name))
        else:
            hosts = [self._join_host(hostname, port)]

        return self._mongodb_uri(hosts, options)

    def _shard_uris(self):
        """URIs for shard replica sets when no mongos is left running."""
        uris = []
        for shard in self.shard_connection_str:
            name, _, hosts = shard.partition('/')
            hostlist = [self._format_hostport(host)
                        for host in hosts.split(',') if host]
            options = ['replicaSet=%s' % quote_plus(name)]
            uris.append(self._mongodb_uri(hostlist, options))
        return uris

    def _mongodb_uri(self, hosts, options):
        """Build a ``mongodb://`` URI, including auth and TLS when set."""
        options = list(options)
        userinfo = ''
        if self.args.get('auth') and self.args.get('initial-user', True):
            # userinfo is percent-encoded; quote_plus would turn spaces
            # into '+', which the URI parser keeps as a literal plus
            username = quote(str(self.args.get('username') or 'user'), safe='')
            auth_db = str(self.args.get('auth_db') or 'admin')
            if auth_db == '$external':
                # x.509 users authenticate with the client certificate
                userinfo = '%s@' % username
                options.append('authMechanism=MONGODB-X509')
            else:
                password = quote(str(self.args.get('password') or 'password'),
                                 safe='')
                userinfo = '%s:%s@' % (username, password)
            options.append('authSource=%s' % quote(auth_db, safe=''))
        mode = self.args.get('tlsMode') or self.args.get('sslMode')
        if mode in ('requireTLS', 'preferTLS', 'requireSSL', 'preferSSL'):
            options.append('tls=true')
            ca_file = self.args.get('tlsCAFile') or self.args.get('sslCAFile')
            if ca_file:
                options.append('tlsCAFile=%s' % quote(str(ca_file), safe=''))
            cert_file = (self.args.get('tlsClientCertificateKeyFile') or
                         self.args.get('sslClientCertificate'))
            if cert_file:
                options.append('tlsCertificateKeyFile=%s'
                               % quote(str(cert_file), safe=''))
        body = '%s%s' % (userinfo, ','.join(hosts))
        if options:
            return 'mongodb://%s/?%s' % (body, '&'.join(options))
        return 'mongodb://%s' % body

    @staticmethod
    def _join_host(hostname, port):
        """Return ``host:port``, with brackets when host is IPv6."""
        try:
            address = ipaddress.ip_address(hostname)
        except ValueError:
            address = None
        if isinstance(address, ipaddress.IPv6Address):
            return '[%s]:%s' % (hostname, port)
        return '%s:%s' % (hostname, port)

    @staticmethod
    def _format_hostport(value):
        """Bracket an IPv6 address inside an existing ``host:port``."""
        if value.startswith('['):
            return value
        host, sep, port = value.rpartition(':')
        if sep and ':' in host:
            return '[%s]:%s' % (host, port)
        return value

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
        self.tls_pymongo_options = self._get_tls_pymongo_options(self.args)

        if (self._get_ssl_server_args() and not
                self.args['sslAllowConnectionsWithoutCertificates'] and not
                self.args['sslClientCertificate'] and not
                self.args['sslClientPEMKeyFile']):
            sys.stderr.write('warning: server requires certificates but no'
                             ' --sslClientCertificate provided\n')

        if (self._get_tls_server_args() and not
                self.args['tlsAllowConnectionsWithoutCertificates'] and not
                self.args['tlsClientCertificateKeyFile']):
            sys.stderr.write('warning: server requires certificates but no'
                             ' --tlsClientCertificateKeyFile provided\n')
        # number of default config servers
        if self.args['config'] == -1:
            self.args['config'] = 1

        # add the 'csrs' parameter as default for MongoDB >= 3.3.0
        if (version.parse(self.current_version) >= version.parse("3.3.0") or
                version.parse(self.current_version) == version.parse("0.0.0")):
            self.args['csrs'] = True

        # construct startup strings
        self._construct_cmdlines()

        # write out parameters
        if self.args['verbose']:
            print("writing .mlaunch_startup file.")
        self._store_parameters()

        # exit if running in testing mode
        if self.test:
            return

        # check if authentication is enabled, make key file
        if self.args['auth'] and first_init:
            if not os.path.exists(self.dir):
                os.makedirs(self.dir)

            if '--keyFile' in self.unknown_args:
                # Check if keyfile is readable
                keyfile = None
                try:
                    keyfile_idx = self.unknown_args.index('--keyFile') + 1
                    keyfile_path = self.unknown_args[keyfile_idx]
                    keyfile = self._read_key_file(keyfile_path)
                except:
                    print(f'\n WARNING: Specified keyFile does not appear readable: {keyfile_path}\n')
            else:
                keyfile = os.path.join(self.dir, "keyfile")
                print(f'Generating keyfile: {keyfile}')
                os.system('openssl rand -base64 753 > "%s"' % keyfile)
                if os.name != 'nt':
                    os.system(f'chmod 600 "{keyfile}"')

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
                con = self.client(self._node_address(mongos[0]))

                shards_to_add = len(self.shard_connection_str)
                nshards = con['config']['shards'].count_documents({})
                if nshards < shards_to_add:
                    if self.args['replicaset']:
                        print("adding shards. can take up to 30 seconds...")
                    else:
                        print("adding shards.")

                shard_conns_and_names = list(zip(self.shard_connection_str,
                                                 shard_names))
                while True:
                    try:
                        nshards = con['config']['shards'].count_documents({})
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
                                print('Shard addition failed: %s; will retry in a moment.' % e)
                            continue

                        if res['ok']:
                            if self.args['verbose']:
                                print("shard %s added successfully" % conn_str)
                                shard_conns_and_names.remove((conn_str, name))
                                break
                        else:
                            if self.args['verbose']:
                                print('Shard addition failed: ' + res + ' - will retry')

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

            roles = []
            found_cluster_admin = False
            if self.args['auth_role_docs']:
                for role_str in self.args['auth_roles']:
                    role_doc = json.loads(role_str)
                    roles.append(role_doc)
                    if role_doc['role'] == "clusterAdmin":
                        found_cluster_admin = True
            else:
                roles = self.args['auth_roles']
                found_cluster_admin = "clusterAdmin" in roles

            if not found_cluster_admin:
                warnings.warn("the stop command will not work with auth "
                              "because the user does not have the "
                              "clusterAdmin role")

            self._add_user(sorted(nodes)[0], name=self.args['username'],
                           password=self.args['password'],
                           database=self.args['auth_db'],
                           roles=roles)

            if self.args['sharded']:
                for shard in shard_names:
                    members = sorted(self.get_tagged([shard]))
                    if self.args['verbose']:
                        print("adding users to %s" % shard)
                    self._add_user(members[0],
                                   name=self.args['username'],
                                   password=self.args['password'],
                                   database=self.args['auth_db'],
                                   roles=roles)

            if self.args['verbose']:
                print("added user %s on %s database" % (self.args['username'],
                                                        self.args['auth_db']))

        # in sharded env, if --mongos 0, kill the dummy mongos
        if self.args['sharded'] and self.args['mongos'] == 0:
            port = self.args['port']
            print("shutting down temporary mongos on %s"
                  % self._node_address(port))
            username = self.args['username'] if self.args['auth'] else None
            password = self.args['password'] if self.args['auth'] else None
            authdb = self.args['auth_db'] if self.args['auth'] else None
            shutdown_host(port, username, password, authdb,
                          node_host=self._dial_host())

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

        for uri in self.connection_string().splitlines():
            if uri:
                print('connection: %s' % uri)

        if self.args['verbose']:
            print("done.")

    # Get the "mongod" version, useful for checking for support or
    # non-support of features.
    # Normally we expect to get back something like "db version v3.4.0",
    # but with release candidates we get abck something like
    # "db version v3.4.0-rc2". This code exact the "major.minor.revision"
    # part of the string
    def getMongoDVersion(self, fatal = True):
        binary = "mongod"
        if self.args and self.args.get('binarypath'):
            binary = os.path.join(self.args['binarypath'], binary)

        try:
            out = check_mongo_server_output(binary, '--version', fatal)
        except Exception:
            return "0.0.0"

        first_line = BytesIO(out).readline().decode('utf-8', 'replace')
        current_version = _extract_server_version(first_line) or "0.0.0"

        print("Detected mongod version: %s" % current_version)
        return current_version

    def _bind_argv(self):
        """Mongod arguments that carry the bind address for this environment."""
        command = self.args.get('command') if self.args else None
        if command and command != 'init':
            stored = getattr(self, 'loaded_unknown_args', None)
            if stored:
                return stored
        return getattr(self, 'unknown_args', None) or []

    def _dial_host(self):
        """Host name or IP that reaches a node in this environment."""
        hostname = None
        if self.args:
            hostname = self.args.get('hostname')
        if not hostname:
            loaded = getattr(self, 'loaded_args', None) or {}
            hostname = loaded.get('hostname')
        return dial_host(hostname, self._bind_argv())

    def _node_address(self, port):
        """``host:port`` for a client connection to one of our nodes."""
        return format_node_address(self._dial_host(), port)

    def client(self, host_and_port, **kwargs):
        kwargs.update(self.ssl_pymongo_options)
        kwargs.update(self.tls_pymongo_options)
        return MongoConnection(host_and_port, **kwargs)

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
        for doc in [x for x in print_docs if isinstance(x, OrderedDict)]:
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

        if (self.args['json']):
            print(json.dumps(print_docs))
        else:
            print()
            print_docs.append(None)
            print_table(print_docs)
            if self.loaded_args.get('auth'):
                print('\tauth: "%s:%s"' % (self.loaded_args.get('username'),
                                        self.loaded_args.get('password')))

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

        self.ssl_pymongo_options = self._get_ssl_pymongo_options(self.loaded_args)
        self.tls_pymongo_options = self._get_tls_pymongo_options(self.loaded_args)

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
            port_range = list(range(current_port,
                                    current_port + num_nodes_per_shard))

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
                        ','.join(self._node_address(i) for i in port_range),
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

        for i in range(num_config):
            port = i + current_port

            try:
                mc = self.client(self._node_address(port),
                                 directConnection=True)
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
        if not hasattr(tags, '__iter__') and isinstance(tags, str):
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

        startup_info = {
            port: _normalize_command(command)
            for port, command in self.startup_info.items()
        }
        out_dict = {
            'protocol_version': 2,
            'mtools_version': __version__,
            'parsed_args': self.args,
            'unknown_args': self.unknown_args,
            'startup_info': startup_info
        }

        if not os.path.exists(datapath):
            os.makedirs(datapath)
        startup_file = os.path.join(datapath, '.mlaunch_startup')
        try:
            with open(startup_file, 'w') as handle:
                json.dump(out_dict, handle, indent=2)
                handle.write('\n')
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
            if re.match(r'^\d{1,2}$', tag1):
                print("warning: ignoring numeric value '%s'" % tag1)
                continue

            if re.match(r'^\d{1,2}$', tag2):
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
            if not re.match(r'^\d{1,2}$', tag):
                tags.append(tag)

        tags.append(extra_tag)

        matches = self.get_tagged(tags)
        return matches

    def _owned_server_args(self, binary, extra='', replset=None):
        """Flags the constructed command already sets."""
        owned = ['--logpath', '--port']
        if binary == 'mongod':
            owned.append('--dbpath')
        # Owned only when this command will contain --fork. MongoDB 8.2+
        # on macOS rejects it, and the launch path omits it.
        if os.name != 'nt' and not self._macos_fork_unsupported():
            owned.append('--fork')
        if replset:
            owned.append('--replSet')
        if binary == 'mongos':
            owned.append('--configdb')
        for flag in ('--configsvr', '--shardsvr'):
            if flag in extra.split():
                owned.append(flag)
        return owned

    def _warn_owned_argument(self, binary, argname):
        """Warn once when an extra flag repeats one mlaunch already sets."""
        key = binary + argname
        if self.ignored_arguments.get(key) is not None:
            return
        self.ignored_arguments[key] = True
        reason = self.OWNED_FLAG_REASONS.get(argname, 'mlaunch sets it')
        print(f"warning: ignoring {argname}; {reason}")

    def _filter_valid_arguments(self, arguments, binary="mongod", owned=None):
        """Return extra arguments to pass through to mongod or mongos.

        Every option is kept. The server accepts it or exits with
        ``Error parsing command line:``. A token that follows a kept
        option is quoted. Example: ``['--slowms', '1000']``.

        Flags in `owned` are dropped, along with a separate value token.
        The constructed command already contains them.
        """
        if self.args and self.args['binarypath']:
            binary = os.path.join(self.args['binarypath'], binary)

        result = []
        owned_args = set(owned or ())
        skip_value = False
        for i, arg in enumerate(arguments):
            if skip_value:
                skip_value = False
                if not arg.startswith('-'):
                    continue
            if arg.startswith('-'):
                argname = arg.split('=', 1)[0]
                if argname in owned_args:
                    self._warn_owned_argument(binary, argname)
                    takes_value = (
                        '=' not in arg and
                        argname not in self.OWNED_FLAGS_WITHOUT_VALUE)
                    if takes_value:
                        skip_value = True
                    continue
                result.append(arg)
            elif i > 0 and arguments[i - 1] in result:
                # value of the previous option, e.g. `--slowms 1000`
                result.append('"%s"' % arg)

        return ' '.join(result)

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

    def _get_log_path(self, command_str):
        match = re.search(r'--logpath\s+("[^"]+"|\'[^\']+\'|\S+)', command_str)
        if not match:
            return None
        path = match.group(1)
        if len(path) >= 2 and path[0] == path[-1] and path[0] in ('"', "'"):
            path = path[1:-1]
        return path

    def _binary_version(self, binary):
        """Version string reported by a specific mongod/mongos binary.

        Cached per path. Returns None when the binary cannot be run or its
        output cannot be parsed.
        """
        cache = self.__dict__.setdefault('_binary_version_cache', {})
        if binary in cache:
            return cache[binary]
        version = None
        try:
            out = subprocess.check_output([binary, '--version'],
                                          stderr=subprocess.STDOUT,
                                          timeout=30)
            version = _extract_server_version(out.decode('utf-8', 'replace'))
        except (OSError, subprocess.SubprocessError):
            pass
        cache[binary] = version
        return version

    def _command_version(self, command_str):
        """Version of the binary a stored startup command will run.

        Falls back to self.current_version when the binary can't be probed.
        """
        try:
            argv = shlex.split(command_str.strip())
        except ValueError:
            argv = []
        if argv and argv[0] == 'nohup':
            argv = argv[1:]
        if argv:
            version = self._binary_version(argv[0])
            if version:
                return version
        return self.current_version

    def _macos_fork_unsupported(self, version=None):
        """MongoDB 8.2+ rejects --fork on macOS (fork+exec is incompatible).

        version defaults to self.current_version. Pass the version of the
        binary in a stored startup command when relaunching.
        """
        if sys.platform != 'darwin':
            return False
        if version is None:
            version = self.current_version
        try:
            major_s, minor_s = version.split('.')[:2]
            major, minor = int(major_s), int(minor_s)
        except (AttributeError, TypeError, ValueError, IndexError):
            return False
        return (major, minor) >= (8, 2)

    def _needs_python_detach(self, command_str):
        """True when the launch command must not be waited on via the shell.

        --fork is what used to make mongod's parent exit only after startup.
        nohup ... & returns immediately, so mlaunch continues init before the
        server is listening. On macOS 8.2+ there is no --fork, so we detach
        in Python and wait ourselves.
        """
        if os.name == 'nt':
            return False
        stripped = command_str.strip()
        if stripped.startswith('nohup ') or stripped.endswith('&'):
            return True
        return self._macos_fork_unsupported(self._command_version(command_str))

    def _launch_argv(self, command_str):
        """Argv for a startup command, without shell daemonization."""
        cmd = command_str.strip()
        backgrounded = cmd.startswith('nohup ') or cmd.endswith('&')
        if cmd.startswith('nohup '):
            cmd = cmd[6:].strip()
        cmd = re.sub(r'\s*>\s*/dev/null(?:\s+2>&1)?\s*&\s*$', '', cmd).strip()
        argv = shlex.split(cmd)
        if backgrounded or self._macos_fork_unsupported(
                self._command_version(command_str)):
            argv = [arg for arg in argv if arg != '--fork']
        return argv

    def _process_is_listening(self, proc, port):
        """True when this process, not a previous one, is bound to port."""
        if proc.poll() is not None:
            return False
        try:
            process = psutil.Process(proc.pid)
            connections = getattr(process, 'net_connections', process.connections)
            for conn in connections(kind='inet'):
                if (conn.status == psutil.CONN_LISTEN and conn.laddr
                        and conn.laddr.port == int(port)):
                    return True
        except (psutil.Error, OSError):
            return False
        return False

    def _spawn_and_wait(self, command_str, port, timeout=300,
                        lock_retry=30):
        """Like _spawn_once, but retry while the dbpath lock is still held.

        A previous mongod on the same dbpath can still be releasing its lock
        after mlaunch stop returns. mongod then exits with code 100 and
        DBPathInUse; retry for up to lock_retry seconds instead of failing.
        """
        deadline = time.time() + lock_retry
        while True:
            try:
                return self._spawn_once(command_str, port, timeout)
            except subprocess.CalledProcessError as e:
                # output is only this attempt. An older DBPathInUse line
                # in an appended log must not extend the retry.
                if (e.returncode == 100 and 'DBPathInUse' in (e.output or '')
                        and time.time() < deadline):
                    time.sleep(0.5)
                    continue
                raise

    def _spawn_once(self, command_str, port, timeout=300):
        """Start mongod/mongos in a new session and wait until it listens.

        This replaces --fork: the caller does not return until startup has
        finished or the process has exited. Readiness is the new process
        accepting connections, so a server that is still shutting down on
        the same port does not count.
        """
        argv = self._launch_argv(command_str)
        mark = self._log_mark(command_str)
        stdout_fh = stderr_fh = None
        stdout_path = stderr_path = None
        try:
            # Files, not pipes: a full pipe can stall mongod before it
            # opens its own log. DEVNULL drops errors that never reach
            # --logpath (bad options, a rejected --fork, an unopenable log).
            stdout_fh = tempfile.NamedTemporaryFile(
                prefix='mlaunch-', suffix='.out', delete=False)
            stderr_fh = tempfile.NamedTemporaryFile(
                prefix='mlaunch-', suffix='.err', delete=False)
            stdout_path = stdout_fh.name
            stderr_path = stderr_fh.name
            os.set_inheritable(stdout_fh.fileno(), True)
            os.set_inheritable(stderr_fh.fileno(), True)
            try:
                proc = subprocess.Popen(
                    argv,
                    stdin=subprocess.DEVNULL,
                    stdout=stdout_fh,
                    stderr=stderr_fh,
                    start_new_session=True,
                    close_fds=True,
                )
            except OSError as e:
                raise SystemExit("can't start %s on port %s: %s"
                                 % (argv[0] if argv else command_str, port,
                                    e.strerror or e))
            finally:
                stdout_fh.close()
                stderr_fh.close()
                stdout_fh = stderr_fh = None

            deadline = time.time() + timeout
            while True:
                returncode = proc.poll()
                if returncode is not None:
                    output = self._attempt_output(
                        command_str, mark, stdout_path, stderr_path)
                    raise subprocess.CalledProcessError(
                        returncode, command_str, output=output)
                if self._process_is_listening(proc, port):
                    return proc
                if time.time() > deadline:
                    detail = self._attempt_output(
                        command_str, mark, stdout_path, stderr_path)
                    log_path = self._get_log_path(command_str)
                    extra = ('\n' + detail) if detail else ''
                    raise SystemExit(
                        "still starting %s on port %s after %ss (pid %s). "
                        "left the process running.%s\nlog: %s"
                        % (os.path.basename(argv[0]) if argv else 'mongod',
                           port, timeout, proc.pid, extra, log_path))
                time.sleep(0.2)
        finally:
            for handle in (stdout_fh, stderr_fh):
                if handle is not None:
                    handle.close()
            for path in (stdout_path, stderr_path):
                if path:
                    try:
                        os.unlink(path)
                    except OSError:
                        pass

    def _log_mark(self, command_str):
        """(device, inode, size) of the log before this spawn.

        None when there is no log yet. A later read starts at this size
        so an appended file does not replay earlier attempts.
        """
        log_path = self._get_log_path(command_str)
        if not log_path:
            return None
        try:
            st = os.stat(log_path)
        except OSError:
            return None
        return (st.st_dev, st.st_ino, st.st_size)

    def _read_log_since(self, command_str, mark):
        """Log text written after mark.

        A shorter file or a new inode means mongod replaced the log, so
        this attempt owns the whole file. A text backtrace still ends the
        read, as it did before.
        """
        log_path = self._get_log_path(command_str)
        if not log_path:
            return ''
        try:
            st = os.stat(log_path)
            with open(log_path, 'rb') as logfile:
                offset = 0
                if mark is not None:
                    dev, ino, size = mark
                    if ((st.st_dev, st.st_ino) == (dev, ino)
                            and st.st_size >= size):
                        offset = size
                logfile.seek(offset)
                chunks = []
                for line in logfile:
                    if line.startswith(b'----- BEGIN BACKTRACE -----'):
                        break
                    chunks.append(line.decode('utf-8', 'replace'))
        except OSError:
            return ''
        return ''.join(chunks)

    def _read_capture(self, *paths):
        parts = []
        for path in paths:
            if not path:
                continue
            try:
                with open(path, 'rb') as handle:
                    data = handle.read(65536)
            except OSError:
                continue
            text = data.decode('utf-8', 'replace').strip()
            if text:
                parts.append(text)
        return '\n'.join(parts)

    def _attempt_output(self, command_str, mark, stdout_path, stderr_path):
        """Console text plus the log bytes this attempt added."""
        captured = self._read_capture(stdout_path, stderr_path)
        log_text = self._read_log_since(command_str, mark).strip()
        return '\n'.join(part for part in (captured, log_text) if part)

    @staticmethod
    def _strip_keyfile(command_str):
        """Remove --keyFile and its value from a stored command line.

        The value may be a quoted path that contains spaces. Matching only
        non-space characters stops inside that path and leaves a broken
        quote for the shell.
        """
        return re.sub(
            r'''--keyFile\s+("[^"]*"|'[^']*'|\S+)''', '', command_str)

    def _wait_for_primary(self):

        members = self.config_docs[self.args['name']]['members']
        hosts = [self._node_address(member['host'].rsplit(':', 1)[-1])
                 for member in members]
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

    def _read_key_file(self, keyfile=None):
        if not keyfile:
            with open(os.path.join(self.dir, 'keyfile'), 'rb') as f:
                return ''.join(f.readlines())
        else:
            with open(keyfile, 'rb') as f:
                return ''.join(f.readlines())

def main():
    tool = MLaunchTool()
    tool.run()


if __name__ == '__main__':
    sys.exit(main())
