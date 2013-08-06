#!/usr/bin/python

import argparse, re
import sys
import inspect

from mtools.util.logline import LogLine
from mtools.util.cmdlinetool import LogFileTool
from mtools.mlogfilter.filters import *

import mtools.mlogfilter.filters as filters

class MLogFilterTool(LogFileTool):

    def __init__(self):
        LogFileTool.__init__(self, multiple_logfiles=False, stdin_allowed=True)
        
        # add all filter classes from the filters module
        self.filters = [c[1] for c in inspect.getmembers(filters, inspect.isclass)]

        self.argparser.description = 'mongod/mongos log file parser. Use parameters to enable filters. A line only gets printed if it passes all enabled filters.'
        self.argparser.add_argument('--verbose', action='store_true', help='outputs information about the parser and arguments.')
        self.argparser.add_argument('--shorten', action='store', type=int, default=False, nargs='?', metavar='LENGTH', help='shortens long lines by cutting characters out of the middle until the length is <= LENGTH (default 200)')
        self.argparser.add_argument('--exclude', action='store_true', default=False, help='if set, excludes the matching lines rather than includes them.')
        self.argparser.add_argument('--human', action='store_true', help='outputs numbers formatted with commas and milliseconds as hr,min,sec,ms for easier readability ')


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


    def run(self, arguments=None):
        """ parses the logfile and asks each filter if it accepts the line.
            it will only be printed if all filters accept the line.
        """

        # add arguments from filter classes before calling superclass run
        for f in self.filters:
            for fa in f.filterArgs:
                self.argparser.add_argument(fa[0], **fa[1])

        # now parse arguments and post-process
        LogFileTool.run(self)
        self.args = dict((k, self._arrayToString(self.args[k])) for k in self.args)

        # create filter objects from classes and pass args
        self.filters = [f(self.args) for f in self.filters]

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

        # go through each line and ask each filter if it accepts
        if not 'logfile' in self.args or not self.args['logfile']:
            exit()


        for line in self.args['logfile']:
            logline = LogLine(line)
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
                    # if input is not stdin
                    if sys.stdin.isatty():
                        break


if __name__ == '__main__':

    tool = MLogFilterTool()    
    tool.run()
