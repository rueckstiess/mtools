#!/usr/bin/python

import argparse, re
import sys
import inspect

from datetime import datetime, timedelta, MINYEAR, MAXYEAR

from mtools.util.logline import LogLine
from mtools.util.cmdlinetool import LogFileTool
from mtools.mlogfilter.filters import *

import mtools.mlogfilter.filters as filters

class MLogFilterTool(LogFileTool):

    def __init__(self):
        LogFileTool.__init__(self, multiple_logfiles=True, stdin_allowed=True)
        
        # add all filter classes from the filters module
        self.filters = [c[1] for c in inspect.getmembers(filters, inspect.isclass)]

        self.argparser.description = 'mongod/mongos log file parser. Use parameters to enable filters. A line only gets printed if it passes all enabled filters.'
        self.argparser.add_argument('--verbose', action='store_true', help='outputs information about the parser and arguments.')
        self.argparser.add_argument('--shorten', action='store', type=int, default=False, nargs='?', metavar='LENGTH', help='shortens long lines by cutting characters out of the middle until the length is <= LENGTH (default 200)')
        self.argparser.add_argument('--exclude', action='store_true', default=False, help='if set, excludes the matching lines rather than includes them.')
        self.argparser.add_argument('--human', action='store_true', help='outputs numbers formatted with commas and milliseconds as hr,min,sec,ms for easier readability.')

        self.argparser.add_argument('--markers', action='store', nargs='*', default=['filename'], help='markers to distinguish original files. Choose from none, enum, alpha, filename (default), or provide list.')
        self.argparser.add_argument('--marker-pos', action='store', default=0, type=int, help="position of marker (default=0, front of line, other options are 'eol' or the position as int.")
        self.argparser.add_argument('--timezone', action='store', nargs='*', default=[], type=int, metavar="N", help="timezone adjustments: add N hours to corresponding log file, single value for global adjustment.")
        self.argparser.add_argument('--datetime-format', action='store', default='auto', type=int, metavar="DT", choices=['ctime-pre2.4', 'ctime', 'iso8601-utc', 'iso8601-local', 'auto'], help="timezone format output.")


    def addFilter(self, filterClass):
        """ adds a filter class to the parser. """
        if not filterClass in self.filters:
            self.filters.append(filterClass)

    
    def _arrayToString(self, arr):
        """ if arr is of type list, join elements with space delimiter. """
        if isinstance(arr, list):
            return " ".join(arr)
        else:
            return arr

    
    def _outputLine(self, line, length=None, human=False):
        if length:
            if len(line) > length:
                line = line[:length/2-2] + '...' + line[-length/2+1:]
        if human:
            line = self._changeMs(line)
            line = self._formatNumbers(line)
        print line


    def _msToString(self, ms):
        """ changes milliseconds to hours min sec ms format """ 
        hr, ms = divmod(ms, 3600000)
        mins, ms = divmod(ms, 60000)
        secs, mill = divmod(ms, 1000)
        return "%ihr %imin %isecs %ims"%(hr, mins, secs, mill) 


    def _changeMs(self, line):
        """ changes the ms part in the string if needed """ 
        # use the the position of the last space instead
        try:
            last_space_pos = line.rindex(' ')
        except ValueError, s:
            return line
        else:
            end_str = line[last_space_pos:]
            new_string = line
            if end_str[-2:] == 'ms' and int(end_str[:-2]) >= 1000:
                # isolate the number of milliseconds 
                ms = int(end_str[:-2])
                # create the new string with the beginning part of the log with the new ms part added in
                new_string = line[:last_space_pos] + ' (' +  self._msToString(ms) + ')' + line[last_space_pos:]
            return new_string

    def _formatNumbers(self, line):
        """ formats the numbers so that there are commas inserted, ie. 1200300 becomes 1,200,300 """
        last_index = 0
        try:
            # find the index of the last } character
            last_index = (line.rindex('}') + 1)
            end = line[last_index:]
        except ValueError, e:
            return line
        else:
            # split the string on numbers to isolate them
            splitted = re.split("(\d+)", end)
            for index, val in enumerate(splitted):
                converted = 0
                try:
                    converted = int(val)
                #if it's not an int pass and don't change the string
                except ValueError, e:
                    pass
                else:
                    if converted > 1000:
                        splitted[index] = format(converted, ",d")
            return line[:last_index] + ("").join(splitted)


    def _datetime_key_for_merge(self, logline):
        dt = logline.datetime

        if logline.line_str == '':
            # if logline is empty (i.e. end of this log file reached) return maxdate to never pick this line
            return datetime(MAXYEAR, 12, 31, 23, 59, 59)
        else:
            # if no datetime present (line doesn't have one) return mindate to pick this line immediately
            return dt or datetime(MINYEAR, 1, 1, 0, 0, 0)



    def _merge_logfiles(self):
        # open files, read first lines, extract first dates
        lines = [LogLine(f.readline()) for f in self.args['logfile']]
        
        # adjust lines by timezone
        for i in range(len(lines)):
            new_datetime = lines[i].datetime + timedelta(self.args['timezone'][i])
            # TODO REPLACE DATE WITH NEW DATE FOR ALL FORMATS
            # lines[i]._line_str = replace(lines[i].datetime.strftime('%a %b %d %H:%M:%S'), new_datetime.strftime('%a %b %d %H:%M:%S'))
            lines[i]._datetime = new_datetime

        while any([ll.line_str != '' for ll in lines]):
            min_line = min(lines, key=self._datetime_key_for_merge)
            min_index = lines.index(min_line)

            if self.args['markers'][min_index]:
                if self.args['marker_pos'] == 0:
                    min_line.line_str = self.args['markers'][min_index] + ' ' + min_line.line_str
                elif self.args['marker_pos'] == 'eol':
                    min_line.line_str = min_line.line_str + ' ' + self.args['markers'][min_index]
                else:
                    tokens = min_line.split_tokens()
                    outline = " ".join(tokens[:self.args['marker_pos']]) + ' ' + self.args['markers'][min_index] + ' ' + " ".join(tokens[self.args['marker_pos']:])

            yield min_line

            # update lines array with a new line from the min_index'th logfile
            lines[min_index] = LogLine(self.args['logfile'][min_index].readline())
            if lines[min_index].datetime:
                lines[min_index]._datetime = lines[min_index].datetime + timedelta(self.args['timezone'][i])


    def logfile_generator(self):
        if len(self.args['logfile']) > 1:
            # todo, merge
            for logline in self._merge_logfiles():
                yield logline
        else:
            # only one file
            for line in self.args['logfile'][0]:
                logline = LogLine(line)
                if logline.datetime:
                    logline._datetime = logline.datetime + timedelta(hours=self.args['timezone'][0])

                yield logline



    def run(self, arguments=None):
        """ parses the logfile and asks each filter if it accepts the line.
            it will only be printed if all filters accept the line.
        """

        # add arguments from filter classes before calling superclass run
        for f in self.filters:
            for fa in f.filterArgs:
                self.argparser.add_argument(fa[0], **fa[1])

        # now parse arguments and post-process
        LogFileTool.run(self, arguments)
        self.args = dict((k, self.args[k] if k in ['logfile', 'markers', 'timezone'] else self._arrayToString(self.args[k])) for k in self.args)

        # handle timezone parameter
        if len(self.args['timezone']) == 1:
            self.args['timezone'] = self.args['timezone'] * len(self.args['logfile'])
        elif len(self.args['timezone']) == len(self.args['logfile']):
            pass
        elif len(self.args['timezone']) == 0:
            self.args['timezone'] = [0] * len(self.args['logfile'])
        else:
            raise SystemExit('Error: Invalid number of timezone parameters. Use either one parameter (for global adjustment) or the number of log files (for individual adjustments).')

        # create filter objects from classes and pass args
        self.filters = [f(self) for f in self.filters]

        # remove non-active filter objects
        self.filters = [f for f in self.filters if f.active]

        # call setup for each active filter
        for f in self.filters:
            f.setup()

        if self.args['shorten'] != False:
            if self.args['shorten'] == None:
                self.args['shorten'] = 200        

        if self.args['verbose']:
            print "mlogfilter> command line arguments"
            for a in self.args:
                print "mlogfilter> %8s: %s" % (a, self.args[a])

        # handle markers parameter
        if len(self.args['markers']) == 1:
            marker = self.args['markers'][0]
            if marker == 'enum':
                self.args['markers'] = ['{%i}'%(i+1) for i in range(len(self.args['logfile']))]
            elif marker == 'alpha':
                self.args['markers'] = ['{%s}'%chr(97+i) for i in range(len(self.args['logfile']))]
            elif marker == 'none':
                self.args['markers'] = [None for _ in self.args['logfile']]
            elif marker == 'filename':
                self.args['markers'] = ['{%s}'%fn.name for fn in self.args['logfile']]
        elif len(self.args['markers']) == len(self.args['logfile']):
            pass
        else:
            raise SystemExit('Error: Number of markers not the same as number of files.')


        # go through each line and ask each filter if it accepts
        if not 'logfile' in self.args or not self.args['logfile']:
            raise SystemExit('no logfile found.')

        for logline in self.logfile_generator():
            if self.args['exclude']:
                # print line if any filter disagrees
                if any([not f.accept(logline) for f in self.filters]):
                    self._outputLine(logline.line_str, self.args['shorten'], self.args['human'])

            else:
                # only print line if all filters agree
                if all([f.accept(logline) for f in self.filters]):
                    self._outputLine(logline.line_str, self.args['shorten'], self.args['human'])

                # if at least one filter refuses to accept any remaining lines, stop
                if any([f.skipRemaining() for f in self.filters]):
                    print [f]
                    # if input is not stdin
                    if sys.stdin.isatty():
                        break


if __name__ == '__main__':

    tool = MLogFilterTool()    
    tool.run()
