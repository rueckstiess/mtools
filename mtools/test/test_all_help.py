import io
from operator import truediv
import sys

import pytest

from mtools.test import all_tools


@pytest.fixture(scope="function", autouse=True)
def patch_io(monkeypatch, capsys):
    monkeypatch.setattr('sys.stdin', io.StringIO('my input'))
    sys.stdin.name = 'foo'
    sys.stdin.isatty = lambda: True


@all_tools
def check_help(tool_cls):
    """
    Check that all command line tools have a --help option that explains the
    usage.

    As per argparse default, this help text always starts with `usage:`.
    """
    tool = tool_cls()

    try:
        tool.run("--help")

    except SystemExit:
        if not hasattr(sys.stdout, "getvalue"):
            raise Exception('stdout not captured in test.')
        output = sys.stdout.getvalue().strip()
        assert output.startswith('usage:')


@all_tools
def check_version(tool_cls):
    """
    Check that all command line tools have a --version option that returns
    the current version.
    """
    tool = tool_cls()

    try:
        tool.run("--version")

    except SystemExit as ex:
        print(ex)
        if not hasattr(sys.stdout, "getvalue"):
            raise Exception('stdout not captured in test.')

        # argparse's --version outputs to stderr, which can't be captured
        # with pytest. Therefore just checking that the scripts run and not
        # output anything to stdout --- FIXED to stderr https://bugs.python.org/issue18920
        #output = sys.stdout.getvalue().strip()
        #assert len(output) == 0


def test_help():
    check_help()


def test_version():
    check_version()