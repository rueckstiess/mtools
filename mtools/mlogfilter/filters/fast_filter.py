from base_filter import BaseFilter

class FastFilter(BaseFilter):
    """ accepts only lines that have a duration that is shorter than the specified
        parameter in ms.
    """
    filterArgs = [
        ('--fast', {'action':'store', 'nargs':'?', 'default':False, 'type':int, 'help':'only output lines with query times shorter than FAST ms (default 1000)'})
    ]

    def __init__(self, mlogfilter):
        BaseFilter.__init__(self, mlogfilter
            )
        if 'fast' in self.mlogfilter.args and self.mlogfilter.args['fast'] != False:
            self.active = True
            if self.mlogfilter.args['fast'] == None:
                self.fastms = 1000
            else:
                self.fastms = self.mlogfilter.args['fast']

    def accept(self, logevent):
        if self.active and logevent.duration != None:
            return logevent.duration <= self.fastms
        return False
