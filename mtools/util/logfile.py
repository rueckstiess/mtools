from mtools.util.logline import LogLine

class LogFile(object):
    """ wrapper class for log files, either as open file streams of from stdin. 
        Later planned to include logfile from a mongod instance.
    """

    def __init__(self, logfile):
        """ provide logfile as open file stream or stdin. """
        self.logfile = logfile
        self.from_stdin = logfile.name == "<stdin>"
        self._start = None
        self._end = None


    @property
    def start(self):
        """ lazy evaluation of start and end of logfile. Returns None for stdin input currently. """
        if self.from_stdin:
            return None
        if not self._start:
            self._calculate_bounds()
        return self._start

    @property
    def end(self):
        """ lazy evaluation of start and end of logfile. Returns None for stdin input currently. """
        if self.from_stdin:
            return None
        if not self._end:
            self._calculate_bounds()
        return self._end


    def _calculate_bounds(self):
        """ calculate beginning and end of logfile. """

        if self.from_stdin: 
            return None

        # get start datetime 
        for line in self.logfile:
            logline = LogLine(line)
            date = logline.datetime
            if date:
                break
        self._start = date

        # get end datetime (lines are at most 10k, go back 15k at most to make sure)
        self.logfile.seek(0, 2)
        file_size = self.logfile.tell()
        self.logfile.seek(-min(file_size, 15000), 2)

        for line in reversed(self.logfile.readlines()):
            logline = LogLine(line)
            date = logline.datetime
            if date:
                break
        self._end = date

        # if there was a roll-over, subtract 1 year from start time
        if self._end < self._start:
            self._start = self._start.replace(year=self._start.year-1)

        # reset logfile
        self.logfile.seek(0)


