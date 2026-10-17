from collections import namedtuple
from operator import itemgetter

from .base_section import BaseSection
from mtools.util import OrderedDict
from mtools.util.grouping import Grouping
from mtools.util.print_table import print_table
from mtools.util.logformat import LogFormat

try:
    import numpy as np
except ImportError:
    np = None

LogTuple = namedtuple('LogTuple', ['namespace', 'operation', 'pattern',
                                   'duration', 'allowDiskUse'])


# Commands that --queries already summarized, plus getMore. Modern servers
# log getMore as a command rather than the legacy getmore operation.
_QUERY_COMMANDS = ('count', 'findandmodify', 'geonear', 'find', 'aggregate',
                   'getmore')


def op_or_cmd(le):
    return le.operation if le.operation != 'command' else le.command


def _command_name(le):
    if not le.command:
        return ''
    return le.command.lower()


def _query_event(le):
    """Return True when this line belongs in the queries table."""
    return (le.operation in ('query', 'getmore', 'update', 'remove') or
            _command_name(le) in _QUERY_COMMANDS)


def _opens_cursor(le):
    """Return True when this line can be the command that opened a cursor."""
    return le.operation == 'query' or _command_name(le) in ('find', 'aggregate')


def _is_getmore(le):
    return le.operation == 'getmore' or _command_name(le) == 'getmore'


def _operation_name(le):
    operation = op_or_cmd(le)
    if operation and operation.lower() == 'getmore':
        return 'getmore'
    return operation


def _pattern_for(le, cursor_patterns):
    """
    Return the pattern this line is grouped by.

    A getMore uses the query that opened its cursor when that query is on
    the line or earlier in this file. Every other operation keeps its own
    pattern.
    """
    pattern = le.pattern
    if not _is_getmore(le):
        return pattern
    origin = le.originating_pattern
    if not origin:
        cursor_id = le.cursorid
        if cursor_id is not None:
            origin = cursor_patterns.get(cursor_id)
    if origin:
        return origin
    return pattern


def _remember_cursor(le, pattern, cursor_patterns):
    """Remember which query shape a cursor id belongs to."""
    if not pattern or not (_opens_cursor(le) or _is_getmore(le)):
        return
    cursor_id = le.cursorid
    if cursor_id is None:
        return
    cursor_patterns.setdefault(cursor_id, pattern)


class QuerySection(BaseSection):
    """QuerySection class."""

    name = "queries"

    def __init__(self, mloginfo):
        BaseSection.__init__(self, mloginfo)

        # add --queries flag to argparser
        helptext = 'outputs statistics about query patterns'
        self.mloginfo.argparser_sectiongroup.add_argument('--queries',
                                                          action='store_true',
                                                          help=helptext)
        self.mloginfo.argparser_sectiongroup.add_argument('--sort',
                                                          action='store',
                                                          default='sum',
                                                          choices=['namespace',
                                                                   'pattern',
                                                                   'count',
                                                                   'min',
                                                                   'max',
                                                                   'mean',
                                                                   '95%',
                                                                   'sum'])
        helptext = 'Number of decimal places for rounding of calculated stats'
        self.mloginfo.argparser_sectiongroup.add_argument('--rounding',
                                                          action='store',
                                                          type=int,
                                                          default=1,
                                                          choices=range(0, 5),
                                                          help=helptext)

    @property
    def active(self):
        """Return boolean if this section is active."""
        return self.mloginfo.args['queries']

    def run(self):
        """Run this section and print out information."""
        grouping = Grouping(group_by=lambda x: (x.namespace, x.operation,
                                                x.pattern, x.allowDiskUse))
        # cursor id -> query shape of the command that opened the cursor.
        # The log is read in order, so a find is recorded before its getMores.
        cursor_patterns = {}
        logfile = self.mloginfo.logfile
        rounding = self.mloginfo.args['rounding']

        if logfile.start and logfile.end:
            progress_start = self.mloginfo._datetime_to_epoch(logfile.start)
            progress_total = (self.mloginfo._datetime_to_epoch(logfile.end) -
                              progress_start)
        else:
            self.mloginfo.progress_bar_enabled = False

        for i, le in enumerate(logfile):
            le._debug = self.mloginfo.args['debug']

            # update progress bar every 1000 lines
            if self.mloginfo.progress_bar_enabled and (i % 1000 == 0):
                if le.datetime:
                    progress_curr = self.mloginfo._datetime_to_epoch(le
                                                                     .datetime)
                    if progress_total:
                        (self.mloginfo
                         .update_progress(float(progress_curr -
                                                progress_start) /
                                          progress_total))

            if _query_event(le):
                pattern = _pattern_for(le, cursor_patterns)
                _remember_cursor(le, pattern, cursor_patterns)
                lt = LogTuple(namespace=le.namespace,
                              operation=_operation_name(le),
                              pattern=pattern, duration=le.duration,
                              allowDiskUse=le.allowDiskUse)
                grouping.add(lt)

        grouping.sort_by_size()

        # clear progress bar again
        if self.mloginfo.progress_bar_enabled:
            self.mloginfo.update_progress(1.0)

        # no queries in the log file
        if len(grouping) < 1:
            print('no queries found.')
            return

        titles = ['namespace', 'operation', 'pattern', 'count', 'min (ms)',
                  'max (ms)', '95%-ile (ms)', 'sum (ms)', 'mean (ms)',
                  'allowDiskUse']
        table_rows = []

        for g in grouping:
            # calculate statistics for this group
            namespace, op, pattern, allowDiskUse = g

            group_events = [le.duration for le in grouping[g]
                            if le.duration is not None]
            group_events_all = [le.duration for le in grouping[g]]

            stats = OrderedDict()
            stats['namespace'] = namespace
            stats['operation'] = op
            stats['pattern'] = pattern
            stats['count'] = len(group_events_all)
            stats['min'] = min(group_events) if group_events else 0
            stats['max'] = max(group_events) if group_events else 0
            if np:
                stats['95%'] = (round(np.percentile(group_events, 95), rounding)
                                if group_events else 0)
            else:
                stats['95%'] = 'n/a'
            stats['sum'] = sum(group_events) if group_events else 0
            stats['mean'] = (round(stats['sum'] / stats['count'], rounding)
                             if group_events else 0)
            stats['allowDiskUse'] = allowDiskUse
            table_rows.append(stats)

        # sort order depending on field names
        reverse = True
        if self.mloginfo.args['sort'] in ['namespace', 'pattern']:
            reverse = False

        table_rows = sorted(table_rows,
                            key=itemgetter(self.mloginfo.args['sort']),
                            reverse=reverse)
        print_table(table_rows, titles, uppercase_headers=False)
        print('')
