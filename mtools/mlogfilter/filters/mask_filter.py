from datetime_filter import DateTimeFilter
from datetime import MINYEAR, timedelta
from mtools.util.logline import LogLine
from mtools.util.logfile import LogFile



class MaskFilter(DateTimeFilter):
    """ This filter takes an argument `--mask <LOGFILE>` and another optional argument
        `--mask-size <SECS>`. It will read <LOGFILE> and for each of the lines extract
        the datetimes (let's call these "events"). It will add some padding for each
        of these events, <SECS>/2 seconds on either side. MaskFilter will then accept
        every line from the original log file (different to <LOGFILE>), that lies within
        one of these masked intervals.

        This feature is very useful to find all correlating lines to certain events.

        For example, find all assertions in a log file, then find all log lines 
        surrounding these assertions:

            grep "assert" mongod.log > assertions.log
            mlogfilter mongod.log --mask assertions.log --mask-size 60

        """


    filterArgs = [
       ('--mask', {'action':'store', 'help':'log file to use for creating the filter mask.'}), 
       ('--mask-size', {'action':'store',  'type':int, 'default':60, 'help':'mask size in seconds around each filter point (default: 60 secs, 30 on each side of the event)'})
    ]


    def __init__(self, mlogfilter):
        """ constructor, init superclass and mark this filter active if `mask` argument is present. """
        DateTimeFilter.__init__(self, mlogfilter)
        self.active = ('mask' in self.mlogfilter.args)
        self.mask_end_reached = False

        self.mask_file = open(self.mlogfilter.args['mask'], 'r')
        self.mask_list = []


    def setup(self):
        """ create mask list consisting of all tuples between which this filter accepts lines. """
        
        # get start and end of the mask log file and set a start_limit
        lfinfo = LogFile(self.mask_file)
        if not lfinfo.start:
            raise SystemExit("Can't parse format of %s. Is this a log file?" % self.mlogfilter.args['mask'])

        self.mask_half_td = timedelta( seconds=self.mlogfilter.args['mask_size'] / 2 )
        self.mask_start = lfinfo.start - self.mask_half_td
        self.mask_end = lfinfo.end + self.mask_half_td

        self.start_limit = self.mask_start

        # create filter mask list
        event_list = [ll.datetime for ll in [ LogLine(line) for line in self.mask_file] if ll.datetime]
        mask_list = []

        if len(event_list) == 0:
            return

        start_point = end_point = None
        
        for e in event_list:
            
            if start_point == None:
                start_point = e - self.mask_half_td
                end_point = e + self.mask_half_td
                continue

            if (e - self.mask_half_td) <= end_point:
                end_point = e + self.mask_half_td
            else:
                mask_list.append((start_point, end_point))
                start_point = e - self.mask_half_td
                end_point = e + self.mask_half_td

        if start_point:
            mask_list.append((start_point, end_point))

        self.mask_list = mask_list


    def accept(self, logline):
        """ overwrite this method in subclass and return True if the provided 
            logline should be accepted (causing output), or False if not.
        """
        dt = logline.datetime
        mask = next( (mask for mask in self.mask_list if mask[0] < dt and mask[1] > dt), None )
        
        return True if mask else False



    def skipRemaining(self):
        """ overwrite this method in sublcass and return True if all lines
            from here to the end of the file should be rejected (no output).
        """
        return self.mask_end_reached