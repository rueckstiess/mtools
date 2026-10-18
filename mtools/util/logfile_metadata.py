#!/usr/bin/env python3
"""Log metadata and restart detection for LogFile."""

import os
import re

from mtools.util.logevent import LogEvent


class MetadataMixin(object):
    """Read version, restart, and replica-set metadata from a log."""

    def _extract_metadata_legacy(self, line):
        """Extract metadata from legacy log line format"""

        if (self._has_level is None and
                line[28:31].strip() in LogEvent.log_levels and
                line[31:39].strip() in LogEvent.log_components):
            self._has_level = True

        # find version string (fast check to eliminate most lines)
        if "version" in line[:100]:
            logevent = LogEvent(line)
            restart = self._check_for_restart_legacy(logevent)
            if restart:
                self._restarts.append((restart, logevent))

        # look for hostname and port which will be logged with pid
        if not self._hostname:
            if " pid=" in line:
                match = re.search(r'port=(?P<port>\d+).*host=(?P<host>\S+)',
                                line)
                if match:
                    self._hostname = match.group('host')
                    self._port = match.group('port')

        """ For 3.0 the "[initandlisten] options:" long entry contained the
            "engine" field if WiredTiger was the storage engine. There were
            only two engines, MMAPv1 and WiredTiger
        """
        if "[initandlisten] options:" in line:
            match = re.search(r'replSet: "(?P<replSet>\S+)"', line)
            if match:
                self._repl_set = match.group('replSet')

            match = re.search(r'engine: "(?P<engine>\S+)"', line)
            if match:
                self._storage_engine = match.group('engine')
            else:
                self._storage_engine = 'mmapv1'

        """ For 3.2 the "[initandlisten] options:" no longer contains the
            "engine" field So now we have to look for the "[initandlisten]
            wiredtiger_open config:" which was present in 3.0, but would
            now tell us definitively that wiredTiger is being used
        """
        if "[initandlisten] wiredtiger_open config:" in line:
            self._storage_engine = 'wiredTiger'

        if "command admin.$cmd command: { replSetInitiate:" in line:
            match = re.search(r'{ _id: "(?P<replSet>\S+)", '
                                r'members: (?P<replSetMembers>[^]]+ ])', line)
            if match:
                self._repl_set = match.group('replSet')
                self._repl_set_members = match.group('replSetMembers')

        # Replica set config logging in MongoDB 3.0+
        new_config = ("New replica set config in use: ")
        if new_config in line:
            match = re.search(r'{ _id: "(?P<replSet>\S+)", '
                                r'version: (?P<replSetVersion>\d+), ', line)
            if match:
                self._repl_set = match.group('replSet')
                self._repl_set_version = match.group('replSetVersion')
            match = re.search(r', protocolVersion: (?P<replSetProtocol>\d+), ', line)
            if match:
                self._repl_set_protocol = match.group('replSetProtocol')
            match = re.search(r'members: (?P<replSetMembers>[^]]+ ])', line)
            if match:
                self._repl_set_members = match.group('replSetMembers')

        # if ("is now in state" in line and
        #        next(state for state in states if line.endswith(state))):
        if "is now in state" in line:
            tokens = line.split()
            # 2.6
            if tokens[1].endswith(']'):
                pos = 4
            else:
                pos = 5
            host = tokens[pos]
            rs_state = tokens[-1]
            state = (host, rs_state, LogEvent(line))
            self._rs_state.append(state)
            return

        if "[rsMgr] replSet" in line:
            tokens = line.split()
            if self._hostname:
                host = self._hostname + ':' + self._port
            else:
                host = os.path.basename(self.name)
            host += ' (self)'
            if tokens[-1] in self.states:
                rs_state = tokens[-1]
            else:
                # 2.6
                if tokens[1].endswith(']'):
                    pos = 2
                else:
                    pos = 6
                rs_state = ' '.join(tokens[pos:])

            state = (host, rs_state, LogEvent(line))
            self._rs_state.append(state)
            return

    def _check_for_restart_legacy(self, logevent):

        if (logevent.thread == 'initandlisten' and
                "db version v" in logevent.line_str):
            self._binary = 'mongod'

        elif logevent.thread == 'mongosMain' and ('MongoS' in logevent.line_str or 
            'mongos' in logevent.line_str):
            self._binary = 'mongos'

        else:
            return False

        version = re.search(r'(?:db|mongos) version v(\d\.\d\.\d+)', logevent.line_str)

        if version:
            version = version.group(1)
            return version
        else:
            return False

    def _check_for_restart_logv2(self, doc):
        if not doc['ctx'] in ('initandlisten', 'mongosMain'):
            return

        if not self._hostname:
            if doc['msg'] == 'MongoDB starting':
                self._hostname = doc['attr'].get('host')

        if not self._clusterrole:
            if doc['msg'] == 'Options set by command line':
                if doc['attr']['options'].get('sharding'):
                    self._clusterrole = \
                        doc['attr']['options']['sharding'].get('clusterRole')

        if not self._port:
            if doc['msg'] == 'MongoDB starting':
                self._port = doc['attr'].get('port')
            elif doc['msg'] == 'Options set by command line':
                if doc['attr']['options'].get('net'):
                    self._port = doc['attr']['options']['net'].get('port')
                else:
                    # process will be listening on default port
                    if self._clusterrole is None:
                        self._port = 27017
                    elif self._clusterrole == 'shardsvr':
                        self._port = 27018
                    elif self._clusterrole == 'configsvr':
                        self._port = 27019

        if not self._storage_engine or not self._repl_set:
            if doc['msg'] == 'Options set by command line':
                if doc['attr']['options'].get('storage'):
                    self._storage_engine = \
                        doc['attr']['options']['storage'].get('engine', 'wiredTiger')
                if doc['attr']['options'].get('replication'):
                    self._repl_set = \
                        doc['attr']['options']['replication'].get('replSetName')

        # Which binary and version is running?
        version = False
        if doc['msg'] == 'Build Info':
            version = doc['attr']['buildInfo'].get('version', False)
            if doc['ctx'] == 'mongosMain':
                self._binary = 'mongos'
            else:
                self._binary = 'mongod'

        return version

    # FIXME
    def _extract_metadata_logv2(self, line):
        """Extract metadata from logv2 JSON format"""
        le = LogEvent(line, True)
        doc = le.doc

        # logv2 always has levels & components
        if self._has_level is None:
            self._has_level = True

        if not doc:
            return

        if doc['ctx'] in ('initandlisten', 'mongosMain'):
            restart = self._check_for_restart_logv2(doc)
            if restart:
                self._restarts.append((restart, le))

        # TODO: add storage engine detection
        self._storage_engine = 'wiredTiger'
        # if "command admin.$cmd command: { replSetInitiate:" in doc:
        #     match = re.search('{ _id: "(?P<replSet>\S+)", '
        #                         'members: (?P<replSetMembers>[^]]+ ])', doc)
        #     if match:
        #         self._repl_set = match.group('replSet')
        #         self._repl_set_members = match.group('replSetMembers')

        # Replica set config logging in MongoDB 3.0+
        # new_config = ("New replica set config in use: ")
        # if new_config in doc:
        #     match = re.search('{ _id: "(?P<replSet>\S+)", '
        #                         'version: (?P<replSetVersion>\d+), ', doc)
        #     if match:
        #         self._repl_set = match.group('replSet')
        #         self._repl_set_version = match.group('replSetVersion')
        #     match = re.search(', protocolVersion: (?P<replSetProtocol>\d+), ', doc)
        #     if match:
        #         self._repl_set_protocol = match.group('replSetProtocol')
        #     match = re.search('members: (?P<replSetMembers>[^]]+ ])', doc)
        #     if match:
        #         self._repl_set_members = match.group('replSetMembers')


        # if ("is now in state" in line and
        #        next(state for state in states if line.endswith(state))):
        # if "is now in state" in doc:
        #     tokens = doc.split()
        #     # 2.6
        #     if tokens[1].endswith(']'):
        #         pos = 4
        #     else:
        #         pos = 5
        #     host = tokens[pos]
        #     rs_state = tokens[-1]
        #     state = (host, rs_state, LogEvent(doc))
        #     self._rs_state.append(state)
        #     return

        # if "[rsMgr] replSet" in doc:
        #     tokens = doc.split()
        #     if self._hostname:
        #         host = self._hostname + ':' + self._port
        #     else:
        #         host = os.path.basename(self.name)
        #     host += ' (self)'
        #     if tokens[-1] in self.states:
        #         rs_state = tokens[-1]
        #     else:
        #         # 2.6
        #         if tokens[1].endswith(']'):
        #             pos = 2
        #         else:
        #             pos = 6
        #         rs_state = ' '.join(tokens[pos:])

        #     state = (host, rs_state, LogEvent(line))
        #     self._rs_state.append(state)
        #     return
