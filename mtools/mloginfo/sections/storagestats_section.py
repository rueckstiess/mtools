from collections import namedtuple
from operator import itemgetter

from .base_section import BaseSection
from mtools.util import OrderedDict
from mtools.util.grouping import Grouping
from mtools.util.print_table import print_table

LogTuple = namedtuple('LogTuple', ['namespace', 'operation', 'bytesRead',
                      'bytesWritten', 'timeReadingMicros', 'timeWritingMicros'])


def op_or_cmd(le):
    return le.operation if le.operation != 'command' else le.command


class StorageStatsSection(BaseSection):
    """StorageStatsSection class."""

    name = "Storage Statistics "

    def __init__(self, mloginfo):
        BaseSection.__init__(self, mloginfo)

        # add --storagestats flag to argparser
        helptext = 'outputs storage statistics for insert and update operations'
        self.mloginfo.argparser_sectiongroup.add_argument('--storagestats',
                                                          action='store_true',
                                                          help=helptext)

    @property
    def active(self):
        """Return boolean if this section is active."""
        return self.mloginfo.args['storagestats']

    def run(self):
        """Run this section and print out information."""
        grouping = Grouping(group_by=lambda x: (x.namespace, x.operation,
                                                x.bytesRead, x.bytesWritten,
                                                x.timeReadingMicros,
                                                x.timeWritingMicros))
        logfile = self.mloginfo.logfile

        if logfile.start and logfile.end:
            progress_start = self.mloginfo._datetime_to_epoch(logfile.start)
            progress_total = (self.mloginfo._datetime_to_epoch(logfile.end) -
                              progress_start)
        else:
            self.mloginfo.progress_bar_enabled = False

        for i, le in enumerate(logfile):
            # update progress bar every 1000 lines
            if self.mloginfo.progress_bar_enabled and (i % 1000 == 0):
                if le.datetime:
                    progress_curr = self.mloginfo._datetime_to_epoch(le.datetime)
                    if progress_total:
                        (self.mloginfo.update_progress(
                            float(progress_curr - progress_start) / progress_total))

            if (le.operation in ['update'] or le.command in ['insert']):
                lt = LogTuple(namespace=le.namespace, operation=op_or_cmd(le),
                              bytesRead=le.bytesRead, bytesWritten=le.bytesWritten,
                              timeReadingMicros=le.timeReadingMicros,
                              timeWritingMicros=le.timeWritingMicros)
                grouping.add(lt)

        grouping.sort_by_size()

        # clear progress bar again
        if self.mloginfo.progress_bar_enabled:
            self.mloginfo.update_progress(1.0)

        # no queries in the log file
        if not len(grouping):
            print('no statistics found.')
            return

        titles = ['namespace', 'operation', 'bytesRead', 'bytesWritten',
                  'timeReadingMicros', 'timeWritingMicros']
        table_rows = []

        for g in grouping:
            # calculate statistics for this group
            namespace, op, bytesRead, bytesWritten, timeReadingMicros, timeWritingMicros = g

            stats = OrderedDict()
            stats['namespace'] = namespace
            stats['operation'] = op
            stats['bytesRead'] = bytesRead
            stats['bytesWritten'] = bytesWritten
            stats['timeReadingMicros'] = timeReadingMicros
            stats['timeWritingMicros'] = timeWritingMicros

            table_rows.append(stats)

        print_table(table_rows, titles, uppercase_headers=False)
        print('')
