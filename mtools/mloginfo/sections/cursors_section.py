from collections import namedtuple
from mtools.util import OrderedDict
from mtools.util.grouping import Grouping
from mtools.util.print_table import print_table
from operator import itemgetter
from .base_section import BaseSection

LogTuple = namedtuple('LogTuple', ['datetime', 'cursorid', 'reapedtime'])


def op_or_cmd(le):
    return le.operation if le.operation != 'command' else le.command


class CursorSection(BaseSection):
    """CursorSection class."""

    name = 'cursors'

    def __init__(self, mloginfo):
        BaseSection.__init__(self, mloginfo)
        helptext = 'outputs statistics about cursors'
        self.mloginfo.argparser_sectiongroup.add_argument('--cursors',
                                                          action='store_true',
                                                          help=helptext)

    @property
    def active(self):
        """Return boolean if this section is active."""
        return self.mloginfo.args['cursors']

    def run(self):
        """Run this section and print out information."""
        grouping = Grouping(group_by=lambda x: (x.datetime, x.cursorid, x.reapedtime))
        logfile = self.mloginfo.logfile

        if logfile.start and logfile.end:
            progress_start = self.mloginfo._datetime_to_epoch(logfile.start)
            progress_total = (self.mloginfo._datetime_to_epoch(logfile.end) - progress_start)
        else:
            self.mloginfo.progress_bar_enabled = False

        for i, le in enumerate(logfile):
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

            if 'Cursor id' in le.line_str:
                lt = LogTuple(le.datetime, le.cursor, le._reapedtime)
                grouping.add(lt)

        grouping.sort_by_size()

        # clear progress bar again
        if self.mloginfo.progress_bar_enabled:
            self.mloginfo.update_progress(1.0)

        # no cursor information in the log file
        if not len(grouping):
            print('no cursor information found.')
            return

        titles = ['datetime', 'cursorid', 'reapedtime']

        table_rows = []
        # using only important key-values
        for g in grouping:
            # calculate statistics for this group
            datetime, cursorid, reapedtime = g
            stats = OrderedDict()
            stats['datetime'] = str(datetime)
            stats['cursorid'] = str(cursorid)
            stats['reapedtime'] = str(reapedtime)
            table_rows.append(stats)

        print_table(table_rows, titles, uppercase_headers=True)

        print('')
