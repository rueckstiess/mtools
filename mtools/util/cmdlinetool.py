import argparse
import sys
from mtools.version import __version__
import signal
import datetime
import os

class BaseCmdLineTool(object):
    """ Base class for any mtools command line tool. Adds --version flag and basic control flow. """

    def __init__(self):
        """ Constructor. Any inheriting class should add a description to the argparser and extend 
            it with additional arguments as needed.
        """
        # define argument parser and add version argument
        self.argparser = argparse.ArgumentParser()
        self.argparser.add_argument('--version', action='version', version="mtools version %s" % __version__)

        self.is_stdin = not sys.stdin.isatty()
        

    def run(self, arguments=None, get_unknowns=False):
        """ Init point to execute the script. If `arguments` string is given, will evaluate the 
            arguments, else evaluates sys.argv. Any inheriting class should extend the run method 
            (but first calling BaseCmdLineTool.run(self)).
        """
        # redirect PIPE signal to quiet kill script, if not on Windows
        if os.name != 'nt':
            signal.signal(signal.SIGPIPE, signal.SIG_DFL)

        if get_unknowns:
            if arguments:
                self.args, self.unknown_args = self.argparser.parse_known_args(args=arguments.split())
            else:
                self.args, self.unknown_args = self.argparser.parse_known_args()
            self.args = vars(self.args)
        else:
            if arguments:
                self.args = vars(self.argparser.parse_args(args=arguments.split()))
            else:
                self.args = vars(self.argparser.parse_args())

    
    def _datetime_to_epoch(self, dt):
        """ converts the datetime to unix epoch (properly). """
        return int((dt - datetime.datetime(1970,1,1)).total_seconds())

    def update_progress(self, progress, prefix=''):
        """ use this helper function to print a progress bar for longer-running scripts. 
            The progress value is a value between 0.0 and 1.0. If a prefix is present, it 
            will be printed before the progress bar. 
        """
        total_length = 40

        if progress == 1.:
            sys.stdout.write('\r' + ' '*(total_length + len(prefix) + 12))
            sys.stdout.write('\n')
            sys.stdout.flush()
        else:
            bar_length = int(round(total_length*progress))
            sys.stdout.write('\r%s [%s%s] %.1f %% ' % (prefix, '='*bar_length, ' '*(total_length-bar_length), progress*100))
            sys.stdout.flush()


    def update_progress(self, progress, prefix=''):
        """ use this helper function to print a progress bar for longer-running scripts. 
            The progress value is a value between 0.0 and 1.0. If a prefix is present, it 
            will be printed before the progress bar. 
        """
        total_length = 40

        if progress == 1.:
            sys.stdout.write('\r' + ' '*(total_length*2 + len(prefix)))
            sys.stdout.write('\n')
            sys.stdout.flush()
        else:
            bar_length = int(round(total_length*progress))
            sys.stdout.write('\r%s [%s%s] %% %3.1f ' % (prefix, '='*bar_length, ' '*(total_length-bar_length), progress*100))
            sys.stdout.flush()


class LogFileTool(BaseCmdLineTool):
    """ Base class for any mtools tool that acts on logfile(s). """

    def __init__(self, multiple_logfiles=False, stdin_allowed=True):
        """ Constructor. Adds logfile(s) and stdin option to the argument parser. """
        BaseCmdLineTool.__init__(self)

        self.multiple_logfiles = multiple_logfiles
        self.stdin_allowed = stdin_allowed

        arg_opts = {'action':'store', 'type':argparse.FileType('r')}

        if self.multiple_logfiles:
            arg_opts['nargs'] = '*'
            arg_opts['help'] = 'logfile(s) to parse'
        else:
            arg_opts['help'] = 'logfile to parse'

        if self.is_stdin:
            if not self.stdin_allowed:
                raise SystemExit("this tool can't parse input from stdin.")
                
            arg_opts['const'] = sys.stdin
            arg_opts['action'] = 'store_const'
            if 'type' in arg_opts: 
                del arg_opts['type']
            if 'nargs' in arg_opts:
                del arg_opts['nargs']

        self.argparser.add_argument('logfile', **arg_opts)


if __name__ == '__main__':
    tool = LogFileTool(multiple_logfiles=False, stdin_allowed=True)
    tool.run()
    print tool.args

