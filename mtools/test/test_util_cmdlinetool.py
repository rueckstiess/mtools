import argparse
import importlib
import io
import os
import sys
import warnings

import pytest

import mtools
from mtools.util.cmdlinetool import InputSourceAction, LogFileTool
from mtools.util.logfile import LogFile


def test_building_the_parser_does_not_use_filetype(monkeypatch):
    """Parser setup opens log files without argparse.FileType."""
    monkeypatch.setattr('sys.stdin', io.StringIO(''))
    sys.stdin.name = 'fixture'
    sys.stdin.isatty = lambda: True
    import mtools.mlogfilter.filters.mask_filter as mask_filter
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter('always', PendingDeprecationWarning)
        importlib.reload(mask_filter)
        LogFileTool()
    messages = [str(item.message) for item in caught]
    assert not any('FileType' in message for message in messages)


def test_opens_a_logfile():
    """A logfile path becomes a LogFile."""
    path = os.path.join(os.path.dirname(mtools.__file__),
                        'test', 'logfiles', 'year_rollover.log')
    source = InputSourceAction('rb')(path)
    try:
        assert isinstance(source, LogFile)
        assert source.name == path
        assert source.start is not None
    finally:
        source.filehandle.close()


def test_missing_file_is_rejected():
    """A path that is not a log or a profile URI is an argument error."""
    with pytest.raises(argparse.ArgumentTypeError):
        InputSourceAction('rb')('/no/such/mtools-log.log')


def test_dash_reads_stdin(monkeypatch):
    """A dash selects binary stdin."""
    buffer = io.BytesIO(b'')
    buffer.name = '<stdin>'
    stdin = io.BytesIO(b'')
    stdin.buffer = buffer
    monkeypatch.setattr(sys, 'stdin', stdin)
    source = InputSourceAction('rb')('-')
    assert isinstance(source, LogFile)
    assert source.from_stdin
    assert source.name == '<stdin>'
