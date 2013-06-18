#!/usr/bin/python

from mtools.util.log2code import Log2CodeConverter
from mtools.util.logline import LogLine
from mtools.util.cmdlinetool import LogFileTool

import argparse
import sys
from collections import defaultdict


class MLogDistinctTool(LogFileTool):

    log2code = Log2CodeConverter()

    def __init__(self):
        """ Constructor: add description to argparser. """
        LogFileTool.__init__(self, multiple_logfiles=False, stdin_allowed=True)
        
        self.argparser.description = 'Groups all log messages in the logfile together \
            and only displays a distinct set of messages with count'

        self.argparser.add_argument('--verbose', action='store_true', default=False, 
            help="outputs lines that couldn't be matched.")

    
    def run(self):
        """ go over each line in the logfile, run through log2code matcher 
            and group by matched pattern.
        """
        LogFileTool.run(self)

        codelines = defaultdict(lambda: 0)
        non_matches = 0

        for line in self.args['logfile']:
            cl = self.log2code(line)
            if cl:
                codelines[cl.pattern] += 1
            else:
                ll = LogLine(line)
                if ll.operation:
                    # skip operations (command, insert, update, delete, query, getmore)
                    continue
                if not ll.thread:
                    # skip the lines that don't have a thread name (usually map/reduce or assertions)
                    continue
                if len(ll.split_tokens) - ll._thread_offset <= 1:
                    # skip empty log messages (after thread name)
                    continue

                # everything else is a real non-match
                non_matches += 1
                if self.args['verbose']:
                    print "couldn't match:", line,

        if self.args['verbose']: 
            print

        for cl in sorted(codelines, key=lambda x: codelines[x], reverse=True):
            print "%8i"%codelines[cl], "  ", " ... ".join(cl)

        print
        if non_matches > 0:
            print "couldn't match %i lines"%non_matches
            if not self.args['verbose']:
                print "to show non-matched lines, run with --verbose."


if __name__ == '__main__':
    tool = MLogDistinctTool()
    tool.run()
