#!/usr/bin/env python

from mtools.util.logfile import LogFile
from mtools.util.logevent import LogEvent
from mtools.util.cmdlinetool import BaseCmdLineTool, InputSourceAction

import sys
import inspect
import argparse
import mtools.mloginfo.sections as sections



class MLogInfoTool(BaseCmdLineTool):

    def __init__(self):
        """ Constructor: add description to argparser. """
        BaseCmdLineTool.__init__(self)

        # add all filter classes from the filters module
        self.sections = dict( [ (c[1].name, c[1](self)) for c in inspect.getmembers(sections, inspect.isclass) ] )

        # initialize arpparser
        self.argparser.description = 'Extracts general information from logfile and prints it to stdout.'
        self.argparser.add_argument('--verbose', action='store_true', help='show more verbose output (depends on info section)')
        
        # for backwards compatibility, if only a logfile is specified without a command, still print out the basic info
        # only add command subparsers if there are at least 2 additional arguments (command, logfile) or if --help is invoked
        if len(sys.argv) != 2 or sys.argv[1] in self.sections.keys() + ['--help', '--version']:
            # create command sub-parsers
            subparsers = self.argparser.add_subparsers(title='commands', dest='command')

            for section in self.sections.values():
                subparser = subparsers.add_parser(section.name, help=section.description, description=section.description)
                section._add_subparser_arguments(subparser)

        # add logfile action manually at the end
        self.argparser.add_argument('logfile', action='store', type=InputSourceAction(), nargs='+', help='logfile(s) to parse')


    def run(self, arguments=None):
        """ Print out useful information about the log file. """
        BaseCmdLineTool.run(self, arguments)

        for i, self.logfile in enumerate(self.args['logfile']):
            if i > 0:
                print
                print ' ------------------------------------------'
                print

            print "     source: %s" % self.logfile.name
            print "      start: %s" % (self.logfile.start.strftime("%Y %b %d %H:%M:%S") if self.logfile.start else "unknown")
            print "        end: %s" % (self.logfile.end.strftime("%Y %b %d %H:%M:%S") if self.logfile.start else "unknown")

            # TODO: add timezone if iso8601 format
            print "date format: %s" % self.logfile.datetime_format
            print "     length: %s" % len(self.logfile)
            print "     binary: %s" % (self.logfile.binary or "unknown")
            

            version = (' -> '.join(self.logfile.versions) or "unknown")

            # if version is unknown, go by date
            if version == 'unknown':
                if self.logfile.datetime_format == 'ctime-pre2.4':
                    version = '< 2.4 (no milliseconds)'
                elif self.logfile.datetime_format == 'ctime':
                    version = '>= 2.4 (milliseconds present)'
                elif self.logfile.datetime_format.startswith('iso8601-'):
                    version = '>= 2.6 (iso8601 format)'

            print "    version: %s" % version,
            print

            # now run requested section
            if 'command' in self.args:
                section = self.sections[ self.args['command'] ]
                print
                print section.name.upper()
                section.run()


if __name__ == '__main__':
    tool = MLogInfoTool()
    tool.run()
