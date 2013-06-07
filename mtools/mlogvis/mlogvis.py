#!/usr/bin/python

from mtools.util.logline import LogLine
from mtools.util.cmdlinetool import LogFileTool
import mtools

import argparse
import sys, os
import shutil
import time

import socket
import SimpleHTTPServer
import SocketServer
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

        outf = open('events.json', 'w')
        outf.write('{"type": "duration", "data":[')
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
                    outf.write(',\n')
                else:
                    first_row = False
                outf.write(logline.to_json(['line_str', 'datetime', 'operation', 'thread', 'namespace', 'nscanned', 'nreturned', 'duration']))
        outf.write(']}')
        outf.close()

        data_path = os.path.join(os.path.dirname(mtools.__file__), 'data')
        src = os.path.join(data_path, 'index.html')
        dst = os.path.join(os.getcwd(), 'index.html')
        
        print "trying to copy %s to %s" % (src, dst)
        shutil.copyfile(src, dst)

        Handler = SimpleHTTPServer.SimpleHTTPRequestHandler
        
        for i in range(100):
            try:
                httpd = SocketServer.TCPServer(("", self.port), Handler)
                break
            except socket.error:
                self.port += 1

        print "serving visualization on http://localhost:%s/"%self.port
        webbrowser.open("http://localhost:%i/"%self.port)

        httpd.serve_forever()


if __name__ == '__main__':
    tool = MLogVisTool()
    tool.run()

