#!/usr/bin/env python3
"""Command line tool utility."""

import argparse
import codecs
import datetime
import os
import re
import signal
import sys

from dateutil.tz import tzutc

from mtools.util.logfile import LogFile
from mtools.version import __version__

try:
    from mtools.util.profile_collection import ProfileCollection

    class InputSourceAction(argparse.FileType):
        """
        Extend the FileType class from the argparse module.

        Try to open the file and pass the handle to a new LogFile object, but
        if that's not possible it will catch the exception and interpret the
        string as a MongoDB URI and try to connect to the database. In that
        case, it will return a ProfileCollection object.

        Both derive from the same base class InputSource and support iteration
        over LogEvents.
        """

        def __call__(self, string):
            """Open log file or MongoDB database."""

            try:
                # catch filetype and return LogFile object
                filehandle = argparse.FileType.__call__(self, string)
                return LogFile(filehandle)

            except argparse.ArgumentTypeError:
                # not a file, try open as MongoDB database
                m = re.match('^(\w+)(?::(\d+))?(?:/([a-zA-Z0-9._-]+))?$',
                             string)
                if m:
                    hostname, port, namespace = m.groups()
                    port = int(port) if port else 27017
                    namespace = namespace or 'test.system.profile'
                    if '.' in namespace:
                        database, collection = namespace.split('.', 1)
                    else:
                        database = namespace
                        collection = 'system.profile'

                    if (hostname == 'localhost' or
                            re.match('\d+\.\d+\.\d+\.\d+', hostname)):
                        return ProfileCollection(hostname, port, database,
                                                 collection)

                raise argparse.ArgumentTypeError("can't open %s as file or "
                                                 "MongoDB connection string."
                                                 % string)

except ImportError:
    class InputSourceAction(argparse.FileType):
        """Extend the FileType class from the argparse module."""

        def __call__(self, string):
            """Open log file."""
            try:
                # catch filetype and return LogFile object
                filehandle = argparse.FileType.__call__(self, string)
                return LogFile(filehandle)
            except argparse.ArgumentTypeError:
                raise argparse.ArgumentTypeError("can't open %s" % string)


class BaseCmdLineTool(object):
    """
    Base class for any mtools command line tool.

    Adds --version flag and basic control flow.
    """

    def __init__(self):
        """
        Constructor.

        Any inheriting class should add a description to the argparser and
        extend it with additional arguments as needed.
        """
        # define argument parser and add version argument
        self.argparser = argparse.ArgumentParser()
        self.argparser.add_argument(
            '--version', 
            action='version',
            version=f'''mtools version {__version__} || Python {sys.version}'''
        )
        self.argparser.add_argument('--no-progressbar', action='store_true',
                                    default=False,
                                    help='disables progress bar')
        self.is_stdin = not sys.stdin.isatty()

    def run(self, arguments=None, get_unknowns=False):
        """
        Init point to execute the script.

        If `arguments` string is given, will evaluate the arguments, else
        evaluates sys.argv. Any inheriting class should extend the run method
        (but first calling BaseCmdLineTool.run(self)).
        """

        # redirect PIPE signal to quiet kill script, if not on Windows
        if os.name != 'nt':
            signal.signal(signal.SIGPIPE, signal.SIG_DFL)
        if get_unknowns:
            if arguments:
                self.args, self.unknown_args = (self.argparser.parse_known_args
                                                (args=arguments.split()))
            else:
                (self.args,
                 self.unknown_args) = self.argparser.parse_known_args()
            self.args = vars(self.args)
        else:
            if arguments:
                myargs = arguments.split()
                self.args = vars(self.argparser.parse_args
                                 (args=myargs))
            else:
                self.args = vars(self.argparser.parse_args())

        self.progress_bar_enabled = (not (self.args['no_progressbar'] or
                                          self.is_stdin))

    def _datetime_to_epoch(self, dt):
        """Convert the datetime to unix epoch (properly)."""
        if dt:
            td = (dt - datetime.datetime.fromtimestamp(0, tzutc()))
            # don't use total_seconds(), that's only available in 2.7
            total_secs = int((td.microseconds +
                              (td.seconds + td.days * 24 * 3600) *
                              10**6) / 10**6)
            return total_secs
        else:
            return 0

    def update_progress(self, progress, prefix=''):
        """
        Print a progress bar for longer-running scripts.

        The progress value is a value between 0.0 and 1.0. If a prefix is
        present, it will be printed before the progress bar.
        """
        total_length = 40

        if progress == 1.:
            sys.stderr.write('\r' + ' ' * (total_length + len(prefix) + 50))
            sys.stderr.write('\n')
            sys.stderr.flush()
        else:
            bar_length = int(round(total_length * progress))
            sys.stderr.write('\r%s [%s%s] %.1f %% '
                             % (prefix, '=' * bar_length,
                                ' ' * (total_length - bar_length),
                                progress * 100))
            sys.stderr.flush()


class LogFileTool(BaseCmdLineTool):
    """Base class for any mtools tool that acts on logfile(s)."""

    def __init__(self, multiple_logfiles=False, stdin_allowed=True):
        """Add logfile(s) and stdin option to the argument parser."""
        BaseCmdLineTool.__init__(self)

        self.multiple_logfiles = multiple_logfiles
        self.stdin_allowed = stdin_allowed

        arg_opts = {'action': 'store', 'type': InputSourceAction('rb')}

        if self.multiple_logfiles:
            arg_opts['nargs'] = '*'
            arg_opts['help'] = 'logfile(s) to parse'
        else:
            arg_opts['help'] = 'logfile to parse'

        if self.is_stdin:
            if not self.stdin_allowed:
                raise SystemExit("this tool can't parse input from stdin.")

            arg_opts['const'] = LogFile(sys.stdin)
            arg_opts['action'] = 'store_const'
            if 'type' in arg_opts:
                del arg_opts['type']
            if 'nargs' in arg_opts:
                del arg_opts['nargs']
        self.argparser.add_argument('logfile', **arg_opts)


if __name__ == '__main__':
    tool = LogFileTool(multiple_logfiles=True, stdin_allowed=True)
    tool.run()
    print(tool.args)
    # for line in tool.args['logfile']:
    #     print(line)
