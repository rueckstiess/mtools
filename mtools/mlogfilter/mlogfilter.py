#!/usr/bin/python

import argparse, re
import sys

from mtools.util.logline import LogLine
from mtools.util.cmdlinetool import LogFileTool
from mtools.mlogfilter.filters import *



class MLogFilterTool(LogFileTool):

    def __init__(self):
        LogFileTool.__init__(self, multiple_logfiles=False, stdin_allowed=True)
        
        self.filters = [] 

        self.argparser.description = 'mongod/mongos log file parser. Use parameters to enable filters. A line only gets printed if it passes all enabled filters.'
        self.argparser.add_argument('--verbose', action='store_true', help='outputs information about the parser and arguments.')
        self.argparser.add_argument('--shorten', action='store', type=int, default=False, nargs='?', metavar='LENGTH', help='shortens long lines by cutting characters out of the middle until the length is <= LENGTH (default 200)')
        self.argparser.add_argument('--exclude', action='store_true', default=False, help='if set, excludes the matching lines rather than includes them.')
        self.argparser.add_argument('--human', action='store_true', help='outputs information in human readable form')



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

    def _outputLine(self, line, length=None, human = False):
        if length:
            if len(line) > length:
                line = line[:length/2-2] + '...' + line[-length/2:]
        if human:
            line = self._changeMs(line)
        print line


    def _msToString(self, ms):
        """ changes milliseconds to hr:min:sec.ms format """ 
        hr, ms = divmod(ms, 3600000)
        mins, ms = divmod(ms, 60000)
        seconds = float(ms)/1000
        return "%i:%02i:%06.3f"%(hr,mins,seconds)

    def _changeMs(self, line):
        """ changes the ms part in the string if needed """ 
        splitted = re.split('\s', line)
        if (splitted[-1])[-2:] == 'ms':
            ms = int(re.split('ms', splitted[-1])[0])
            new_string = " ".join(splitted[:-1])
            new_string = new_string + ' ' +  self._msToString(ms)
        return new_string



    def run(self):

        """ parses the logfile and asks each filter if it accepts the line.
            it will only be printed if all filters accept the line.
        """

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


        if self.args['shorten'] != False:
            if self.args['shorten'] == None:
                self.args['shorten'] = 200        

        if self.args['verbose']:
            print "mlogfilter> command line arguments"
            for a in self.args:
                print "mlogfilter> %8s: %s" % (a, self.args[a])

        # go through each line and ask each filter if it accepts
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

    # add filters
    tool.addFilter(LogLineFilter)
    tool.addFilter(SlowFilter)
    tool.addFilter(FastFilter)
    tool.addFilter(WordFilter)
    tool.addFilter(TableScanFilter)
    tool.addFilter(DateTimeFilter)
    
    tool.run()









    
