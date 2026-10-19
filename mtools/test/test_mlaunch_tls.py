import pytest

from mtools.mlaunch.mlaunch import MLaunchTool
from mtools.mlaunch.tls_args import TlsArgsMixin
from mtools.util.cmdlinetool import BaseCmdLineTool


def test_tls_methods_stay_on_mlaunch():
    assert issubclass(MLaunchTool, TlsArgsMixin)
    for name in ('_get_ssl_server_args', '_get_ssl_pymongo_options',
                 '_get_tls_server_args', '_get_tls_pymongo_options'):
        assert callable(getattr(MLaunchTool, name))


def _parsed_tool(arg_str, tmp_path):
    """Parse init arguments without starting mongod."""
    tool = MLaunchTool.__new__(MLaunchTool)
    BaseCmdLineTool.__init__(tool)
    tool.current_version = '6.0.0'
    tool.init = lambda: None
    tool.run('%s --dir %s' % (arg_str, tmp_path))
    return tool


@pytest.mark.parametrize('mode,prefix', [
    ('requireTLS', 'tls'),
    ('preferTLS', 'tls'),
    ('requireSSL', 'ssl'),
    ('preferSSL', 'ssl'),
    ('disabled', 'tls'),
    ('disabled', 'ssl'),
])
def test_security_mode_argv_and_pymongo(tmp_path, mode, prefix):
    flag = '--%sMode' % prefix
    tool = _parsed_tool('init --single %s %s' % (flag, mode), tmp_path)
    argv = getattr(tool, '_get_%s_server_args' % prefix)()
    options = getattr(tool, '_get_%s_pymongo_options' % prefix)(tool.args)
    assert argv == ' --%sMode "%s"' % (prefix, mode)
    expected = {'tls': True}
    if prefix == 'ssl':
        expected['tlsAllowInvalidCertificates'] = True
    assert options == expected
    other = 'ssl' if prefix == 'tls' else 'tls'
    assert getattr(tool, '_get_%s_server_args' % other)() == ''
    assert getattr(tool, '_get_%s_pymongo_options' % other)(tool.args) == {}


def test_tls_file_options_keep_their_pymongo_names(tmp_path):
    ca = tmp_path / 'ca.pem'
    client = tmp_path / 'client.pem'
    ca.write_text('ca\n')
    client.write_text('client\n')
    tool = _parsed_tool(
        'init --single --tlsMode requireTLS --tlsCAFile %s '
        '--tlsClientCertificateKeyFile %s' % (ca, client), tmp_path)
    assert ' --tlsMode "requireTLS"' in tool._get_tls_server_args()
    assert ' --tlsCAFile "%s"' % ca in tool._get_tls_server_args()
    assert 'tlsClientCertificateKeyFile' not in tool._get_tls_server_args()
    assert tool._get_tls_pymongo_options(tool.args) == {
        'tls': True,
        'tlsCAFile': str(ca),
        'tlsCertificateKeyFile': str(client),
    }


def test_ssl_file_options_use_the_tls_pymongo_names(tmp_path):
    ca = tmp_path / 'ca.pem'
    client = tmp_path / 'client.pem'
    ca.write_text('ca\n')
    client.write_text('client\n')
    tool = _parsed_tool(
        'init --single --sslMode requireSSL --sslCAFile %s '
        '--sslClientCertificate %s' % (ca, client), tmp_path)
    assert ' --sslMode "requireSSL"' in tool._get_ssl_server_args()
    assert ' --sslCAFile "%s"' % ca in tool._get_ssl_server_args()
    assert tool._get_ssl_pymongo_options(tool.args) == {
        'tls': True,
        'tlsAllowInvalidCertificates': True,
        'tlsCAFile': str(ca),
        'tlsCertificateKeyFile': str(client),
    }
