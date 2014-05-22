class BaseSection(object):
    """ BaseSection class. All sections need to derive from it and add
        their arguments to the mloginfo.argparser object and determine if they are
        active.
    """

    filterArgs = []
    name = 'base'
    description = 'description of this section'
    

    def __init__(self, mloginfo):
        """ constructor. save command line arguments and set active to False
            by default. 
        """
        # mloginfo object, use it to get access to argparser and other class variables
        self.mloginfo = mloginfo
        
    
    def _add_subparser_arguments(self, subparser):
        """ add additional subparser arguments in this method if required. """
        pass

    
    def run(self):
        pass

