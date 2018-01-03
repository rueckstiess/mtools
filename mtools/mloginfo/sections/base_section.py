class BaseSection(object):
    """
    BaseSection class.

    All sections need to derive from it and add their arguments to the
    mloginfo.argparser object and determine if they are active.
    """

    filterArgs = []
    name = 'base'
    active = False

    def __init__(self, mloginfo):
        """Save command line arguments and set active to False by default."""
        # mloginfo object, use it to get access to argparser and other
        # class variables
        self.mloginfo = mloginfo

    def run(self):
        """Override this method in subclasses."""
        pass
