from .base_filter import BaseFilter


class QueryRatioFilter(BaseFilter):
    """
    QueryRatioFilter class.

    Accept only if the line contains a nscannedObjects:[0-9] nreturned:[0-9] where
    the ratio of nscannedObjects:nreturned is higher than the given argument (default 1000).
    """

    filterArgs = [
        ('--queryratio', {
            'action': 'store',
            'nargs': '?',
            'default': 1000,
            'type': int,
            'help': ('only output lines which have a certain query target ratio '
                     '(nscannedObjects (docsExamined) to nreturned) (default: 1000).')
            })
        ]

    def __init__(self, mlogfilter):
        BaseFilter.__init__(self, mlogfilter)

        if 'queryratio' in self.mlogfilter.args:
            self.active = True
            if self.mlogfilter.args['queryratio'] is None:
                self.queryratio = 1000
            else:
                self.queryratio = self.mlogfilter.args['queryratio']

    def accept(self, logevent):
        """
        Process line.

        Overwrite BaseFilter.accept() and return True if the provided
        logevent should be accepted (causing output), or False if not.
        """
        nscannedObjects = logevent.nscannedObjects
        nreturned = logevent.nreturned

        if nscannedObjects is not None and nreturned is not None:
            if nreturned == 0:
                # avoid division by 0 errors
                nreturned = 1
            return (nscannedObjects / nreturned > self.queryratio)

        return False
