#!/usr/bin/python

from mtools.util.logline import LogLine
from mtools.util.cmdlinetool import LogFileTool
import mtools

import os
import webbrowser


class MLogVisTool(LogFileTool):

    def __init__(self):
        LogFileTool.__init__(self, multiple_logfiles=False, stdin_allowed=True)

        self.argparser.description = 'mongod/mongos log file visualizer (browser edition). Extracts \
            information from each line of the log file and outputs a html file that can be viewed in \
            a browser. Automatically opens a browser tab and shows the file.'

    def run(self):
        LogFileTool.run(self)

        # store in current local folder
        mlogvis_dir = '.'

        # change stdin logfile name and remove the < >
        logname = self.args['logfile'].name
        if logname == '<stdin>':
            logname = 'stdin'

        os.chdir(mlogvis_dir)

        data_path = os.path.join(os.path.dirname(mtools.__file__), 'data')
        srcfilelocation = os.path.join(data_path, 'index.html')
        outf = '{"type": "duration", "logfilename": "' + logname + '", "data":['

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

        dstfilelocation = os.path.join(os.getcwd(), '%s.html'%logname)

        print "copying %s to %s" % (srcfilelocation, dstfilelocation)

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
