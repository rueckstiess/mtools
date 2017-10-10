from base_section import BaseSection
from collections import defaultdict
from datetime import datetime, date, time

try: 
    from mtools.util.profile_collection import ProfileCollection
except ImportError:
    ProfileCollection = None
    
class ConnectionSection(BaseSection):
    """ This section goes through the logfile and extracts information 
        about opened and closed connections.
    """
    
    name = "connections"

    def __init__(self, mloginfo):
        BaseSection.__init__(self, mloginfo)

        # add --restarts flag to argparser
        self.mloginfo.argparser_sectiongroup.add_argument('--connections', action='store_true', help='outputs information about opened and closed connections')
        self.mloginfo.argparser_sectiongroup.add_argument('--stats', action='store_true', help='outputs helpful statistics for connection duration (min/max/avg)')


    @property
    def active(self):
        """ return boolean if this section is active. """
        return self.mloginfo.args['connections']


    def run(self):
        """ run this section and print out information. """
        if ProfileCollection and isinstance(self.mloginfo.logfile, ProfileCollection):
            print
            print "    not available for system.profile collections"
            print
            return

        ip_opened = defaultdict(lambda: 0)
        ip_closed = defaultdict(lambda: 0)
        
        socket_exceptions = 0

        genstats = self.mloginfo.args['stats']
        if genstats:
            genstats = True
            connections_start = defaultdict(lambda: 0)
            ipwise_sum_durations = defaultdict(lambda:0)
            ipwise_count = defaultdict(lambda:0)
            ipwise_min_connection_duration = defaultdict(lambda:9999999999)
            ipwise_max_connection_duration = defaultdict(lambda:-1)

            min_connection_duration = 9999999999
            max_connection_duration = -1

            sum_durations = 0
            fullconn_counts = 0

        for logevent in self.mloginfo.logfile:
            line = logevent.line_str

 
            pos = line.find('connection accepted')
            if pos != -1:
                # connection was opened, increase counter
                tokens = line[pos:pos+100].split(' ')
                if tokens[3] == 'anonymous':
                    ip = 'anonymous'
                else:
                    ip, _ = tokens[3].split(':')
                ip_opened[ip] += 1

                if genstats:
                    dt = logevent.datetime

                    #initialize using default constructor
                    ipwise_min_connection_duration[ip]
                    ipwise_max_connection_duration[ip]

                    connid = tokens[4].strip('#')

                    if dt != None:                  
                        connections_start[connid] = dt  
    #                    print "connection id %s start %s" % (connid, connections_start[connid])
                

            pos = line.find('end connection')
            if pos != -1:
                # connection was closed, increase counter
                tokens = line[pos:pos+100].split(' ')
                if tokens[2] == 'anonymous':
                    ip = 'anonymous'
                else:
                    ip, _ = tokens[2].split(':')
                ip_closed[ip] += 1

                if genstats:
                    dt = logevent.datetime

                    #The connection id value is stored just before end connection -> [conn385] end connection
                    tokens_conn = line[:pos].split(' ')
                    end_connid = tokens_conn[3].strip('[|conn|]')
    #                print "End connection id %s " % (end_connid)

                    #Check if the log file recorded start of this connid
                    if connections_start[end_connid]:
    #                    print "connection id end %s" % (connections_start[end_connid])

                        if dt != None:
                            dur = dt - connections_start[end_connid]
                            dur_in_sec = dur.seconds
    #                        print "Duration of connection id %s is %d seconds" % (end_connid, dur_in_sec)

                            if dur_in_sec < min_connection_duration:
                                min_connection_duration = dur_in_sec

                            if dur_in_sec > max_connection_duration:
                                max_connection_duration = dur_in_sec

                            if dur_in_sec < ipwise_min_connection_duration[ip]:
                                ipwise_min_connection_duration[ip] = dur_in_sec

                            if dur_in_sec > ipwise_max_connection_duration[ip]:
                                ipwise_max_connection_duration[ip] = dur_in_sec

                            sum_durations += dur.seconds
                            fullconn_counts += 1

                            ipwise_sum_durations[ip] += dur_in_sec
                            ipwise_count[ip] += 1


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
            opened = ip_opened[ip] if ip in ip_opened else 0
            closed = ip_closed[ip] if ip in ip_closed else 0

            if genstats:
                covered_count = ipwise_count[ip] if ip in ipwise_count else 1
                connection_duration_ip = ipwise_sum_durations[ip] if ip in ipwise_sum_durations else 0

                print "%-15s  opened: %-8i  closed: %-8i dur-avg(s): %-8i dur-min(s): %-8i dur-max(s): %-8i" % (ip, opened, closed, connection_duration_ip/covered_count, ipwise_min_connection_duration[ip], ipwise_max_connection_duration[ip])
            else:
                print "%-15s  opened: %-8i  closed: %-8i" % (ip, opened, closed)

        print

        if genstats and fullconn_counts > 0:
            print "Average connection duration across all IPs %d seconds, Minimum duration %d , Maximum duration %d" % (sum_durations/fullconn_counts, min_connection_duration, max_connection_duration)
        
