#!/usr/bin/python

from mtools.util.logline import LogLine

import argparse
import sys, os
import shutil
import time

import socket
import SimpleHTTPServer
import SocketServer
import webbrowser

PORT = 8888
here = os.path.dirname(__file__)


if __name__ == '__main__':
    # create parser object
    parser = argparse.ArgumentParser(description='mongod/mongos log file visualizer (browser edition). \
        Extracts information from each line of the log file and outputs a json document per line, stored \
        in a sub-folder .mlogvis/. Then spins up an HTTP server and opens a page in the browser to view the data.')
    
    # only create default argument if not using stdin
    if sys.stdin.isatty():
        parser.add_argument('logfile', action='store', help='logfile to visualize.')

    args = vars(parser.parse_args())

    # open logfile
    if sys.stdin.isatty():
        logfile = open(args['logfile'], 'r')
    else:
        logfile = sys.stdin

    # make sub-folder .mlogvis and change to it
    mlogvis_dir = '.mlogvis'

    if not os.path.exists(mlogvis_dir):
        os.makedirs(mlogvis_dir)
    os.chdir(mlogvis_dir)

    outf = open('events.json', 'w')
    outf.write('{"type": "duration", "data":[')
    first_row = True
    for line in logfile:
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

    src = os.path.join(os.path.dirname(here, 'index.html')
    dst = os.path.join(os.getcwd(), 'index.html')
    print "trying to copy %s to %s" % (src, dst)
    shutil.copyfile(src, dst)

    Handler = SimpleHTTPServer.SimpleHTTPRequestHandler
    
    for i in range(100):
        try:
            httpd = SocketServer.TCPServer(("", PORT), Handler)
            break
        except socket.error:
            PORT += 1

    print "serving visualization on http://localhost:%s/"%PORT
    webbrowser.open("http://localhost:%i/"%PORT)

    httpd.serve_forever()



