class BaseFilter(object):
    """
    Base Filter class.

    All filters need to derive from it and implement their version of
    filterArgs, accept, and optionally skipRemaining.

    filterArgs needs to be a list of tuples with 2 elements each. The
    first tuple element is the filter argument, e.g. --xyz. The second
    element of the tuple is a dictionary that gets passed to the
    ArgumentParser object's add_argument method.
    """

    filterArgs = []

    def __init__(self, mlogfilter):
        """
        Constructor.

        Save command line arguments and set active to False by default.
        """
        self.mlogfilter = mlogfilter

        # filters need to actively set this flag to true
        self.active = False

    def setup(self):
        """
        Setup function.

        Hook to setup anything necessary for the filter before actually
        going through logevents. overwrite in subclass if setup is required.
        """
        pass

    def accept(self, logevent):
        """
        Process line.

        Overwrite this method in subclass and return True if the provided
        logevent should be accepted (causing output), or False if not.
        """
        return True

    def skipRemaining(self):
        """
        Skip remaining lines.

        Overwrite this method in sublcass and return True if all lines
        from here to the end of the file should be rejected (no output).
        """
        return False
