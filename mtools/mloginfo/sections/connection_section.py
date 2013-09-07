from base_section import BaseSection
from collections import defaultdict
import re

class ConnectionSection(BaseSection):
    """ This section goes through the logfile and extracts information 
        about opened and closed connections.
    """
    
    name = "connections"

    def __init__(self, mloginfo):
        BaseSection.__init__(self, mloginfo)

        # add --restarts flag to argparser
        self.mloginfo.argparser_sectiongroup.add_argument('--connections', action='store_true', help='outputs information about opened and closed connections')


    @property
    def active(self):
        """ return boolean if this section is active. """
        return self.mloginfo.args['connections']


    def run(self):
        """ run this section and print out information. """

        ip_opened = defaultdict(lambda: 0)
        ip_closed = defaultdict(lambda: 0)
        socket_exceptions = 0

        # rewind log file in case other sections are walking the lines
        self.mloginfo.args['logfile'].seek(0, 0)

        for line in self.mloginfo.args['logfile']:
            pos = line.find('connection accepted')
            if pos != -1:
                # connection was opened, increase counter
                tokens = line[pos:pos+100].split(' ')
                ip, _ = tokens[3].split(':')
                ip_opened[ip] += 1

            pos = line.find('end connection')
            if pos != -1:
                # connection was closed, increase counter
                tokens = line[pos:pos+100].split(' ')
                ip, _ = tokens[2].split(':')
                ip_closed[ip] += 1

            if "SocketException" in line:
                socket_exceptions += 1


        # calculate totals
        total_opened = sum(ip_opened.values())
        total_closed = sum(ip_closed.values())

        unique_ips = set(ip_opened.keys())
        unique_ips.update(ip_closed.keys())


        # output statistics
        print "     total opened:", total_opened
        print "     total closed:", total_closed
        print "    no unique IPs:", len(unique_ips)
        print "socket exceptions:", socket_exceptions
        print

        for ip in sorted(unique_ips, key=lambda x: ip_opened[x], reverse=True):
            print ip
            print "    opened:", ip_opened[ip] if ip in ip_opened else 0
            print "    closed:", ip_closed[ip] if ip in ip_closed else 0
            print

