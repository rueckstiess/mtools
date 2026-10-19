#!/usr/bin/env python3
"""Sharding discovery for LogFile."""

import json
import re

from dateutil.parser import parse as parse_datetime

from mtools.util.logevent import LogEvent
from mtools.util.logformat import LogFormat

# MongoDB 4.4 structured log ids. The stable ``msg`` is checked as well so a
# renamed id still matches the same event.
_MONITOR_ID = 4603701          # Starting Replica Set Monitor
_REPL_CONFIG_ID = 21392        # New replica set config in use
_CHANGELOG_ID = 22080          # About to log metadata event
_SLOW_QUERY_ID = 51803         # Slow query
_SPLIT_LOOKUP_ID = 22107       # Requested split points lookup for chunk
_AUTOSPLIT_ID = 21908          # autosplitted chunk
_AUTOSPLIT_FAILED_ID = 21910   # Unable to auto-split chunk
_JUMBO_ID = 21873              # Marking chunk as jumbo

_STEP_RE = re.compile(r'^step \d+ of \d+$')


def _json_object(line):
    """Return a logv2 document, or None when the line is not JSON."""
    if isinstance(line, bytes):
        line = line.decode('utf-8', 'replace')
    line = line.strip()
    if not line.startswith('{'):
        return None
    try:
        doc = json.loads(line)
    except json.JSONDecodeError:
        return None
    if isinstance(doc, dict):
        return doc
    return None


def _event_time(doc):
    """Timezone-aware time from a logv2 ``t.$date`` field."""
    try:
        raw = doc['t']['$date']
    except (KeyError, TypeError):
        return None
    if not isinstance(raw, str):
        return None
    try:
        return parse_datetime(raw)
    except (ValueError, OverflowError, TypeError):
        return None


def _namespace(value):
    """Collection namespace from a string or a NamespaceString object."""
    if isinstance(value, str):
        return value
    if not isinstance(value, dict):
        return None
    if isinstance(value.get('ns'), str):
        return value['ns']
    database = value.get('db') or ''
    collection = value.get('coll') or ''
    if isinstance(database, dict):
        database = database.get('db') or ''
    if database and collection:
        return '%s.%s' % (database, collection)
    if isinstance(database, str) and database:
        return database
    return None


def _error_text(value):
    """Short error string from a log attribute."""
    if value is None or value == '':
        return None
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        for key in ('codeName', 'errmsg', 'reason'):
            text = value.get(key)
            if text:
                return str(text)
    return json.dumps(value, sort_keys=True, default=str)


def _line_error(attr):
    """Error carried on a structured log line, if any."""
    if not isinstance(attr, dict):
        return None
    return _error_text(attr.get('error') or attr.get('errmsg'))


def _bounds_text(min_key, max_key):
    """Stable range string for a chunk min and max."""
    if min_key is None and max_key is None:
        return None
    return 'min: %s, max: %s' % (
        json.dumps(min_key, sort_keys=True, default=str),
        json.dumps(max_key, sort_keys=True, default=str))


def _chunk_range(value):
    """Range text from a chunk attribute that is a string or a document."""
    if isinstance(value, str):
        return value
    if not isinstance(value, dict):
        return None
    if 'min' in value or 'max' in value:
        return _bounds_text(value.get('min'), value.get('max'))
    nested = value.get('chunkInfo')
    if isinstance(nested, dict):
        return _chunk_range(nested)
    return None


def _migration_steps(details):
    """``(step name, milliseconds)`` pairs from a moveChunk details document."""
    steps = []
    for key, value in details.items():
        if not _STEP_RE.match(str(key)):
            continue
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            continue
        steps.append((str(key), str(int(value))))
    return steps


def _member_hosts(members):
    """Comma-separated hosts from a replica set config members array."""
    if not isinstance(members, list):
        return ''
    hosts = []
    for member in members:
        if isinstance(member, dict) and member.get('host'):
            hosts.append(str(member['host']))
    return ','.join(hosts)


