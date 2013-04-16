#!/usr/bin/python

from mtools.mtoolbox.log2code import Log2CodeConverter
from mtools.mtoolbox.logline import LogLine
import argparse
import sys
from collections import defaultdict

log2code = Log2CodeConverter()

if __name__ == '__main__':
    codelines = defaultdict(lambda: 0)
    non_matches = 0

    # create parser object
    parser = argparse.ArgumentParser(description='Groups all log messages in the logfile together and only displays a distinct set of messages with count (BETA)')
    parser.add_argument('--verbose', action='store_true', default=False, help="outputs lines that couldn't be matched")

    # only create default argument if not using stdin
    if sys.stdin.isatty():
        parser.add_argument('logfile', action='store', help='logfile to convert')
    
    args = vars(parser.parse_args())

    # open logfile
    if sys.stdin.isatty():
        logfile = open(args['logfile'], 'r')
    else:
        logfile = sys.stdin

    for line in logfile:
        cl = log2code(line)
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
            if args['verbose']:
                print "couldn't match:", line,

    if args['verbose']: 
        print

    for cl in sorted(codelines, key=lambda x: codelines[x], reverse=True):
        print "%8i"%codelines[cl], "  ", " ... ".join(cl)

    print
    print "couldn't match %i lines"%non_matches
    if not args['verbose']:
        print "to show those lines, run with --verbose."
