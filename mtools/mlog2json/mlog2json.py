#!/usr/bin/python

from mtools.util.logline import LogLine
from mtools.util.cmdlinetool import LogFileTool

class MLog2JsonTool(LogFileTool):

    def __init__(self):
        """ Constructor: add description to argparser. """
        LogFileTool.__init__(self, multiple_logfiles=False, stdin_allowed=True)
        
        self.argparser.description = 'mongod/mongos log file to json converter. \
            Extracts information from each line of the log file and outputs a \
            json document per line. To import into mongodb, use: mlog2json \
            logfile | mongoimport -d DATABASE -c COLLECTION'

    def run(self):
        """ Go through each line, convert string to LogLine object, then print
            JSON representation of the line. 
        """
        LogFileTool.run(self)

        for line in self.args['logfile']:
            print LogLine(line).to_json()


if __name__ == '__main__':
    tool = MLog2JsonTool()
    tool.run()
