from base_filter import BaseFilter

class TableScanFilter(BaseFilter):
    """ accepts only if the line contains a nscanned:[0-9] nreturned:[0-9] where the ratio of nscanned:nreturned is > 100 and nscanned > 10000
    """
    filterArgs = [
        ('--scan', {'action':'store_true', 'help':'only output lines which appear to be table scans (if nscanned>10000 and ratio of nscanned to nreturned>100)'})
    ]

    def __init__(self, commandLineArgs):
        BaseFilter.__init__(self, commandLineArgs)
        if 'scan' in self.commandLineArgs:
            self.active = self.commandLineArgs['scan']

    def accept(self, logline):

        ns = logline.nscanned
        nr = logline.nreturned

        if ns != None and nr != None:
            if nr == 0:
                # avoid division by 0 errors
                nr = 1
            return (ns > 10000 and ns/nr > 100)

        return False
