from mtools.mlaunch.mlaunch import MLaunchTool
from mtools.mlaunch.topology import TopologyMixin


def test_topology_methods_stay_on_mlaunch():
    assert issubclass(MLaunchTool, TopologyMixin)
    for name in ('_construct_cmdlines', '_construct_sharded',
                 '_construct_replset', '_construct_config',
                 '_construct_single', '_construct_mongod',
                 '_construct_mongos', '_initiate_replset', '_add_user'):
        assert callable(getattr(MLaunchTool, name))


def test_construct_mongod_stores_a_command_without_starting(tmp_path):
    tool = MLaunchTool.__new__(MLaunchTool)
    tool.args = {
        'auth': False,
        'hostname': 'localhost',
        'sharded': None,
        'replicaset': False,
        'binarypath': None,
    }
    tool.unknown_args = []
    tool.current_version = '4.0.0'
    tool.startup_info = {}
    tool.dir = str(tmp_path)
    tool._get_ssl_server_args = lambda: ''
    tool._get_tls_server_args = lambda: ''
    tool._macos_fork_unsupported = lambda version=None: False
    # No mongod on the test host: accept no extra server arguments.
    tool._filter_valid_arguments = lambda arguments, binary='mongod', **kw: ''
    dbpath = tmp_path / 'db'
    logpath = tmp_path / 'mongod.log'
    tool._construct_mongod(str(dbpath), str(logpath), 27017)
    command = tool.startup_info['27017']
    assert '--port 27017' in command
    assert '--dbpath "%s"' % dbpath in command
    assert '--logpath "%s"' % logpath in command
    assert '--fork' in command


def test_construct_cmdlines_still_chooses_single(tmp_path):
    tool = MLaunchTool.__new__(MLaunchTool)
    tool.args = {'sharded': None, 'single': True, 'replicaset': False,
                 'port': 27017}
    tool.dir = str(tmp_path)
    called = {}

    def construct_single(basedir, port, name=None, extra=''):
        called['basedir'] = basedir
        called['port'] = port

    tool._construct_single = construct_single
    tool._construct_cmdlines()
    assert called == {'basedir': str(tmp_path), 'port': 27017}
