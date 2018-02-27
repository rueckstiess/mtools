from datetime import timedelta

from .datetime_filter import DateTimeFilter
from mtools.util.cmdlinetool import InputSourceAction


class MaskFilter(DateTimeFilter):
    """
    MaskFilter class.

    This filter takes an argument `--mask <LOGFILE>` and another optional
    argument `--mask-size <SECS>`. It will read <LOGFILE> and for each of the
    lines extract the datetimes (let's call these "events"). It will add some
    padding for each of these events, <SECS>/2 seconds on either side.
    MaskFilter will then accept every line from the original log file
    (different to <LOGFILE>), that lies within one of these masked intervals.

    This feature is very useful to find all correlating lines to certain
    events.

    For example, find all assertions in a log file, then find all log lines
    surrounding these assertions:

        grep "assert" mongod.log > assertions.log
        mlogfilter mongod.log --mask assertions.log --mask-size 60
    """

    filterArgs = [
        ('--mask', {'action': 'store', 'type': InputSourceAction('rb'),
                    'help': ('source (log file or system.profile db) '
                             'to create the filter mask.')}),
        ('--mask-size', {'action': 'store', 'type': int, 'default': 60,
                         'help': ('mask size in seconds around each filter '
                                  'point (default: 60 secs, 30 on each side '
                                  'of the event)')}),
        ('--mask-center', {'action': 'store',
                           'choices': ['start', 'end', 'both'],
                           'default': 'end',
                           'help': ('mask center point for events with '
                                    'duration (default: end). If both is '
                                    'chosen, all events from start to end '
                                    'are returned.')})
        ]

    def __init__(self, mlogfilter):
        """
        Constructor.

        Init superclass and mark this filter active if `mask`
        argument is present.
        """
        DateTimeFilter.__init__(self, mlogfilter)
        self.active = ('mask' in self.mlogfilter.args and
                       self.mlogfilter.args['mask'] is not None)
        if self.active:
            self.mask_end_reached = False
            self.mask_source = self.mlogfilter.args['mask']
            self.mask_list = []

    def setup(self):
        """
        Create mask list.

        Consists of all tuples between which this filter accepts lines.
        """
        # get start and end of the mask and set a start_limit
        if not self.mask_source.start:
            raise SystemExit("Can't parse format of %s. Is this a log file or "
                             "system.profile collection?"
                             % self.mlogfilter.args['mask'])

        self.mask_half_td = timedelta(seconds=self.mlogfilter.args
                                      ['mask_size'] / 2)

        # load filter mask file
        logevent_list = list(self.mask_source)

        # define start and end of total mask
        self.mask_start = self.mask_source.start - self.mask_half_td
        self.mask_end = self.mask_source.end + self.mask_half_td

        # consider --mask-center
        if self.mlogfilter.args['mask_center'] in ['start', 'both']:
            if logevent_list[0].duration:
                self.mask_start -= timedelta(milliseconds=logevent_list[0]
                                             .duration)

        if self.mlogfilter.args['mask_center'] == 'start':
            if logevent_list[-1].duration:
                self.mask_end -= timedelta(milliseconds=logevent_list[-1]
                                           .duration)

        self.start_limit = self.mask_start

        # different center points
        if 'mask_center' in self.mlogfilter.args:
            if self.mlogfilter.args['mask_center'] in ['start', 'both']:
                starts = ([(le.datetime - timedelta(milliseconds=le.duration))
                          if le.duration is not None else le.datetime
                          for le in logevent_list if le.datetime])

            if self.mlogfilter.args['mask_center'] in ['end', 'both']:
                ends = [le.datetime for le in logevent_list if le.datetime]

            if self.mlogfilter.args['mask_center'] == 'start':
                event_list = sorted(starts)
            elif self.mlogfilter.args['mask_center'] == 'end':
                event_list = sorted(ends)
            elif self.mlogfilter.args['mask_center'] == 'both':
                event_list = sorted(zip(starts, ends))

        mask_list = []

        if len(event_list) == 0:
            return

        start_point = end_point = None

        for e in event_list:
            if start_point is None:
                start_point, end_point = self._pad_event(e)
                continue

            next_start = (e[0] if type(e) == tuple else e) - self.mask_half_td
            if next_start <= end_point:
                end_point = ((e[1] if type(e) == tuple else e) +
                             self.mask_half_td)
            else:
                mask_list.append((start_point, end_point))
                start_point, end_point = self._pad_event(e)

        if start_point:
            mask_list.append((start_point, end_point))

        self.mask_list = mask_list

    def _pad_event(self, event):
        if type(event) == tuple:
            start_point = event[0] - self.mask_half_td
            end_point = event[1] + self.mask_half_td
        else:
            start_point = event - self.mask_half_td
            end_point = event + self.mask_half_td

        return start_point, end_point

    def accept(self, logevent):
        """
        Process line.

        Overwrite BaseFilter.accept() and return True if the provided
        logevent should be accepted (causing output), or False if not.
        """
        dt = logevent.datetime
        if not dt:
            return False

        mask = next((mask for mask in self.mask_list
                     if mask[0] < dt and mask[1] > dt), None)

        return True if mask else False

    def skipRemaining(self):
        """
        Skip remaining lines.

        Overwrite BaseFilter.skipRemaining() and return True if all lines
        from here to the end of the file should be rejected (no output).
        """
        return self.mask_end_reached
