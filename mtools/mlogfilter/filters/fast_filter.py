from .base_filter import BaseFilter


class FastFilter(BaseFilter):
    """
    FastFilter class.

    Accept only lines that have a duration that is shorter than the specified
    parameter in ms.
    """

    filterArgs = [
        ('--fast', {'action': 'store', 'nargs': '?', 'default': False,
                    'type': int,
                    'help': ('only output lines with query times shorter '
                             'than FAST ms (default 1000)')})
        ]

    def __init__(self, mlogfilter):
        BaseFilter.__init__(self, mlogfilter)
        if ('fast' in self.mlogfilter.args and
                self.mlogfilter.args['fast'] is not False):
            self.active = True
            if self.mlogfilter.args['fast'] is None:
                self.fastms = 1000
            else:
                self.fastms = self.mlogfilter.args['fast']

    def accept(self, logevent):
        """
        Process line.

        Overwrite BaseFilter.accept() and return True if the provided
        logevent should be accepted (causing output), or False if not.
        """
        if self.active and logevent.duration is not None:
            return logevent.duration <= self.fastms
        return False
