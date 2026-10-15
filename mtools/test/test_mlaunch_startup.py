import json

from mtools.mlaunch.mlaunch import MLaunchTool, _normalize_command


def test_normalize_command_collapses_spaces_outside_quotes():
    command = (
        '"mongod" --bind_ip_all --ipv6 --replSet replset '
        '--dbpath "/Users/tap1r/tmp/v9-rs/replset/rs1/db" '
        '--logpath "/Users/tap1r/tmp/v9-rs/replset/rs1/mongod.log" '
        '--port 27017  --keyFile "/Users/tap1r/tmp/v9-rs/keyfile"  '
        '--wiredTigerCacheSizeGB 1 '
    )
    normalized = _normalize_command(command)
    assert '  ' not in normalized
    assert not normalized.endswith(' ')
    assert '--port 27017 --keyFile' in normalized
    assert ('--keyFile "/Users/tap1r/tmp/v9-rs/keyfile" '
            '--wiredTigerCacheSizeGB 1') in normalized


def test_normalize_command_keeps_spaces_inside_quotes():
    command = '--dbpath "/Users/bobby tables/db"  --logpath "/tmp/a.log"'
    assert _normalize_command(command) == (
        '--dbpath "/Users/bobby tables/db" --logpath "/tmp/a.log"')


def test_normalize_command_keeps_empty_windows_quotes():
    command = 'start /b ""  "mongod.exe" --port 27017 '
    assert _normalize_command(command) == (
        'start /b "" "mongod.exe" --port 27017')


def test_store_parameters_pretty_prints_and_normalizes(tmp_path):
    tool = MLaunchTool(test=True)
    tool.dir = str(tmp_path)
    tool.args = {'command': 'init'}
    tool.unknown_args = []
    original = ('"mongod" --port 27017  --keyFile "/tmp/key file"  '
                '--wiredTigerCacheSizeGB 1 ')
    tool.startup_info = {'27017': original}

    tool._store_parameters()

    text = (tmp_path / '.mlaunch_startup').read_text()
    assert text.endswith('\n')
    assert '\n  "protocol_version": 2,' in text
    loaded = json.loads(text)
    stored = loaded['startup_info']['27017']
    assert stored == ('"mongod" --port 27017 --keyFile "/tmp/key file" '
                      '--wiredTigerCacheSizeGB 1')
    assert '  ' not in stored
    assert tool.startup_info['27017'] == original
