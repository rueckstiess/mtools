#!/usr/bin/python

import argparse, re
from mtools.mtoolbox.logline import LogLine
from filters import *
import sys


class MongoLogFilter(object):
    def __init__(self):
        self.filters = [] 

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

    def _outputLine(self, line, length=None):
        if length:
            if len(line) > length:
                line = line[:length/2-2] + '...' + line[-length/2:]
        print line

    def parse(self):
        """ parses the logfile and asks each filter if it accepts the line.
            it will only be printed if all filters accept the line.
        """

        # create parser object
        parser = argparse.ArgumentParser(description='mongod/mongos log file parser. Use parameters to enable filters. A line only gets printed if it passes all enabled filters.')
        
        # only create default argument if not using stdin
        if sys.stdin.isatty():
            parser.add_argument('logfile', action='store', help='logfile to parse.')
        
        parser.add_argument('--verbose', action='store_true', help='outputs information about the parser and arguments.')
        parser.add_argument('--shorten', action='store', type=int, default=False, nargs='?', metavar='LENGTH', help='shortens long lines by cutting characters out of the middle until the length is <= LENGTH (default 200)')

        # add arguments from filter classes
        for f in self.filters:
            for fa in f.filterArgs:
                parser.add_argument(fa[0], **fa[1])

        self.args = vars(parser.parse_args())
        self.args = dict((k, self._arrayToString(self.args[k])) for k in self.args)
        
        # if self.args['verbose']:
        #     print self.args

        # create filter objects from classes and pass args
        self.filters = [f(self.args) for f in self.filters]

        # remove non-active filter objects
        self.filters = [f for f in self.filters if f.active]

        # open logfile
        if sys.stdin.isatty():
            logfile = open(self.args['logfile'], 'r')
        else:
            logfile = sys.stdin

        if self.args['shorten'] != False:
            if self.args['shorten'] == None:
                self.args['shorten'] = 200        

        if self.args['verbose']:
            print "mlogfilter> command line arguments"
            for a in self.args:
                print "mlogfilter> %8s: %s" % (a, self.args[a])

        # go through each line and ask each filter if it accepts
        for line in logfile:
            logline = LogLine(line)

            # only print line if all filters agree
            if all([f.accept(logline) for f in self.filters]):
                self._outputLine(logline.line_str, self.args['shorten'])

            # if at least one filter refuses to accept remaining lines, stop
            if any([f.skipRemaining() for f in self.filters]):
                # if called from shell, break
                if sys.stdin.isatty():
                    break


if __name__ == '__main__':

    # create MongoLogParser instance
    mlogfilter = MongoLogFilter()

    # add filters
    mlogfilter.addFilter(SlowFilter)
    mlogfilter.addFilter(WordFilter)
    mlogfilter.addFilter(TableScanFilter)
    mlogfilter.addFilter(DateTimeFilter)
    
    # start parsing
    mlogfilter.parse()









    
