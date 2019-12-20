#!/usr/bin/env python

import os
import sys
import webbrowser

import mtools
from mtools.util.cmdlinetool import LogFileTool


class MLogVisTool(LogFileTool):

    def __init__(self):
        LogFileTool.__init__(self, multiple_logfiles=False, stdin_allowed=True)

        self.argparser.description = ('mongod/mongos log file visualizer '
                                      '(browser edition). Extracts '
                                      'information from each line of the log '
                                      'file and outputs a html file that can '
                                      'be viewed in a browser. Automatically '
                                      'opens a browser tab and shows the '
                                      'file.')
        self.argparser.add_argument('--no-browser', action='store_true',
                                    help=('only creates .html file, but does '
                                          'not open the browser.'))
        self.argparser.add_argument('--out', '-o', action='store',
                                    default=None,
                                    help=('filename to output. Default is '
                                          '<original logfile>.html'))
        self.argparser.add_argument('--line-max', action='store',
                                    type=int, default=10000,
                                    help=('max count of datapoints at which '
                                          'actual log line strings are not '
                                          'printed any more.'))

    def _export(self, with_line_str=True):
        fields = ['_id', 'datetime', 'operation', 'thread', 'namespace',
                  'nscanned', 'nreturned', 'duration', 'numYields', 'w', 'r']
        if with_line_str:
            fields.append('line_str')

        first_row = True
        result_str = ''
        out_count = 0
        for line_no, logevent in enumerate(self.args['logfile']):
            # only export lines that have a datetime and duration
            if logevent.duration is not None and logevent.datetime:
                out_count += 1
                # if too many lines include a line_str, the page won't load
                if with_line_str and out_count > self.args['line_max']:
                    print("Warning: more than %i data points detected. "
                          "Skipping actual log line strings for faster "
                          "plotting." % self.args['line_max'])
                    return False
                # write log line out as json
                if not first_row:
                    # prepend comma and newline
                    result_str += ',\n'
                else:
                    first_row = False
                # hack to include _id for log lines from file
                logevent._id = line_no
                result_str += logevent.to_json(fields)
        return result_str

    def run(self, arguments=None):
        LogFileTool.run(self, arguments)

        # store in current local folder
        mlogvis_dir = '.'

        # change stdin logfile name and remove the < >
        logname = self.args['logfile'].name
        if logname == '<stdin>':
            logname = 'stdin'

        if self.args['out'] is not None:
            outputname = self.args['out']
        else:
            outputname = logname + '.html'

        os.chdir(mlogvis_dir)

        data_path = os.path.join(os.path.dirname(mtools.__file__), 'data')
        srcfilelocation = os.path.join(data_path, 'index.html')

        json_docs = self._export(True)
        if not json_docs:
            json_docs = self._export(False)

        outf = ('{"type": "duration", "logfilename": "' +
                logname + '", "data":[' + json_docs + ']}')

        dstfilelocation = os.path.join(os.getcwd(), '%s' % outputname)

        print("copying %s to %s" % (srcfilelocation, dstfilelocation))

        srcfile = open(srcfilelocation)
        contents = srcfile.read()
        srcfile.close()

        dstfile = open(dstfilelocation, 'wt')
        replaced_contents = contents.replace('##REPLACE##', outf)
        dstfile.write(replaced_contents)
        dstfile.close()

        if not self.args['no_browser']:
            print("serving visualization on file://" + dstfilelocation)
            webbrowser.open("file://" + dstfilelocation)


def main():
    tool = MLogVisTool()
    tool.run()


if __name__ == '__main__':
    sys.exit(main())
