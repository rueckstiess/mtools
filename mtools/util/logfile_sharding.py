#!/usr/bin/env python3
"""Sharding discovery for LogFile."""

import re
import sys

from mtools.util.logevent import LogEvent
from mtools.util.logformat import LogFormat


class ShardingInfoMixin(object):
    """Find shard, CSRS, and chunk-move records in a log."""

    def _find_sharding_info_legacy(self):
        """
        Iterate over legacy log file and find any sharding related info
        """
        self._shards = []
        self._chunks_moved_from = []
        self._chunks_moved_to = []
        self._chunk_splits = []
        
        prev_line = ""

        for line in self.filehandle:
            if isinstance(line, bytes):
                line = line.decode("utf-8", "replace")

            if self.binary == "mongos":
        
                if "Starting new replica set monitor for" in line:
                    if "[mongosMain]" in line:
                        match = re.search("for (?P<csrsName>\w+)/"
                                          "(?P<replSetMembers>\S+)", line)
                        if match:
                            csrs_info = (match.group('csrsName'),
                                         match.group('replSetMembers'))
                            self._csrs = csrs_info
                    else:
                        match = re.search("for (?P<shardName>\w+)/"
                                          "(?P<replSetMembers>\S+)", line)
                        if match:
                            shard_info = (match.group('shardName'),
                                        match.group('replSetMembers'))
                            self._shards.append(shard_info)

            elif self.binary == "mongod":
                logevent = LogEvent(line)
                if "New replica set config in use" in line:
                    
                    if "configsvr: true" in line:
                        match = re.search(' _id: "(?P<replSet>\S+)".*'
                                          'members: (?P<replSetMembers>[^]]+ ])', line)
                        if match:
                            self._csrs = (
                                match.group('replSet'),
                                match.group('replSetMembers')
                            )

                if "Starting new replica set monitor for" in line:
                    match = re.search("for (?P<replSet>\w+)/"
                                        "(?P<replSetMembers>\S+)", line)
                    if match:
                        if self._csrs and match.group('replSet') != self._csrs[0]:
                            self._shards.append((
                                match.group('replSet'),
                                match.group('replSetMembers')
                            ))
                        elif not self._csrs:
                            self._csrs = (
                                match.group('replSet'),
                                match.group('replSetMembers')
                            )
    
            if "moveChunk.from" in line:
                logevent = LogEvent(line)
                match = re.search('ns: "(?P<namespace>\S+)".*'
                                  'details: { (?P<range>.*\}).*'
                                  'to: "(?P<movedTo>\S+)".*note: "(?P<note>\S+)"', line)
                if match:
                    time = logevent.datetime
                    chunk_range = match.group('range')
                    namespace = match.group('namespace')
                    moved_to = match.group('movedTo')
                    note = match.group('note')
                    
                    if note == "success":
                        errmsg = None
                        steps = re.findall('(?P<steps>step \d of \d): (?P<stepTimes>\d+)', line)
                    else:
                        match = re.search(':: caused by :: (?P<errmsg>\S+):', prev_line)
                        steps = None
                        if match:
                            errmsg = match.group('errmsg')
                        else:
                            errmsg = "Unknown"

                    chunk_migration = (time, chunk_range, moved_to, namespace, steps, note, errmsg)

                    self._chunks_moved_from.append(chunk_migration)

            if "moveChunk.to" in line:
                logevent = LogEvent(line)
                match = re.search('ns: "(?P<namespace>\S+)".*'
                                  'details: { (?P<range>.*\}).*.*note: "(?P<note>\S+)"', line)
                if match:
                    time = logevent.datetime
                    chunk_range = match.group('range')
                    namespace = match.group('namespace')
                    # TODO: alter this to find moved from shard name when SERVER-45770 TICKET is added
                    moved_from = "Unknown"
                    note = match.group('note')

                    if note == "success":
                        errmsg = None
                        steps = re.findall('(?P<steps>step \d of \d): (?P<stepTimes>\d+)', line)
                    else:
                        steps = None
                        match = re.search('errmsg: "(?P<errmsg>.*)"', line)
                        if match:
                            errmsg = match.group('errmsg')

                    chunk_migration = (time, chunk_range, moved_from, namespace, steps, note, errmsg)

                    self._chunks_moved_to.append(chunk_migration)

            if "Finding the split vector for" in line:
                logevent = LogEvent(line)
                match = re.search('for (?P<namespace>\S+).*'
                                  'numSplits: (?P<numSplits>\d+)', line)
                if match:
                    time = logevent.datetime
                    split_range = None
                    namespace = match.group("namespace")
                    numSplits = match.group('numSplits')
                    success = None
                    time_taken = 0
                    error = None
                    self._chunk_splits.append((time, split_range, namespace, numSplits, success, time_taken, error))
            elif "splitVector" in line:
                logevent = LogEvent(line)
                match = re.search('splitVector: "(?P<namespace>\S+)".*,'
                                  ' (?P<range>min:.*), max.*op_msg (?P<time_taken>\d+)', line)
                if match:
                    time = logevent.datetime
                    split_range = match.group("range")
                    namespace = match.group("namespace")
                    time_taken = match.group("time_taken")
                    numSplits = 0
                    success = True
                    error = None
                    self._chunk_splits.append((time, split_range, namespace, numSplits, success, time_taken, error))
            elif "Unable to auto-split chunk" in line:
                logevent = LogEvent(line)
                match = re.search(r"chunk \[(?P<range>.*)\) "
                                  r'in namespace (?P<namespace>\S+)'
                                  r' :: caused by :: (?P<error>\S+): ', line)
                if match:
                    time = logevent.datetime
                    split_range = match.group("range")
                    namespace = match.group("namespace")
                    numSplits = 0
                    success = False
                    time_taken = 0
                    error = match.group("error")
                    self._chunk_splits.append((time, split_range, namespace, numSplits, success, time_taken, error))
            elif "jumbo" in line:
                logevent = LogEvent(line)
                match = re.search(r'migration (?P<namespace>\S+): \[(?P<range>.*)\)', prev_line)
                if match:
                    time = logevent.datetime
                    split_range = match.group("range")
                    namespace = match.group("namespace")
                    numSplits = 0
                    success = False
                    time_taken = 0
                    error = "Jumbo"
                    self._chunk_splits.append((time, split_range, namespace, numSplits, success, time_taken, error))
            
            prev_line = line

        # reset logfile
        self._seek(0)

    # FIXME
    def _find_sharding_info_logv2(self):
        """
        Iterate over logv2 file and find any sharding related info
        """
        self._shards = []
        self._chunks_moved_from = []
        self._chunks_moved_to = []
        self._chunk_splits = []

        print(f"Sharding info extraction is not yet supported for: {self.logformat} ",
              file=sys.stderr)

    def _find_sharding_info(self):
        """
        Iterate over file and find any sharding related information
        """
        self._shards = []
        self._chunks_moved_from = []
        self._chunks_moved_to = []
        self._chunk_splits = []
        
        prev_line = ""

        # FIXME
        if self.logformat == LogFormat.LEGACY:
            self._find_sharding_info_legacy()
        else:
            self._find_sharding_info_logv2()
