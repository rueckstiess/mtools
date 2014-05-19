import os
import re
import datetime
from base_filter import BaseFilter


class ThreadsFilter(BaseFilter):
    """
    This filter breaks the log files into separate thread files. It takes a
    number of parameters that control the format of the outputted files.

    --flatten/--[no]-flatten: These parameters control the directory structure generated.
    If --flatten(the default) is provided then the directory structure will look something like :
       ./threads/flat/<file 1>
                      <file 2>
                      <file 3>
    That is, all the files are in a single directory.
    If --no-flatten is specified then the directory structure will look more like :
       ./threads/structured/<time 1>/<file 1>
                                     <file 2>
       ./threads/structured/<time 2>/<file 3>

    That is, the files are put in a multiple directories based on the thread start time (if known).

    The --bucketsize specifies an integer param (default is 1), which is the number of seconds used to
    bucket the files in when using --no-flatten or structured.
    In the case of --flatten OR --no-flatten, it also affects the name of file created (the thread creation time
    is promoted to the nearest bucket).

    This bucketing can be very useful when you want to find the amount of activity per unit time. It is very similar to the
    --bucketsize parameter for the `mplotqueries --type connchurn` command.

    The --out parameter specifies the output directory for the thread files, it defaults to "./threads/"
    """

    filterArgs = [
        ('--threads',    {'action': 'store_true',
                          'help': 'split file into separate files per threads'}),
        ('--flatten',    {'action': 'store_true',
                          'dest': 'flatten',
                          'help': 'split the log into separate files for every thread.',
                          'default': True}),
        ('--no-flatten', {'action': 'store_false',
                          'dest': 'flatten',
                          'help': 'split the log into separate files for every thread.'}),
        ('--bucketsize', {'action': 'store',
                          'help': 'the bucket size.',
                          'default': 1}),
        ('--out',        {'action': 'store',
                          'default': './threads/',
                          'help': 'the destination directory.'}),
    ]

    ACCEPTED = re.compile('^.* connection accepted from (?P<host>[a-zA-Z0-9\-\.:]+) (?P<id>#[0-9]+)')
    ENDED = re.compile('^.* \[(?P<conn>[a-zA-Z0-9]+)\] end connection (?P<host>[a-zA-Z\-0-9\.:]+)')
    STARTING = re.compile('^.* \[.*\] (MongoDB starting :|MongoS .* starting:) pid=')
    FMT = '%y%H%M%S'

    def __init__(self, mlogfilter):
        """
        Create a new filter instance for the 'threads' filter.
        if the 'threads' command line is True then the filter is activated and
        the initial configuration is created.
        :param mlogfilter: configuration information for the filter
        """
        BaseFilter.__init__(self, mlogfilter)

        if 'threads' in self.mlogfilter.args and self.mlogfilter.args['threads'] == True:
            self.conns = {}
            self.active = True
            self.flatten = self.mlogfilter.args['flatten'] if 'flatten' in self.mlogfilter.args else True
            if 'out' in self.mlogfilter.args and self.mlogfilter.args['out'] is not None:
                self.out = self.mlogfilter.args['out']
            self.active = True
            self.bucketsize = int(self.mlogfilter.args['bucketsize']) if 'bucketsize' in self.mlogfilter.args else 1
            if self.bucketsize < 0:
                self.bucketsize = 1
        else:
            self.active = False

    def teardown(self):
        """
        teardown event for a filter. Since the log files may not contain all the events for a thread,
        for example the close connection for 'conn13', we need this method to flush any remaining events
        before the filter completes.
        """
        for k, lines in self.conns.items():
            outfile = self.get_outfile(lines)
            try:
                f = open(outfile, 'w+')
                for item in lines:
                    f.write("%s\n" % item)
            finally:
                f.close()
        self.conns.clear()


    def flush(self, logevent):
        """
        If the logevent is a start event, then flush all current events (otherwise connections
        between multiple sessions may end up in the same file and the start information for the
        thread is lost/muddled.
        :param logevent: the logevent to check
        """
        if self.STARTING.match(logevent.line_str):
            self.teardown()

    def bucket(self, time, up=False):
        """
        convert time to the nearest bucket.
        :param time: the logevent time to bucket
        :param up: round up (down is the default) or down
        """
        v = time
        if self.bucketsize > 1:
            v = int(time.strftime("%s"))
            v -= v % self.bucketsize
            if up:
                v += 2 * self.bucketsize
            v = datetime.datetime.fromtimestamp(v)
        return v

    def get_end(self, lines):
        """
        get the last good time for a thread. If some event lines are missing
        then this may not be completely accurate.
        :param lines: the log event lines for a thread
        """
        line = next(obj for obj in reversed(lines) if obj.datetime is not None)
        est = line.datetime
        st = self.bucket(est, False)
        return st.strftime(self.FMT)

    def get_start(self, lines):
        """
        get the first good time for a thread. If some event lines are missing then this
        time may not be completely accurate.
        :param lines: the log event lines for a thread
        """
        line = next(obj for obj in lines if obj.datetime is not None)
        est = line.datetime
        st = self.bucket(est, False)
        return st.strftime(self.FMT)

    def append(self, identifier, line):
        """
        add the line to the list of lines for the thread
        :param identifier: the thread identifier , for example 'conn13' or 'initandlisten'
        :param line: the log line event
        :return: the lines for this identifier
        """
        if not identifier in self.conns:
            self.conns[identifier] = []
        return self.conns[identifier].append(line)

    def get_outfile(self, lines):
        """
        generate a file name for the thread. The file name depends on a number of factors:
            # the hostname from the first or last event
            # the first good timestamp (and the bucketsize)
            # the last good timestamp (and the bucketsize)
            # the thread name
            # the --flatten/--no-flatten flags
        In addition to generating a file name, this method will also create the containing
        directory if it does not already exist.
        :param lines: the log line event
        :return: the lines for this identifier
        """
        endline = lines[-1]
        startline = lines[0]

        match_data = self.ENDED.match(endline.line_str) or self.ACCEPTED.match(startline.line_str)
        if match_data is not None:
            frm = match_data.group('host')
            frm = re.sub(':', '_', frm)
        else:
            frm = None

        estamp = self.get_end(lines)
        sstamp = self.get_start(lines)

        dirname = self.out
        p = [dirname]
        thread = endline.thread
        if thread is not None and thread.startswith("conn"):
            md = self.ACCEPTED.match(endline.line_str)
            if md is not None:
                thread = "conn" + md.group('id')
        if thread is None:
            dbe = re.compile(r" dbexit:")
            dbexit = next(obj for obj in lines if dbe.match(obj.line_str) is None)
            if dbexit is not None:
                thread = 'dbexit'
            else:
                thread = 'unknown'

        name = '_'.join([x for x in [sstamp, estamp, frm, thread] if x is not None])
        if self.flatten:
            p += ['flat', name]
        else:
            p += ['structured', sstamp, name]
        outfile = os.path.join(*p) + '.log'
        directory = os.path.dirname(outfile)
        if not os.path.exists(directory):
            os.makedirs(os.path.dirname(outfile))
        return outfile

    def process_connect(self, logevent):
        """
        append the log line to the correct thread if it matches a connection  accepted event
        :param logevent: the log line event to check
        """
        match_data = self.ACCEPTED.match(logevent.line_str)
        if match_data:
            self.append(logevent.conn, logevent)

    def process_line(self, logevent):
        """
        append the log line to the correct thread
        :param logevent: the log line event to check
        """
        self.append(logevent.thread, logevent)

    def process_disconnect(self, endline):
        """
        flush a thread to the correct file if it matches the disconnect pattern. Delete the
        thread from the dictionary on completion.
        :param endline: the log line event to check
        """
        match_data = self.ENDED.match(endline.line_str)
        if match_data:
            c = endline.thread
            outfile = self.get_outfile(self.conns[c])
            f = open(outfile, 'w+')
            try:
                for item in self.conns[c]:
                    f.write("%s\n" % item)
                del self.conns[c]
            finally:
                f.close()

    def accept(self, logevent):
        """
        Standard filter method, if enabled this filter always returns False
        In this case the log lines are not displayed but streamed into the files in the threads directory
        :param logevent: the log line to check
        """
        if self.active:
            self.flush(logevent)

            self.process_connect(logevent)
            self.process_line(logevent)
            self.process_disconnect(logevent)
            return False
        else:
            return True
