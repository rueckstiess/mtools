from base_filter import BaseFilter

class FastFilter(BaseFilter):
    """ accepts only lines that have a duration that is shorter than the specified
        parameter in ms.
    """
    filterArgs = [
        ('--fast', {'action':'store', 'nargs':'?', 'default':False, 'type':int, 'help':'only output lines with query times shorter than FAST ms (default 1000)'})
    ]

    def __init__(self, commandLineArgs):
        BaseFilter.__init__(self, commandLineArgs)
        if 'fast' in self.commandLineArgs and self.commandLineArgs['fast'] != False:
            self.active = True
            if self.commandLineArgs['fast'] == None:
                self.fastms = 1000
            else:
                self.fastms = self.commandLineArgs['fast']

    def accept(self, logline):
        if self.active and logline.duration:
            return logline.duration <= self.fastms
        return False
