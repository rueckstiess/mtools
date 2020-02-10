#!/usr/bin/env python3

import datetime
import inspect
import sys

import mtools.mloginfo.sections as sections
from mtools.util.cmdlinetool import LogFileTool


class MLogInfoTool(LogFileTool):

    def __init__(self):
        """Constructor: add description to argparser."""
        LogFileTool.__init__(self, multiple_logfiles=True, stdin_allowed=False)

        self.argparser.description = ('Extracts general information from '
                                      'logfile and prints it to stdout.')
        self.argparser.add_argument('--debug', action='store_true',
                                    help=('show debug output '
                                          '(depends on info section)'))
        self.argparser.add_argument('--verbose', action='store_true',
                                    help=('show more verbose output '
                                          '(depends on info section)'))

        inf = 'info sections'
        cmds = ('Below commands activate additional info sections for the '
                'log file.')
        self.argparser_sectiongroup = self.argparser.add_argument_group(inf,
                                                                        cmds)

        # add all filter classes from the filters module
        self.sections = ([c[1](self)
                          for c in inspect.getmembers(sections,
                                                      inspect.isclass)])

    def run(self, arguments=None):
        """Print useful information about the log file."""
        LogFileTool.run(self, arguments)

        if (self.args['logfile'] is None or len(self.args['logfile']) == 0):
            self.argparser.print_usage()
            print("\nERROR: At least one logfile argument must be provided")
            self.argparser.exit()

        for i, self.logfile in enumerate(self.args['logfile']):
            if i > 0:
                print("\n ------------------------------------------\n")

            if self.logfile.datetime_format == 'ctime-pre2.4':
                # no milliseconds when datetime format doesn't support it
                start_time = (self.logfile.start.strftime("%Y %b %d %H:%M:%S")
                              if self.logfile.start else "unknown")
                end_time = (self.logfile.end.strftime("%Y %b %d %H:%M:%S")
                            if self.logfile.start else "unknown")
            else:
                # include milliseconds
                start_time = (self.logfile.start.strftime("%Y %b %d "
                                                          "%H:%M:%S.%f")[:-3]
                              if self.logfile.start else "unknown")
                end_time = (self.logfile.end.strftime("%Y %b %d "
                                                      "%H:%M:%S.%f")[:-3]
                            if self.logfile.start else "unknown")

            print("     source: %s" % self.logfile.name)
            print("       host: %s"
                  % (self.logfile.hostname + ':' + str(self.logfile.port)
                     if self.logfile.hostname else "unknown"))
            print("      start: %s" % (start_time))
            print("        end: %s" % (end_time))

            print("date format: %s" % self.logfile.datetime_format)

            # self.logfile.timezone is a dateutil.tzinfo object
            tzdt = datetime.datetime.now(self.logfile.timezone)
            if (tzdt.tzname()):
                timezone = tzdt.tzname()
            else:
                timezone = f"UTC {tzdt.strftime('%z')}"
            print("   timezone: %s" % timezone)
            print("     length: %s" % len(self.logfile))
            print("     binary: %s" % (self.logfile.binary or "unknown"))

            version = (' -> '.join(self.logfile.versions) or "unknown")

            # if version is unknown, go by date
            if version == 'unknown':
                if self.logfile.datetime_format == 'ctime-pre2.4':
                    version = '< 2.4 (no milliseconds)'
                elif self.logfile.datetime_format == 'ctime':
                    version = '>= 2.4.x ctime (milliseconds present)'
                elif (self.logfile.datetime_format == "iso8601-utc" or
                      self.logfile.datetime_format == "iso8601-local"):
                    if self.logfile.has_level:
                        version = '>= 3.0 (iso8601 format, level, component)'
                    else:
                        version = '= 2.6.x (iso8601 format)'

            print("    version: %s" % version)
            print("    storage: %s"
                  % (self.logfile.storage_engine or 'unknown'))

            # now run all sections
            for section in self.sections:
                if section.active:
                    print("\n%s" % section.name.upper())
                    section.run()


def main():
    tool = MLogInfoTool()
    tool.run()
    return 0  # we need to return an integer


if __name__ == '__main__':
    sys.exit(main())