def _monitor_target(uri):
    """``(set name, hosts)`` from a replica-set monitor URI.

    MongoDB logs id 4603701 with ``uri`` set to ``MongoURI::toString()``.
    That is ``mongodb://host,host/?replicaSet=name`` or ``name/host,host``.
    """
    if not isinstance(uri, str) or not uri:
        return None
    if '://' in uri:
        rest = uri.split('://', 1)[1]
        if '@' in rest:
            rest = rest.split('@', 1)[1]
        hosts, _, query = rest.partition('?')
        hosts = hosts.split('/')[0]
        name = None
        for part in query.split('&'):
            key, _, value = part.partition('=')
            if key == 'replicaSet' and value:
                name = value
                break
        if not name or not hosts:
            return None
        return name, hosts
    if '/' not in uri:
        return None
    name, hosts = uri.split('/', 1)
    hosts = hosts.split('?')[0]
    if not name or not hosts:
        return None
    return name, hosts


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
                        match = re.search(r"for (?P<csrsName>\w+)/"
                                          r"(?P<replSetMembers>\S+)", line)
                        if match:
                            csrs_info = (match.group('csrsName'),
                                         match.group('replSetMembers'))
                            self._csrs = csrs_info
                    else:
                        match = re.search(r"for (?P<shardName>\w+)/"
                                          r"(?P<replSetMembers>\S+)", line)
                        if match:
                            shard_info = (match.group('shardName'),
                                          match.group('replSetMembers'))
                            self._shards.append(shard_info)

            elif self.binary == "mongod":
                logevent = LogEvent(line)
                if "New replica set config in use" in line:

                    if "configsvr: true" in line:
                        match = re.search(r' _id: "(?P<replSet>\S+)".*'
                                          'members: (?P<replSetMembers>[^]]+ ])', line)
                        if match:
                            self._csrs = (
                                match.group('replSet'),
                                match.group('replSetMembers')
                            )

                if "Starting new replica set monitor for" in line:
                    match = re.search(r"for (?P<replSet>\w+)/"
                                      r"(?P<replSetMembers>\S+)", line)
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
                match = re.search(r'ns: "(?P<namespace>\S+)".*'
                                  r'details: { (?P<range>.*\}).*'
                                  r'to: "(?P<movedTo>\S+)".*note: "(?P<note>\S+)"', line)
                if match:
                    time = logevent.datetime
                    chunk_range = match.group('range')
                    namespace = match.group('namespace')
                    moved_to = match.group('movedTo')
                    note = match.group('note')

                    if note == "success":
                        errmsg = None
                        steps = re.findall(r'(?P<steps>step \d of \d): (?P<stepTimes>\d+)', line)
                    else:
                        match = re.search(r':: caused by :: (?P<errmsg>\S+):', prev_line)
                        steps = None
                        if match:
                            errmsg = match.group('errmsg')
                        else:
                            errmsg = "Unknown"

                    chunk_migration = (time, chunk_range, moved_to, namespace, steps, note, errmsg)

                    self._chunks_moved_from.append(chunk_migration)

            if "moveChunk.to" in line:
                logevent = LogEvent(line)
                match = re.search(r'ns: "(?P<namespace>\S+)".*'
                                  r'details: { (?P<range>.*\}).*.*note: "(?P<note>\S+)"', line)
                if match:
                    time = logevent.datetime
                    chunk_range = match.group('range')
                    namespace = match.group('namespace')
                    # TODO: alter this to find the moved-from shard name
                    # when SERVER-45770 is added
                    moved_from = "Unknown"
                    note = match.group('note')

                    if note == "success":
                        errmsg = None
                        steps = re.findall(r'(?P<steps>step \d of \d): (?P<stepTimes>\d+)', line)
                    else:
                        steps = None
                        match = re.search(r'errmsg: "(?P<errmsg>.*)"', line)
                        if match:
                            errmsg = match.group('errmsg')

                    chunk_migration = (time, chunk_range, moved_from,
                                       namespace, steps, note, errmsg)

                    self._chunks_moved_to.append(chunk_migration)

            if "Finding the split vector for" in line:
                logevent = LogEvent(line)
                match = re.search(r'for (?P<namespace>\S+).*'
                                  r'numSplits: (?P<numSplits>\d+)', line)
                if match:
                    time = logevent.datetime
                    split_range = None
                    namespace = match.group("namespace")
                    numSplits = match.group('numSplits')
                    success = None
                    time_taken = 0
                    error = None
                    self._chunk_splits.append(
                        (time, split_range, namespace, numSplits, success, time_taken, error))
            elif "splitVector" in line:
                logevent = LogEvent(line)
                match = re.search(r'splitVector: "(?P<namespace>\S+)".*,'
                                  r' (?P<range>min:.*), max.*op_msg (?P<time_taken>\d+)', line)
                if match:
                    time = logevent.datetime
                    split_range = match.group("range")
                    namespace = match.group("namespace")
                    time_taken = match.group("time_taken")
                    numSplits = 0
                    success = True
                    error = None
                    self._chunk_splits.append(
                        (time, split_range, namespace, numSplits, success, time_taken, error))
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
                    self._chunk_splits.append(
                        (time, split_range, namespace, numSplits, success, time_taken, error))
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
                    self._chunk_splits.append(
                        (time, split_range, namespace, numSplits, success, time_taken, error))

            prev_line = line

        # reset logfile
        self._seek(0)
        self._lines_read = 0

    def _find_sharding_info_logv2(self):
        """Read MongoDB 4.4+ structured logs for shards, moves, and splits."""
        self._shards = []
        self._chunks_moved_from = []
        self._chunks_moved_to = []
        self._chunk_splits = []

        # Metadata scan rewinds the file. Run it before this walk.
        binary = self.binary
        prev_error = None
        for line in self.filehandle:
            doc = _json_object(line)
            if doc is None:
                prev_error = None
                continue
            attr = doc.get('attr')
            if not isinstance(attr, dict):
                attr = {}
            self._consume_logv2_line(binary, doc, attr, prev_error)
            prev_error = _line_error(attr)

        self._seek(0)
        self._lines_read = 0

    def _consume_logv2_line(self, binary, doc, attr, prev_error):
        """Dispatch one structured log line to the matching recorder."""
        msg = doc.get('msg') or ''
        log_id = doc.get('id')
        if log_id == _REPL_CONFIG_ID or msg == 'New replica set config in use':
            self._record_repl_config(attr.get('config'))
        elif log_id == _MONITOR_ID or msg == 'Starting Replica Set Monitor':
            self._record_monitor(binary, doc.get('ctx'), attr.get('uri'))
        elif log_id == _CHANGELOG_ID or msg == 'About to log metadata event':
            self._record_changelog(_event_time(doc), attr.get('event'), prev_error)
        elif log_id == _SLOW_QUERY_ID or msg == 'Slow query':
            self._record_slow_split(_event_time(doc), attr)
        elif log_id == _SPLIT_LOOKUP_ID or msg == (
                'Requested split points lookup for chunk'):
            self._record_split_lookup(_event_time(doc), attr)
        elif log_id == _AUTOSPLIT_ID or msg == 'autosplitted chunk':
            self._record_autosplit(_event_time(doc), attr)
        elif log_id == _AUTOSPLIT_FAILED_ID or msg == 'Unable to auto-split chunk':
            self._record_failed_split(_event_time(doc), attr)
        elif log_id == _JUMBO_ID or msg == 'Marking chunk as jumbo':
            self._record_jumbo(_event_time(doc), attr)

    def _record_repl_config(self, config):
        """Remember a config server from id 21392 when ``configsvr`` is set."""
        if not isinstance(config, dict) or not config.get('configsvr'):
            return
        name = config.get('_id')
        if not name:
            return
        self._csrs = (name, _member_hosts(config.get('members')))

    def _record_monitor(self, binary, ctx, uri):
        """Classify id 4603701 as the CSRS or as a shard."""
        target = _monitor_target(uri)
        if target is None:
            return
        name, hosts = target
        if binary == 'mongos':
            if ctx == 'mongosMain':
                self._csrs = (name, hosts)
            else:
                self._shards.append((name, hosts))
            return
        if self._csrs and name != self._csrs[0]:
            self._shards.append((name, hosts))
        elif not self._csrs:
            self._csrs = (name, hosts)

    def _record_changelog(self, when, event, prev_error):
        """Record id 22080 when the changelog event is a chunk move."""
        if when is None or not isinstance(event, dict):
            return
        what = event.get('what')
        if what not in ('moveChunk.from', 'moveChunk.to'):
            return
        details = event.get('details')
        if not isinstance(details, dict):
            details = {}
        namespace = _namespace(event.get('ns'))
        note = details.get('note')
        chunk_range = _bounds_text(details.get('min'), details.get('max'))
        if note == 'success':
            steps = _migration_steps(details)
            errmsg = None
        else:
            steps = None
            errmsg = _error_text(details.get('errmsg')) or prev_error or 'Unknown'
        if what == 'moveChunk.from':
            moved = details.get('to') or 'Unknown'
            self._chunks_moved_from.append(
                (when, chunk_range, moved, namespace, steps, note, errmsg))
        else:
            # Donor is present on the structured event. Legacy text logs
            # left it as Unknown.
            moved = details.get('from') or 'Unknown'
            self._chunks_moved_to.append(
                (when, chunk_range, moved, namespace, steps, note, errmsg))

    def _record_slow_split(self, when, attr):
        """Record a splitVector slow query (id 51803)."""
        if when is None:
            return
        command = attr.get('command')
        if not isinstance(command, dict) or 'splitVector' not in command:
            return
        duration = attr.get('durationMillis')
        if isinstance(duration, bool) or not isinstance(duration, (int, float)):
            taken = []
        else:
            taken = [str(int(duration))]
        self._chunk_splits.append((
            when,
            _bounds_text(command.get('min'), command.get('max')),
            _namespace(command.get('splitVector')),
            0,
            True,
            taken,
            None))

    def _record_split_lookup(self, when, attr):
        """Record id 22107. This message has no split count."""
        if when is None:
            return
        self._chunk_splits.append((
            when,
            _bounds_text(attr.get('minKey'), attr.get('maxKey')),
            _namespace(attr.get('namespace')),
            0,
            None,
            [],
            None))

    def _record_autosplit(self, when, attr):
        """Record a successful autosplit (id 21908)."""
        if when is None:
            return
        count = attr.get('splitPoints')
        if isinstance(count, bool) or not isinstance(count, (int, float)):
            count = 0
        self._chunk_splits.append((
            when,
            _bounds_text(attr.get('minKey'), attr.get('maxKey')),
            _namespace(attr.get('namespace')),
            int(count),
            True,
            [],
            None))

    def _record_failed_split(self, when, attr):
        """Record id 21910."""
        if when is None:
            return
        self._chunk_splits.append((
            when,
            _chunk_range(attr.get('chunk')),
            _namespace(attr.get('namespace')),
            0,
            False,
            [],
            _error_text(attr.get('error')) or 'Unknown'))

    def _record_jumbo(self, when, attr):
        """Record id 21873. 4.4 puts the chunk text in ``chunk`` only."""
        if when is None:
            return
        namespace = _namespace(attr.get('namespace')) or ''
        self._chunk_splits.append((
            when,
            _chunk_range(attr.get('chunk')),
            namespace,
            0,
            False,
            [],
            'Jumbo'))

    def _find_sharding_info(self):
        """
        Iterate over file and find any sharding related information
        """
        self._shards = []
        self._chunks_moved_from = []
        self._chunks_moved_to = []
        self._chunk_splits = []

        if self.logformat == LogFormat.LEGACY:
            self._find_sharding_info_legacy()
        else:
            self._find_sharding_info_logv2()
