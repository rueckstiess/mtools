"""``--config`` count-or-file and ``--verbose`` forwarded to the server."""

import re

from mtools.mlaunch.mlaunch import MLaunchTool
from mtools.util.cmdlinetool import BaseCmdLineTool


def _parsed_tool(arg_str, tmp_path):
    """Parse init arguments without starting mongod."""
    tool = MLaunchTool.__new__(MLaunchTool)
    BaseCmdLineTool.__init__(tool)
    tool.current_version = '6.0.0'
    tool.init = lambda: None
    tool.run('%s --dir %s' % (arg_str, tmp_path))
    tool.startup_info = {}
    tool._filter_valid_arguments = lambda *args, **kwargs: ''
    return tool


def _init_parser(tool):
    return tool.argparser._subparsers._group_actions[0].choices['init']


def test_config_count_stays_an_int(tmp_path):
    tool = _parsed_tool('init --sharded 2 --replicaset --config 3', tmp_path)
    assert tool.args['config'] == 3
    assert tool.args['server_config'] is None


def test_config_file_keeps_the_default_count(tmp_path):
    tool = _parsed_tool('init --single --config mongod.conf', tmp_path)
    assert tool.args['config'] == 1
    assert tool.args['server_config'] == 'mongod.conf'

    equals = _parsed_tool('init --single --config=mongod.conf', tmp_path)
    assert equals.args['config'] == 1
    assert equals.args['server_config'] == 'mongod.conf'


def test_config_last_value_wins(tmp_path):
    file_then_count = _parsed_tool(
        'init --single --config mongod.conf --config 3', tmp_path)
    assert file_then_count.args['config'] == 3
    assert file_then_count.args['server_config'] is None

    count_then_file = _parsed_tool(
        'init --single --config 3 --config mongod.conf', tmp_path)
    assert count_then_file.args['config'] == 1
    assert count_then_file.args['server_config'] == 'mongod.conf'


def test_config_file_is_on_mongod_and_mongos(tmp_path):
    tool = _parsed_tool('init --single --config mongod.conf', tmp_path)
    tool._construct_mongod('/tmp/db', '/tmp/mongod.log', 27017)
    tool._construct_mongos('/tmp/mongos.log', 27018, 'localhost:27019')
    assert '--config "mongod.conf"' in tool.startup_info['27017']
    assert '--config "mongod.conf"' in tool.startup_info['27018']


def test_numeric_config_is_not_forwarded(tmp_path):
    tool = _parsed_tool('init --single --config 1', tmp_path)
    tool._construct_mongod('/tmp/db', '/tmp/mongod.log', 27017)
    assert '--config' not in tool.startup_info['27017']


def test_verbose_adds_one_v(tmp_path):
    tool = _parsed_tool('init --single --verbose', tmp_path)
    tool._construct_mongod('/tmp/db', '/tmp/mongod.log', 27017)
    command = tool.startup_info['27017']
    assert re.search(r'(^|\s)-v(\s|$)', command)
    assert '--verbose' not in command


def test_existing_verbosity_is_not_repeated(tmp_path):
    tool = _parsed_tool('init --single --verbose -vv', tmp_path)
    assert tool.unknown_args == ['-vv']
    assert tool._forwarded_server_args() == ''


def test_passthrough_example_is_not_config(tmp_path):
    tool = _parsed_tool('init --single', tmp_path)
    commands = tool.argparser._action_groups[0].description
    assert 'or --slowms.' in commands
    assert 'or --config.' not in commands
    assert 'or --slowms.' in _init_parser(tool).description
