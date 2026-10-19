"""Default WiredTiger cache size for mongod."""

from mtools.mlaunch.mlaunch import MLaunchTool
from mtools.util.cmdlinetool import BaseCmdLineTool


def _tool():
    """A command builder that does not run mongod --help."""
    tool = MLaunchTool.__new__(MLaunchTool)
    BaseCmdLineTool.__init__(tool)
    tool.current_version = '7.0.0'
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
    tool._filter_valid_arguments = _accept_cache_flag
    return tool


def _accept_cache_flag(arguments, binary='mongod', config=False, owned=None):
    """Report the GB cache flag as supported, and keep user arguments."""
    if arguments == ['--wiredTigerCacheSizeGB']:
        return '--wiredTigerCacheSizeGB'
    return ' '.join(arguments)


def _mongod_command(tool):
    tool._construct_mongod('/tmp/db', '/tmp/mongod.log', 27017)
    return tool.startup_info['27017']


def test_default_cache_is_half_a_gigabyte():
    command = _mongod_command(_tool())
    assert '--wiredTigerCacheSizeGB 0.5' in command
    assert '--wiredTigerCacheSizeGB 1' not in command


def test_cache_default_is_omitted_when_the_binary_lacks_the_flag():
    tool = _tool()
    tool._filter_valid_arguments = lambda *args, **kwargs: ''
    command = _mongod_command(tool)
    assert '--wiredTigerCacheSizeGB' not in command


def test_user_cache_size_is_kept():
    tool = _tool()
    tool.unknown_args = ['--wiredTigerCacheSizeGB', '2']
    command = _mongod_command(tool)
    assert command.count('--wiredTigerCacheSizeGB') == 1
    assert '--wiredTigerCacheSizeGB 2' in command
    assert '0.5' not in command


def test_cache_percent_suppresses_the_gb_default():
    tool = _tool()
    tool.unknown_args = ['--wiredTigerCacheSizePct', '0.1']
    command = _mongod_command(tool)
    assert '--wiredTigerCacheSizePct 0.1' in command
    assert '--wiredTigerCacheSizeGB' not in command


def test_mongos_does_not_receive_a_cache_size():
    tool = _tool()
    tool._construct_mongos('/tmp/mongos.log', 27017, 'localhost:27019')
    command = tool.startup_info['27017']
    assert '--wiredTigerCacheSizeGB' not in command
    assert '--wiredTigerCacheSizePct' not in command
