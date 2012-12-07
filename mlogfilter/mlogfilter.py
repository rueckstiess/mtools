#!/usr/bin/python

import argparse, re
from filters import WordFilter, SlowFilter, DateTimeFilter
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

    def parse(self):
        """ parses the logfile and asks each filter if it accepts the line.
            it will only be printed if all filters accept the line.
        """

        # create parser object
        parser = argparse.ArgumentParser(description='mongod/mongos log file parser.')
        
        # only create default argument if not using stdin
        if sys.stdin.isatty():
            parser.add_argument('logfile', action='store', nargs='?', help='logfile to parse.')
        
        parser.add_argument('--verbose', action='store_true', help='outputs information about the parser and arguments.')

        # add arguments from filter classes
        for f in self.filters:
            for fa in f.filterArgs:
                parser.add_argument(fa[0], **fa[1])

        args = vars(parser.parse_args())
        args = dict((k, self._arrayToString(args[k])) for k in args)
        
        # create filter objects from classes and pass args
        self.filters = [f(args) for f in self.filters]

        # remove non-active filter objects
        self.filters = [f for f in self.filters if f.active]

        # open logfile
        if sys.stdin.isatty():
            logfile = open(args['logfile'], 'r')
        else:
            logfile = sys.stdin


        if args['verbose']:
            print "mlogfilter> command line arguments"
            for a in args:
                print "mlogfilter> %8s: %s" % (a, args[a])

        # go through each line and ask each filter if it accepts
        for line in logfile:

            # special case: if line starts with ***, always print (server restart)
            if line.startswith('***'):
                print line,
                continue

            # only print line if all filters agree
            if all([f.accept(line) for f in self.filters]):
                print line,

            # if at least one filter refuses to print remaining lines, stop
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
    mlogfilter.addFilter(DateTimeFilter)
    
    # start parsing
    mlogfilter.parse()









    
