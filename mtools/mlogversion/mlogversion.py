#!/usr/bin/python

import sys
import re
import argparse
from mtools.util.log2code import Log2CodeConverter
from mtools.util.logline import LogLine

if __name__ == '__main__':
    # create parser object
    parser = argparse.ArgumentParser(description='mongod/mongos log file version detector (BETA).\n Parses a log file and matches each line to its original source code version. Each line that limits the remaining possible set of versions is printed. If a mongos/d restart is detected, the definitive version is printed instead.')
    log2code = Log2CodeConverter()

    possible_versions = set(Log2CodeConverter.all_versions)

    # only create default argument if not using stdin
    if sys.stdin.isatty():
        parser.add_argument('logfile', action='store', help='logfile to detect version.')

    args = vars(parser.parse_args())

    # open logfile
    if sys.stdin.isatty():
        logfile = open(args['logfile'], 'r')
    else:
        logfile = sys.stdin

    re_versiond = re.compile(r'db version v(\d\.\d\.\d), pdfile version')
    re_versions = re.compile(r'MongoS version (\d\.\d\.\d) starting:')

    re_brackets = re.compile(r'\[\w+\]')
    for i, line in enumerate(logfile): 
        match = re_brackets.search(line)
        if not match:
            continue

        start = match.end()

        # check for explicit version string
        match = re_versiond.search(line[start:]) or re_versions.search(line[start:])

        if match:
            version = match.group(1)
            print "%32s %s" % ("restart detected in log line %i:"%(i+1), line.rstrip())
            print "%32s %s" % ("previous possible versions:", ", ".join([pv[1:] for pv in sorted(possible_versions)]))
            print "%32s %s" % ("version after restart is:", version)
            print
            possible_versions = set(["r"+version])
            
        if len(possible_versions) == 1:
            # from here on, version is known, skip to next section
            continue

        ll = LogLine(line)
        if ll.operation != None:
            # if log line is a known command operation (query, update, command, ...) skip
            continue

        lcl = log2code(line[start:])
        if lcl:
            old_len = len(possible_versions)
            possible_versions = possible_versions & set(lcl.versions)
            if len(possible_versions) != old_len:
                print "%32s %s" % ("log line %i:"%(i+1), line.rstrip())
                print "%32s %s" % ("matched pattern:", " ... ".join(lcl.pattern))
                print "%32s %s" % ("only present in:", ", ".join(sorted(lcl.versions)))
                print "%32s %s" % ("possible versions now:", ", ".join(sorted(possible_versions)))
                print

        if len(possible_versions) == 0:
            print "empty version set. exiting."
            raise SystemExit

    if len(possible_versions) > 1:
        print "possible versions at end of file:", ", ".join([pv[1:] for pv in sorted(possible_versions)])
    else:
        print "version at end of file: ", possible_versions.pop()[1:]
