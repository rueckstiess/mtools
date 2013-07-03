#!/usr/bin/python

from mtools.util.logline import LogLine
from mtools.util.cmdlinetool import LogFileTool
import mtools

import os
import webbrowser


class MLogVisTool(LogFileTool):

    def __init__(self):
        LogFileTool.__init__(self, multiple_logfiles=False, stdin_allowed=True)

        self.argparser.description = 'mongod/mongos log file visualizer (browser edition). \
            Extracts information from each line of the log file and outputs a json document \
            per line, stored in a sub-folder .mlogvis/. Then spins up an HTTP server and \
            opens a page in the browser to view the data.'

        self.port = 8888

    def run(self):
        LogFileTool.run(self)

        # make sub-folder .mlogvis and change to it
        mlogvis_dir = '.mlogvis'

        if not os.path.exists(mlogvis_dir):
            os.makedirs(mlogvis_dir)
        os.chdir(mlogvis_dir)

        data_path = os.path.join(os.path.dirname(mtools.__file__), 'data')
        srcfilelocation = os.path.join(data_path, 'index.html')
        outf = '{"type": "duration", "logfilename": "' + self.args['logfile'].name + '", "data":['

        first_row = True
        for line in self.args['logfile']:
            logline = LogLine(line)
            # group regular connections together
            if logline.datetime and logline.duration:
                if logline.thread and logline.thread.startswith("conn"):
                    logline._thread = "conn####"
                # write log line out as json
                if not first_row:
                    # prepend comma and newline
                    outf += ',\n'
                else:
                    first_row = False
                outf += logline.to_json(['line_str', 'datetime', 'operation', 'thread', 'namespace', 'nscanned', 'nreturned', 'duration'])
        outf += ']}'

        dstfilelocation = os.path.join(os.getcwd(), 'index.html')

        print "trying to copy %s to %s" % (srcfilelocation, dstfilelocation)

        srcfile = open(srcfilelocation)
        contents = srcfile.read()
        srcfile.close()

        dstfile = open(dstfilelocation, 'wt')
        replaced_contents = contents.replace('##REPLACE##', outf)
        dstfile.write(replaced_contents)
        dstfile.close()

        print "serving visualization on file://"+dstfilelocation

        webbrowser.open("file://"+dstfilelocation)


if __name__ == '__main__':
    tool = MLogVisTool()
    tool.run()
