"""Server version parsing for mlaunch; no mongod needed."""

from unittest import mock

import pytest
from packaging import version

from mtools.mlaunch import mlaunch
from mtools.mlaunch.mlaunch import MLaunchTool, _extract_server_version


@pytest.mark.parametrize('text, expected', [
    ('db version v7.0.14', '7.0.14'),
    ('db version v8.0.0-rc2', '8.0.0'),
    ('db version v8.3.0-alpha6-261-g43a317d-patch', '8.3.0'),
    ('mongos version v6.0.3\nBuild Info: {"version": "6.0.3"}', '6.0.3'),
])
def test_extract_server_version(text, expected):
    result = _extract_server_version(text)
    assert result == expected
    assert str(version.parse(result)) == expected


@pytest.mark.parametrize('text', ['', None, 'garbage', 'db version vX.Y'])
def test_extract_server_version_no_match(text):
    assert _extract_server_version(text) is None


@pytest.mark.parametrize('first_line, expected', [
    (b'db version v7.0.14', '7.0.14'),
    (b'db version v8.0.0-rc2', '8.0.0'),
    (b'db version v8.3.0-alpha6-261-g43a317d-patch', '8.3.0'),
    (b'something unexpected', '0.0.0'),
])
def test_get_mongod_version(first_line, expected, capsys):
    tool = MLaunchTool(test=True)
    tool.args = {}
    out = first_line + b'\nBuild Info: {\n    "version": "x"\n}\n'
    with mock.patch.object(mlaunch, 'check_mongo_server_output',
                           return_value=out) as check:
        result = tool.getMongoDVersion()
    check.assert_called_once()
    assert result == expected
    version.parse(result)
    assert 'Detected mongod version: %s' % expected in capsys.readouterr().out
