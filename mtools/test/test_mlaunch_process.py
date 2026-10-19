from pymongo.errors import ConnectionFailure

from mtools.mlaunch.mlaunch import MLaunchTool, shutdown_host, wait_for_host
from mtools.mlaunch.process import ProcessMixin


def test_process_methods_stay_on_mlaunch():
    assert issubclass(MLaunchTool, ProcessMixin)
    for name in ('stop', 'start', 'kill', 'restart', 'is_running', 'wait_for',
                 '_start_on_ports', '_get_processes', '_get_last_error_log'):
        assert callable(getattr(MLaunchTool, name))
    assert callable(wait_for_host)
    assert callable(shutdown_host)


def test_wait_for_no_ports_returns_empty():
    tool = MLaunchTool.__new__(MLaunchTool)
    tool.args = {'verbose': False}
    tool.ssl_pymongo_options = {}
    tool.tls_pymongo_options = {}
    assert tool.wait_for([]) == ()


def test_is_running_is_false_when_the_node_is_down():
    tool = MLaunchTool.__new__(MLaunchTool)

    def client(*args, **kwargs):
        raise ConnectionFailure('down')

    tool.client = client
    tool._node_address = lambda port: 'localhost:%s' % port
    assert tool.is_running(27017) is False


def test_restart_stops_then_starts():
    tool = MLaunchTool.__new__(MLaunchTool)
    order = []
    tool._get_processes = lambda: {}
    tool.stop = lambda: order.append('stop')
    tool.start = lambda: order.append('start')
    tool.restart()
    assert order == ['stop', 'start']
