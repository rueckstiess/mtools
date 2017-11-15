from base_filter import BaseFilter


class SlowFilter(BaseFilter):
    """
    Accepts only lines that have a duration that is longer than the specified
    parameter in ms (default 1000).
    """
    filterArgs = [
        ('--slow', {'action': 'store', 'nargs': '?', 'default': False,
                    'type': int, 'help': ('only output lines with query times '
                                          'longer than SLOW ms '
                                          '(default 1000)')})
        ]

    def __init__(self, mlogfilter):
        BaseFilter.__init__(self, mlogfilter)

        if ('slow' in self.mlogfilter.args and
                self.mlogfilter.args['slow'] is not False):
            self.active = True
            if self.mlogfilter.args['slow'] is None:
                self.slowms = 1000
            else:
                self.slowms = self.mlogfilter.args['slow']

    def accept(self, logevent):
        if logevent.duration is not None:
            return logevent.duration >= self.slowms
        return False
