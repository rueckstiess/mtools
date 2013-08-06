from base_filter import BaseFilter

class SlowFilter(BaseFilter):
    """ accepts only lines that have a duration that is longer than the specified 
        parameter in ms (default 1000).
    """
    filterArgs = [
        ('--slow', {'action':'store', 'nargs':'?', 'default':False, 'type':int, 'help':'only output lines with query times longer than SLOW ms (default 1000)'})
    ]

    def __init__(self, commandLineArgs):
        BaseFilter.__init__(self, commandLineArgs)
        if 'slow' in self.commandLineArgs and self.commandLineArgs['slow'] != False:
            self.active = True
            if self.commandLineArgs['slow'] == None:
                self.slowms = 1000
            else:
                self.slowms = self.commandLineArgs['slow']

    def accept(self, logline):
        if logline.duration:
            return logline.duration >= self.slowms
        return False