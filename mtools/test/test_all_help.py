import sys
from nose.tools import *
from mtools.test import all_tools
import time

@all_tools
def test_help(tool_cls):
    """ This tests if all command line tools have a `--help` option that explains the usage.
        As per argparse default, this help text always starts with `usage:`.
    """
    tool = tool_cls()
   
    try:
        tool.run("--help")

    except SystemExit as e:
        pass
        if not hasattr(sys.stdout, "getvalue"):
            raise Exception('stdout not captured in test.')
        output = sys.stdout.getvalue().strip()
        assert output.startswith('usage:')

