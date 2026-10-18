#!/usr/bin/env python3
"""Process lifetime helpers for mlaunch."""

import os
import queue as Queue
import shlex
import signal
import subprocess
import sys
import threading
import time

import psutil
from pymongo.errors import AutoReconnect, ConnectionFailure, OperationFailure


def wait_for_host(port, interval=1, timeout=30, to_start=True, queue=None,
                  ssl_pymongo_options=None, tls_pymongo_options=None,
                  node_host='localhost'):
    """
    Ping server and wait for response.

    Ping a mongod or mongos every `interval` seconds until it responds, or
    `timeout` seconds have passed. If `to_start` is set to False, will wait for
    the node to shut down instead. This function can be called as a separate
    thread.

    If queue is provided, it will place the results in the message queue and
    return, otherwise it will just return the result directly.
    """
    from mtools.mlaunch.mlaunch import MongoConnection, format_node_address
    host = format_node_address(node_host, port)
    start_time = time.time()
    while True:
        if (time.time() - start_time) > timeout:
            if queue:
                queue.put_nowait((port, False))
            return False
        try:
            # make connection and ping host
            con = MongoConnection(host, directConnection=True,
                                  **(ssl_pymongo_options or {}),
                                  **(tls_pymongo_options or {}))
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


def shutdown_host(port, username=None, password=None, authdb=None,
                  node_host='localhost'):
    """
    Send the shutdown command to a mongod or mongos on given port.

    This function can be called as a separate thread.
    """
    from mtools.mlaunch.mlaunch import MongoConnection, format_node_address
    host = format_node_address(node_host, port)
    try:
        if username and password and authdb:
            if authdb != "admin":
                raise RuntimeError(
                    "given username/password is not for admin database")
            mc = MongoConnection(host, username=username, password=password,
                                 directConnection=True)
        else:
            mc = MongoConnection(host, directConnection=True)

        try:
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


class ProcessMixin(object):
    """Start, stop, and inspect mlaunch mongod and mongos processes."""

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
            # Every node is already up. Scripts re-run start, so this is
            # success rather than an error.
            print('all nodes already running.')
            return

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

    def kill(self):
        self.discover()

        # get matching tags, can only send signals to running nodes
        matches = self._get_ports_from_args(self.args, 'running')
        processes = self._get_processes()

        # convert signal to int, default is SIGTERM for graceful shutdown
        sig = self.args.get('signal') or 'SIGTERM'
        if os.name == 'nt':
            sig = signal.CTRL_BREAK_EVENT
        if isinstance(sig, int):
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
        signalled = []
        for port in processes:
            # only send signal to matching processes
            if port in matches:
                p = processes[port]
                p.send_signal(sig)
                signalled.append(p)
                if self.args['verbose']:
                    print(" %s on port %i, pid=%i" % (p.name, port, p.pid))

        print("sent signal %s to %i process%s."
              % (sig, len(matches), '' if len(matches) == 1 else 'es'))

        # A shutdown signal returns before mongod has released its dbpath
        # lock and port. Without --fork, an immediate start can race it and
        # fail with DBPathInUse, so wait for terminating processes to exit.
        if os.name != 'nt' and sig in (signal.SIGTERM, signal.SIGINT,
                                       signal.SIGKILL):
            _, alive = psutil.wait_procs(signalled, timeout=60)
            if alive:
                print("still shutting down after 60s: pid %s"
                      % ', '.join(str(p.pid) for p in alive))
        else:
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

    def is_running(self, port):
        """Return True if a host on a specific port is running."""
        try:
            con = self.client(self._node_address(port), directConnection=True)
            con.admin.command('ping')
            return True
        except (AutoReconnect, ConnectionFailure, OperationFailure):
            # Catch OperationFailure to work around SERVER-31916.
            return False

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
                self.ssl_pymongo_options, self.tls_pymongo_options,
                self._dial_host())))

        if self.args and 'verbose' in self.args and self.args['verbose']:
            print("waiting for nodes %s..."
                  % ('to start' if to_start else 'to shutdown'))

        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join()

        # get all results back and return tuple
        return tuple(queue.get_nowait() for _ in ports)

    def _get_last_error_log(self, command_str):
        return self._read_log_since(command_str, None)

    def _start_on_ports(self, ports, wait=False, override_auth=False):
        if override_auth and self.args['verbose']:
            print("creating cluster without auth for setup, "
                  "will enable auth at the end...")

        for port in ports:
            command_str = self.startup_info[str(port)]

            if override_auth:
                # this is to set up sharded clusters without auth first,
                # then relaunch with auth
                command_str = self._strip_keyfile(command_str)

            try:
                if os.name == 'nt':
                    # start /b is a cmd.exe builtin, so Windows keeps a shell.
                    subprocess.check_call(command_str, shell=True)
                    # create sub process on windows doesn't wait for output,
                    # wait a few seconds for mongod instance up
                    time.sleep(5)
                elif self._needs_python_detach(command_str):
                    # Detach, then block until the process is listening.
                    # --fork used to provide this barrier. nohup does not.
                    argv = self._launch_argv(command_str)
                    binary = os.path.basename(argv[0]) if argv else 'mongod'
                    if '--configsvr' in command_str:
                        binary = 'config server'
                    if self.args['verbose']:
                        print("launching: %s" % command_str)
                    else:
                        print("launching: %s on port %s" % (binary, port))
                    self._spawn_and_wait(command_str, port)
                else:
                    subprocess.check_output(shlex.split(command_str),
                                            stderr=subprocess.STDOUT)

                    binary = command_str.split()[0]
                    if '--configsvr' in command_str:
                        binary = 'config server'

                    if self.args['verbose']:
                        print("launching: %s" % command_str)
                    else:
                        print("launching: %s on port %s" % (binary, port))

            except subprocess.CalledProcessError as e:
                print(e.output)
                # Detach already put this attempt's console text and new
                # log bytes in e.output. The shell path still logs to the
                # file and leaves stdout empty.
                if not self._needs_python_detach(command_str):
                    print(self._get_last_error_log(command_str),
                          file=sys.stderr)
                log_path = self._get_log_path(command_str)
                raise SystemExit("can't start process, return code %i. "
                                 "tried to launch: %s\nlog: %s"
                                 % (e.returncode, command_str, log_path))
            except OSError as e:
                # Direct exec raises this when the binary is missing.
                # The shell path used to surface that as CalledProcessError.
                raise SystemExit("can't start process: %s\ntried to launch: %s"
                                 % (e, command_str))

        if wait:
            self.wait_for(ports)

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
