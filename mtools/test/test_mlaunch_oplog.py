"""Oplog size passthrough and the one-hour retention default."""

from mtools.mlaunch.mlaunch import MLaunchTool
from mtools.util.cmdlinetool import BaseCmdLineTool


def _tool(version):
    """A mongod command builder that does not run mongod --help."""
    tool = MLaunchTool.__new__(MLaunchTool)
    BaseCmdLineTool.__init__(tool)
    tool.current_version = version
    tool.args = {
        'auth': False,
        'hostname': 'localhost',
        'sharded': None,
        'replicaset': False,
        'binarypath': None,
        'verbose': False,
    }
    tool.unknown_args = []
    tool.startup_info = {}
    tool.ssl_server_args = ''
    tool.tls_server_args = ''
    tool._filter_valid_arguments = lambda *args, **kwargs: ''
    return tool


def _mongod_command(tool):
    tool._construct_mongod('/tmp/db', '/tmp/mongod.log', 27017)
    return tool.startup_info['27017']


def test_config_server_strip_keeps_oplog_size():
    assert '--oplogSize' not in MLaunchTool.UNSUPPORTED_CONFIG_ARGS


def test_default_retention_is_one_hour_on_4_4():
    command = _mongod_command(_tool('4.4.0'))
    assert '--oplogMinRetentionHours 1' in command


def test_default_retention_is_one_hour_when_version_is_unknown():
    command = _mongod_command(_tool('0.0.0'))
    assert '--oplogMinRetentionHours 1' in command


def test_retention_is_omitted_before_4_4():
    command = _mongod_command(_tool('4.2.14'))
    assert '--oplogMinRetentionHours' not in command


def test_user_retention_is_kept():
    tool = _tool('7.0.0')
    tool.unknown_args = ['--oplogMinRetentionHours', '2']
    tool._filter_valid_arguments = (
        lambda *args, **kwargs: '--oplogMinRetentionHours "2"')
    command = _mongod_command(tool)
    assert command.count('--oplogMinRetentionHours') == 1
    assert '--oplogMinRetentionHours "2"' in command


def test_mongos_does_not_receive_the_retention_default():
    tool = _tool('7.0.0')
    tool._construct_mongos('/tmp/mongos.log', 27017, 'localhost:27019')
    command = tool.startup_info['27017']
    assert '--oplogMinRetentionHours' not in command
    assert '--oplogSize' not in command
