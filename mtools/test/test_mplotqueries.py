from mtools.mplotqueries.mplotqueries import MPlotQueriesTool
import mtools

import os
import sys
import tempfile


class TestMPlotQueries(object):
    """ This class tests functionality around the mplotqueries tool. """

    def setup(self):
        """ start up method to init log file path. """
        self.logfile_path = os.path.join(os.path.dirname(mtools.__file__), 'test/logfiles/', 'mongos.log')

    def init_tool(self):
        """
        we need to setup tool after patching stdin
        """
        self.tool = MPlotQueriesTool()

    def test_from_stdin(self):
        """
        test mplotqueries with stdin
        """
        tmp = sys.stdin
        fn = tempfile.mktemp(suffix=".png")
        try:
            sys.stdin = PMock(open(self.logfile_path, 'r'), name="<stdin>", isatty=lambda: False)
            self.init_tool()
            self.tool.run(' --type event --output-file %s ' % fn)

            output = sys.stdout.getvalue()
            lines = output.splitlines()
            assert any(map(lambda line: 'EVENT plot' in line, lines))
        finally:
            sys.stdin = tmp
            try:
                os.remove(fn)
            except OSError:
                pass

    def test_from_file(self):
        """
        test mplotqueries with file
        """
        tmp = sys.stdin
        fn = tempfile.mktemp(suffix=".png")
        try:
            # sys.stdin = PMock(open(self.logfile_path, 'r'), isatty=lambda: True)
            sys.stdin = open(self.logfile_path, 'r')
            self.init_tool()
            # self.tool.is_stdin = True
            self.tool.run(' --type event --output-file %s %s' %(tempfile.mktemp(".png"),self.logfile_path))

            output = sys.stdout.getvalue()
            lines = output.splitlines()
            assert any(map(lambda line: 'EVENT plot' in line, lines))

        finally:
            sys.stdin = tmp
            try:
                os.remove(fn)
            except OSError:
                pass


class PMock(object):
    """Poor Man's Mock."""

    def __init__(self, obj, **kwoverrides):
        """create PMock."""
        super(PMock, self).__init__()
        #Set attribute.
        self._obj = obj
        self._overrides = kwoverrides

    def __getattr__(self, attrib):
        """
         first check override other wise delegate to obj
        """
        if attrib in self._overrides:
            return self._overrides[attrib]
        return getattr(self._obj, attrib)
