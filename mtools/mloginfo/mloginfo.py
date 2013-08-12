#!/usr/bin/python

from mtools.util.logfile import LogFile
from mtools.util.logline import LogLine
from mtools.util.cmdlinetool import LogFileTool

class MLogInfoTool(LogFileTool):

    def __init__(self):
        """ Constructor: add description to argparser. """
        LogFileTool.__init__(self, multiple_logfiles=False, stdin_allowed=False)
        
        self.argparser.description = 'Extracts general information from logfile and prints it to stdout.'
        self.argparser.add_argument('--restarts', action='store_true', help='outputs information about every detected restart.')


    def run(self, arguments=None):
        """ Print out useful information about the log file. """
        LogFileTool.run(self, arguments)

        logfile = LogFile(self.args['logfile'])
        print "start of logfile: %s" % logfile.start.strftime("%b %d %H:%M:%S")
        print "  end of logfile: %s" % logfile.end.strftime("%b %d %H:%M:%S")

        # get one logline (within first 20 lines) for datetime format
        logline = None
        for i in range(20):
            logline = LogLine(self.args['logfile'].next())
            if logline.datetime:
                break

        # TODO: add timezone if iso8601 format
        
        print "    line numbers: %s" % logfile.num_lines
        print "          binary: %s" % (logfile.binary or "unknown")

        version = (' -> '.join(logfile.versions) or "unknown")
        
        # if version is unknown, go by date
        if version == 'unknown' and logline:
            if logline.datetime_format == 'ctime-pre2.4':
                version = '< 2.4 (no milliseconds)'
            elif logline.datetime_format == 'ctime':
                version = '>= 2.4 (milliseconds present)'
            elif logline.datetime_format.startswith('iso8601-'):
                version = '>= 2.6 (iso8601 format)'

        print "         version: %s" % version

        # restarts section
        if self.args['restarts']:
            print
            print "RESTARTS"

            for version, logline in logfile.restarts:
                print "   %s version %s" % (logline.datetime.strftime("%b %d %H:%M:%S"), version)

            if len(logfile.restarts) == 0:
                print "  no restarts found"


if __name__ == '__main__':
    tool = MLogInfoTool()
    tool.run()
