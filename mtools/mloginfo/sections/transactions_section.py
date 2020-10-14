import re
from collections import namedtuple
from operator import itemgetter
from mtools.util import OrderedDict
from mtools.util.grouping import Grouping
from mtools.util.print_table import print_table
from .base_section import BaseSection

LogTuple = namedtuple('LogTuple', ['datetime', 'txnNumber', 'autocommit', 'readConcern',
                                   'timeActiveMicros', 'timeInactiveMicros', 'duration'])


def op_or_cmd(le):
    return le.operation if le.operation != 'command' else le.command


class TransactionSection(BaseSection):
    """TransactionSection class."""

    name = "transactions"

    def __init__(self, mloginfo):
        BaseSection.__init__(self, mloginfo)

        # add --transactions flag to argparser
        helptext = 'outputs statistics about transactions'
        self.mloginfo.argparser_sectiongroup.add_argument('--transactions',
                                                          action='store_true',
                                                          help=helptext)

        # add --tsort flag to argparser for transaction sort
        self.mloginfo.argparser_sectiongroup.add_argument('--tsort',
                                                          action='store',

                                                          choices=['duration'])

    @property
    def active(self):
        """Return boolean if this section is active."""
        return self.mloginfo.args['transactions']

    def run(self):

        """Run this section and print out information."""
        grouping = Grouping(group_by=lambda x: (x.datetime, x.txnNumber,
                                                x.autocommit, x.readConcern,
                                                x.timeActiveMicros,
                                                x.timeInactiveMicros,
                                                x.duration))

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

            if re.search('transaction', le.line_str):
                lt = LogTuple(le.datetime, le.txnNumber, le.autocommit, le.readConcern,
                              le.timeActiveMicros, le.timeInactiveMicros, le.duration)

                grouping.add(lt)

        grouping.sort_by_size()

        # clear progress bar again
        if self.mloginfo.progress_bar_enabled:
            self.mloginfo.update_progress(1.0)

        # no queries in the log file
        if not len(grouping):
            print('no transactions found.')
            return

        titles = ['datetime', 'txnNumber', 'autocommit', 'readConcern',
                  'timeActiveMicros', 'timeInactiveMicros', 'duration']

        table_rows = []
        # using only important key-values
        # can be used in future
        for g in grouping:
            # calculate statistics for this group
            (datetime, txnNumber, autocommit, readConcern, timeActiveMicros,
             timeInactiveMicros, duration) = g

            stats = OrderedDict()
            stats['datetime'] = str(datetime)
            stats['txnNumber'] = txnNumber
            stats['autocommit'] = autocommit
            stats['readConcern'] = readConcern
            stats['timeActiveMicros'] = timeActiveMicros
            stats['timeInactiveMicros'] = timeInactiveMicros
            stats['duration'] = duration
            table_rows.append(stats)

        if self.mloginfo.args['tsort'] == 'duration':
            table_rows = sorted(table_rows,
                                key=itemgetter(self.mloginfo.args['tsort']),
                                reverse=True)

        print_table(table_rows, titles, uppercase_headers=True)

        print('')
