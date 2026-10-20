import pytest

from mtools.mlaunch.arguments import ArgumentsMixin
from mtools.mlaunch.mlaunch import MLaunchTool
from mtools.util.cmdlinetool import BaseCmdLineTool


def test_argument_parser_stays_on_mlaunch():
    assert issubclass(MLaunchTool, ArgumentsMixin)
    assert callable(getattr(MLaunchTool, '_build_argument_parser'))


def _tool():
    tool = MLaunchTool.__new__(MLaunchTool)
    BaseCmdLineTool.__init__(tool)
    tool.current_version = '6.0.0'
    tool.init = lambda: None
    return tool


def test_run_parses_single_and_port(tmp_path):
    tool = _tool()
    tool.run('init --single --port 27018 --dir %s' % tmp_path)
    assert tool.args['command'] == 'init'
    assert tool.args['single'] is True
    assert tool.args['port'] == 27018
    assert tool.args['arbiter'] is False
    assert tool.dir == str(tmp_path)


def test_leading_dash_arguments_default_to_init(tmp_path):
    tool = _tool()
    tool.run('--single --port 27019 --dir %s' % tmp_path)
    assert tool.args['command'] == 'init'
    assert tool.args['port'] == 27019


def test_single_arbiter_is_rejected(tmp_path):
    tool = _tool()
    with pytest.raises(SystemExit):
        tool.run('init --single --arbiter --dir %s' % tmp_path)


def test_tls_and_ssl_modes_still_parse(tmp_path):
    tool = _tool()
    tool.run('init --single --tlsMode requireTLS --sslMode preferSSL '
             '--dir %s' % tmp_path)
    assert tool.args['tlsMode'] == 'requireTLS'
    assert tool.args['sslMode'] == 'preferSSL'
