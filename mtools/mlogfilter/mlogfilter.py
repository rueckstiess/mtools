#!/usr/bin/env python3

import inspect
import re
import sys
from datetime import MAXYEAR, MINYEAR, datetime, timedelta

from dateutil.tz import tzutc

import mtools.mlogfilter.filters as filters
from mtools.util.cmdlinetool import LogFileTool


class MLogFilterTool(LogFileTool):

    def __init__(self):
        LogFileTool.__init__(self, multiple_logfiles=True, stdin_allowed=True)

        # add all filter classes from the filters module
        self.filters = [c[1] for c in inspect.getmembers(filters,
                                                         inspect.isclass)]

        self.argparser.description = ('mongod/mongos log file parser. Use '
                                      'parameters to enable filters. A line '
                                      'only gets printed if it passes all '
                                      'enabled filters. If several log files '
                                      'are provided, their lines are merged '
                                      'by timestamp.')
        self.argparser.add_argument('--verbose', action='store_true',
                                    help=('outputs information about the '
                                          'parser and arguments.'))
        self.argparser.add_argument('--shorten', action='store', type=int,
                                    default=False, nargs='?', metavar='LENGTH',
                                    help=('shortens long lines by cutting '
                                          'characters out of the middle until '
                                          'the length is <= LENGTH '
                                          '(default 200)'))
        self.argparser.add_argument('--exclude', action='store_true',
                                    default=False,
                                    help=('if set, excludes the matching '
                                          'lines rather than includes them.'))
        self.argparser.add_argument('--human', action='store_true',
                                    help=('outputs large numbers formatted '
                                          'with commas and print milliseconds '
                                          'as hr,min,sec,ms for easier '
                                          'readability.'))
        self.argparser.add_argument('--json', action='store_true',
                                    help=('outputs all matching lines in json '
                                          'format rather than the native '
                                          'log line.'))
        self.argparser.add_argument('--markers', action='store', nargs='*',
                                    default=['filename'],
                                    help=('use markers when merging several '
                                          'files to distinguish them. Choose '
                                          'from none, enum, alpha, filename '
                                          '(default), or provide list.'))
        self.argparser.add_argument('--timezone', action='store', nargs='*',
                                    default=[], type=int, metavar="N",
                                    help=("timezone adjustments: add N hours "
                                          "to corresponding log file, single "
                                          "value for global adjustment."))
        self.argparser.add_argument('--timestamp-format', action='store',
                                    default='none', choices=['none',
                                                             'ctime-pre2.4',
                                                             'ctime',
                                                             'iso8601-utc',
                                                             'iso8601-local'],
                                    help=("choose datetime format for "
                                          "log output"))

    def addFilter(self, filterclass):
        """Add a filter class to the parser."""
        if filterclass not in self.filters:
            self.filters.append(filterclass)

    def _arrayToString(self, arr):
        """If arr is of type list, join elements with space delimiter."""
        if isinstance(arr, list):
            return " ".join(arr)
        else:
            return arr

    def _outputLine(self, logevent, length=None, human=False):
        """
        Print the final line.

        Provides various options (length, human, datetime changes, ...).
        """
        # adapt timezone output if necessary
        if self.args['timestamp_format'] != 'none':
            logevent._reformat_timestamp(self.args['timestamp_format'],
                                         force=True)
        if any(self.args['timezone']):
            if self.args['timestamp_format'] == 'none':
                self.args['timestamp_format'] = logevent.datetime_format
            logevent._reformat_timestamp(self.args['timestamp_format'],
                                         force=True)

        if self.args['json']:
            print(logevent.to_json())
            return
        line = logevent.line_str

        if length:
            if len(line) > length:
                line = (line[:int(length / 2 - 2)] + '...' +
                        line[int(-length / 2 + 1):])
        if human:
            line = self._changeMs(line)
            line = self._formatNumbers(line)

        print(line)

    def _msToString(self, ms):
        """Change milliseconds to hours min sec ms format."""
        hr, ms = divmod(ms, 3600000)
        mins, ms = divmod(ms, 60000)
        secs, mill = divmod(ms, 1000)
        return "%ihr %imin %isecs %ims" % (hr, mins, secs, mill)

    def _changeMs(self, line):
        """Change the ms part in the string if needed."""
        # use the position of the last space instead
        try:
            last_space_pos = line.rindex(' ')
        except ValueError:
            return line
        else:
            end_str = line[last_space_pos:]
            new_string = line
            if end_str[-2:] == 'ms' and int(end_str[:-2]) >= 1000:
                # isolate the number of milliseconds
                ms = int(end_str[:-2])
                # create the new string with the beginning part of the
                # log with the new ms part added in
                new_string = (line[:last_space_pos] +
                              ' (' + self._msToString(ms) + ')' +
                              line[last_space_pos:])
            return new_string

    def _formatNumbers(self, line):
        """
        Format the numbers so that there are commas inserted.

        For example: 1200300 becomes 1,200,300.
        """
        # below thousands separator syntax only works for
        # python 2.7, skip for 2.6
        if sys.version_info < (2, 7):
            return line

        last_index = 0
        try:
            # find the index of the last } character
            last_index = (line.rindex('}') + 1)
            end = line[last_index:]
        except ValueError:
            return line
        else:
            # split the string on numbers to isolate them
            splitted = re.split(r"(\d+)", end)
            for index, val in enumerate(splitted):
                converted = 0
                try:
                    converted = int(val)
                # if it's not an int pass and don't change the string
                except ValueError:
                    pass
                else:
                    if converted > 1000:
                        splitted[index] = format(converted, ",d")
            return line[:last_index] + ("").join(splitted)

    def _datetime_key_for_merge(self, logevent):
        """Helper method for ordering log lines correctly during merge."""
        if not logevent:
            # if logfile end is reached, return max datetime to never
            # pick this line
            return datetime(MAXYEAR, 12, 31, 23, 59, 59, 999999, tzutc())

        # if no datetime present (line doesn't have one) return mindate
        # to pick this line immediately
        return logevent.datetime or datetime(MINYEAR, 1, 1, 0, 0, 0, 0,
                                             tzutc())

    def _merge_logfiles(self):
        """Helper method to merge several files together by datetime."""
        # open files, read first lines, extract first dates
        lines = [next(iter(logfile), None) for logfile in self.args['logfile']]

        # adjust lines by timezone
        for i in range(len(lines)):
            if lines[i] and lines[i].datetime:
                lines[i]._datetime = (lines[i].datetime +
                                      timedelta(hours=self.args['timezone']
                                                [i]))

        while any(lines):
            min_line = min(lines, key=self._datetime_key_for_merge)
            min_idx = lines.index(min_line)

            if self.args['markers'][min_idx]:
                min_line.merge_marker_str = self.args['markers'][min_idx]

            yield min_line

            # update lines array with a new line from the min_idx'th logfile
            lines[min_idx] = next(iter(self.args['logfile'][min_idx]), None)
            if lines[min_idx] and lines[min_idx].datetime:
                lines[min_idx]._datetime = (
                    lines[min_idx].datetime +
                    timedelta(hours=self.args['timezone'][min_idx]))

    def logfile_generator(self):
        """Yield each line of the file, or the next line if several files."""
        if not self.args['exclude']:
            # ask all filters for a start_limit and fast-forward to the maximum
            start_limits = [f.start_limit for f in self.filters
                            if hasattr(f, 'start_limit')]

            if start_limits:
                for logfile in self.args['logfile']:
                    logfile.fast_forward(max(start_limits))

        if len(self.args['logfile']) > 1:
            # merge log files by time
            for logevent in self._merge_logfiles():
                try:
                    yield logevent
                except StopIteration:
                    return

        else:
            # only one file
            for logevent in self.args['logfile'][0]:
                if self.args['timezone'][0] != 0 and logevent.datetime:
                    logevent._datetime = (logevent.datetime +
                                          timedelta(hours=self
                                                    .args['timezone'][0]))
                try:
                    yield logevent
                except StopIteration:
                    return

    def run(self, arguments=None):
        """
        Parse the logfile.

        Ask each filter if it accepts the line. It will only be printed if all
        filters accept the line.
        """
        # add arguments from filter classes before calling superclass run
        for f in self.filters:
            for fa in f.filterArgs:
                self.argparser.add_argument(fa[0], **fa[1])
        # now parse arguments and post-process
        LogFileTool.run(self, arguments)

        self.args = dict((k, self.args[k]
                          if k in ['logfile', 'markers', 'timezone']
                          else self._arrayToString(self.args[k]))
                         for k in self.args)
        # make sure logfile is always a list, even if 1 is provided
        # through sys.stdin
        if not isinstance(self.args['logfile'], list):
            self.args['logfile'] = [self.args['logfile']]

        # require at least 1 log file (either through stdin or as parameter)
        if len(self.args['logfile']) == 0:
            raise SystemExit('Error: Need at least 1 log file, either as '
                             'command line parameter or through stdin.')

        # handle timezone parameter
        if len(self.args['timezone']) == 1:
            self.args['timezone'] = (self.args['timezone'] *
                                     len(self.args['logfile']))
        elif len(self.args['timezone']) == len(self.args['logfile']):
            pass
        elif len(self.args['timezone']) == 0:
            self.args['timezone'] = [0] * len(self.args['logfile'])
        else:
            raise SystemExit('Error: Invalid number of timezone parameters. '
                             'Use either one parameter (for global '
                             'adjustment) or the number of log files '
                             '(for individual adjustments).')

        # create filter objects from classes and pass args
        self.filters = [f(self) for f in self.filters]

        # remove non-active filter objects
        self.filters = [f for f in self.filters if f.active]

        # call setup for each active filter
        for f in self.filters:
            f.setup()

        if self.args['shorten'] is not False:
            if self.args['shorten'] is None:
                self.args['shorten'] = 200

        if self.args['verbose']:
            print("command line arguments")
            for a in self.args:
                print("    %s: %s" % (a, self.args[a]))
            print("\nactive filters: " +
                  ", ".join([f.__class__.__name__ for f in self.filters]))
            print('\n====================')

        # handle markers parameter
        if len(self.args['markers']) == 1:
            marker = self.args['markers'][0]
            if marker == 'enum':
                self.args['markers'] = ['{%i}' % (i + 1)
                                        for i in range(len(self
                                                           .args['logfile']))]
            elif marker == 'alpha':
                self.args['markers'] = ['{%s}' % chr(97 + i)
                                        for i in range(len(self
                                                           .args['logfile']))]
            elif marker == 'none':
                self.args['markers'] = [None for _ in self.args['logfile']]
            elif marker == 'filename':
                self.args['markers'] = ['{%s}' % logfile.name
                                        for logfile in self.args['logfile']]
        elif len(self.args['markers']) == len(self.args['logfile']):
            pass
        else:
            raise SystemExit('Error: Number of markers not the same as '
                             'number of files.')

        # with --human, change to ctime format if not specified otherwise
        if self.args['timestamp_format'] == 'none' and self.args['human']:
            self.args['timestamp_format'] = 'ctime'

        # go through each line and ask each filter if it accepts
        if 'logfile' not in self.args or not self.args['logfile']:
            raise SystemExit('no logfile found.')

        for logevent in self.logfile_generator():
            if self.args['exclude']:
                # print line if any filter disagrees
                if any([not f.accept(logevent) for f in self.filters]):
                    self._outputLine(logevent, self.args['shorten'],
                                     self.args['human'])

            else:
                # only print line if all filters agree
                if all([f.accept(logevent) for f in self.filters]):
                    self._outputLine(logevent, self.args['shorten'],
                                     self.args['human'])

                # if at least one filter refuses to accept any
                # remaining lines, stop
                if any([f.skipRemaining() for f in self.filters]):
                    # if input is not stdin
                    if sys.stdin.isatty():
                        break


def main():
    tool = MLogFilterTool()
    tool.run()


if __name__ == '__main__':
    sys.exit(main())
