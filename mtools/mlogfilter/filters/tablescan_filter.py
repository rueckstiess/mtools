from .base_filter import BaseFilter


class TableScanFilter(BaseFilter):
    """
    TableScanFilter class.

    ``--scan`` accepts a line when nscanned > 10000 and
    nscanned / nreturned > 100. ``--queryratio RATIO`` accepts a line when
    docsExamined / nreturned is greater than RATIO. nreturned of 0 is
    treated as 1 so the ratio stays defined.
    """

    filterArgs = [
        ('--scan', {
            'action': 'store_true',
            'help': ('only output lines which have poor index usage '
                     '(nscanned>10000 and ratio of nscanned to '
                     'nreturned>100); to see confirmed collection scans, '
                     'use --planSummary COLLSCAN.')
            }),
        ('--queryratio', {
            'action': 'store',
            'type': float,
            'metavar': 'RATIO',
            'help': ('only output lines where docsExamined / nreturned '
                     'is greater than RATIO. nreturned of 0 is treated '
                     'as 1. Lines that have no docsExamined use '
                     'nscanned (keysExamined).')
            })
        ]

    def __init__(self, mlogfilter):
        BaseFilter.__init__(self, mlogfilter)
        args = self.mlogfilter.args
        self.scan = bool(args.get('scan'))
        self.queryratio = args.get('queryratio')
        self.active = self.scan or self.queryratio is not None

    def accept(self, logevent):
        """
        Process line.

        Overwrite BaseFilter.accept() and return True if the provided
        logevent should be accepted (causing output), or False if not.
        """
        if self.scan and not self._exceeds(
                logevent.nscanned, logevent.nreturned, 100, 10000):
            return False
        if self.queryratio is not None:
            examined = logevent.nscannedObjects
            if examined is None:
                examined = logevent.nscanned
            returned = logevent.nreturned
            if not self._exceeds(examined, returned, self.queryratio):
                return False
        return self.active

    @staticmethod
    def _exceeds(examined, returned, ratio, minimum=None):
        """Return True when examined/returned is above ratio.

        ``minimum`` is an optional exclusive lower bound on ``examined``,
        used by ``--scan``. A returned count of 0 is treated as 1.
        """
        if examined is None or returned is None:
            return False
        if minimum is not None and not examined > minimum:
            return False
        if returned == 0:
            returned = 1
        return examined / returned > ratio
