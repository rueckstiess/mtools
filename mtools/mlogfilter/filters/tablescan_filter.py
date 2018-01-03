from .base_filter import BaseFilter


class TableScanFilter(BaseFilter):
    """
    TableScanFilter class.

    Accept only if the line contains a nscanned:[0-9] nreturned:[0-9] where
    the ratio of nscanned:nreturned is > 100 and nscanned > 10000.
    """

    filterArgs = [
        ('--scan', {
            'action': 'store_true',
            'help': ('only output lines which have poor index usage '
                     '(nscanned>10000 and ratio of nscanned to '
                     'nreturned>100); to see confirmed collection scans, '
                     'use --planSummary COLLSCAN.')
            })
        ]

    def __init__(self, mlogfilter):
        BaseFilter.__init__(self, mlogfilter)

        if 'scan' in self.mlogfilter.args:
            self.active = self.mlogfilter.args['scan']

    def accept(self, logevent):
        """
        Process line.

        Overwrite BaseFilter.accept() and return True if the provided
        logevent should be accepted (causing output), or False if not.
        """
        ns = logevent.nscanned
        nr = logevent.nreturned

        if ns is not None and nr is not None:
            if nr == 0:
                # avoid division by 0 errors
                nr = 1
            return (ns > 10000 and ns / nr > 100)

        return False
