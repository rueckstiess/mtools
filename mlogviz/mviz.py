#!/usr/bin/python

from mtools.mtoolbox.logline import LogLine
import webbrowser
import argparse
import sys
import time

import SimpleHTTPServer
import SocketServer

PORT = 8888

if __name__ == '__main__':
    # create parser object
    parser = argparse.ArgumentParser(description='mongod/mongos log file to json converter. \
        Extracts information from each line of the log file and outputs a json document per line. \
        To import into mongodb, use: mlog2json logfile | mongoimport -d DATABASE -c COLLECTION')
    
    # only create default argument if not using stdin
    if sys.stdin.isatty():
        parser.add_argument('logfile', action='store', help='logfile to convert')

    args = vars(parser.parse_args())

    # open logfile
    if sys.stdin.isatty():
        logfile = open(args['logfile'], 'r')
    else:
        logfile = sys.stdin

    outf = open('mviz_events.json', 'w')
    outf.write('[')
    for line in logfile:
        logline = LogLine(line)
        # group regular connections together
        if logline.datetime and logline.duration:
            if logline.thread and logline.thread.startswith("conn"):
                logline._thread = "conn####"
            # write log line out as json
            outf.write(logline.to_json(['line_str', 'datetime', 'operation', 'thread', 'namespace', 'nscanned', 'nreturned', 'duration']) + ",\n")
    outf.write('{}]')
    outf.close()

    Handler = SimpleHTTPServer.SimpleHTTPRequestHandler
    httpd = SocketServer.TCPServer(("", PORT), Handler)

    print "serving visualization at port", PORT
    webbrowser.open("http://localhost:%i/"%PORT)

    httpd.serve_forever()



