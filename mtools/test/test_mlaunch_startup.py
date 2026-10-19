import json
import os
import shutil
import subprocess
import sys

import pytest

from mtools.mlaunch.mlaunch import (
    MLaunchTool, _command_line_error, _normalize_command)


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


def test_normalize_command_keeps_escaped_quote_inside_double_quotes():
    command = 'mongod --setParameter "a=\\"x  y\\"   z"   --port 1'
    assert (_normalize_command(command) ==
            'mongod --setParameter "a=\\"x  y\\"   z" --port 1')


def test_normalize_command_keeps_no_break_space():
    command = 'mongod --dbpath /data/a\u00a0b  --port 1'
    assert (_normalize_command(command) ==
            'mongod --dbpath /data/a\u00a0b --port 1')


def _tool():
    tool = MLaunchTool(test=True)
    tool.args = {
        'auth': False,
        'hostname': 'localhost',
        'binarypath': None,
        'sharded': False,
        'replicaset': False,
        'verbose': False,
    }
    tool.unknown_args = []
    return tool


def test_filter_passes_options_the_help_text_used_to_hide():
    tool = _tool()
    result = tool._filter_valid_arguments(
        ['--verbose', '--config', 'mongod.conf',
         '--wiredTigerEngineConfigString', 'cache_size=1G',
         '--nopreallocj', '--foobar', '-vvv'],
        'mongod')
    assert result == (
        '--verbose --config "mongod.conf" '
        '--wiredTigerEngineConfigString "cache_size=1G" '
        '--nopreallocj --foobar -vvv')


def test_filter_passes_the_same_options_to_mongos():
    tool = _tool()
    result = tool._filter_valid_arguments(
        ['--wiredTigerCacheSizeGB', '1', '--storageEngine', 'wiredTiger',
         '--oplogSize', '19', '--slowms', '5'],
        'mongos')
    assert result == (
        '--wiredTigerCacheSizeGB "1" --storageEngine "wiredTiger" '
        '--oplogSize "19" --slowms "5"')


def test_cache_percent_suppresses_the_gb_default():
    tool = _tool()
    tool.unknown_args = ['--wiredTigerCacheSizePct', '0.5']
    tool._construct_mongod('/data/db', '/data/mongod.log', 27017)
    command = tool.startup_info['27017']
    assert '--wiredTigerCacheSizePct "0.5"' in command
    assert '--wiredTigerCacheSizeGB' not in command


def test_cache_gb_default_is_added_when_the_user_sets_neither():
    tool = _tool()
    tool.unknown_args = ['--slowms', '1000']
    tool._construct_mongod('/data/db', '/data/mongod.log', 27017)
    command = tool.startup_info['27017']
    assert '--wiredTigerCacheSizeGB 1' in command
    assert '--slowms "1000"' in command


@pytest.mark.skipif(os.name == 'nt', reason='Windows launch does not use --fork')
def test_fork_is_owned_only_when_the_command_includes_it(monkeypatch):
    tool = _tool()
    monkeypatch.setattr(sys, 'platform', 'darwin')
    tool.current_version = '9.0.4'
    assert '--fork' not in tool._owned_server_args('mongod')
    tool.current_version = '7.0.14'
    assert '--fork' in tool._owned_server_args('mongod')
    monkeypatch.setattr(sys, 'platform', 'linux')
    tool.current_version = '9.0.4'
    assert '--fork' in tool._owned_server_args('mongod')


def test_user_fork_stays_when_mlaunch_omits_it(monkeypatch, capsys):
    tool = _tool()
    monkeypatch.setattr(sys, 'platform', 'darwin')
    tool.current_version = '9.0.4'
    tool.unknown_args = ['--fork', '--slowms', '1000']
    tool._construct_mongod('/data/db', '/data/mongod.log', 27017)
    command = tool.startup_info['27017']
    assert command.count('--fork') == 1
    assert '--slowms "1000"' in command
    assert 'ignoring --fork' not in capsys.readouterr().out
    assert '--fork' not in tool._launch_argv(command)


def test_command_line_error_reads_the_parser_sentence():
    output = (
        '{"t":{"$date":"2026-10-19T00:00:00.000Z"},"s":"I",'
        '"msg":"Shuffling initializers"}\n'
        "Error parsing command line: unrecognised option '--nopreallocj'\n"
        "try 'mongod --help' for more information\n"
    )
    sentence = "Error parsing command line: unrecognised option '--nopreallocj'"
    assert _command_line_error(output) == sentence
    assert _command_line_error(output.encode('utf-8')) == sentence
    assert _command_line_error('') is None
    assert _command_line_error(None) is None
    assert _command_line_error('DBPathInUse: Unable to lock') is None


def _fail_launch(command, output):
    def fail(*args, **kwargs):
        raise subprocess.CalledProcessError(2, command, output=output)
    return fail


def test_start_on_ports_reports_a_command_line_error(monkeypatch, capsys):
    tool = _tool()
    capsys.readouterr()
    command = 'mongod --dbpath "/data/db" --port 27017 --notARealOption'
    tool.startup_info = {'27017': command}
    output = (
        "Error parsing command line: unrecognised option '--notARealOption'\n"
    )
    fail = _fail_launch(command, output)
    monkeypatch.setattr(tool, '_needs_python_detach', lambda command_str: False)
    monkeypatch.setattr('mtools.mlaunch.mlaunch.subprocess.check_output', fail)
    monkeypatch.setattr('mtools.mlaunch.mlaunch.subprocess.check_call', fail)

    with pytest.raises(SystemExit) as exc:
        tool._start_on_ports([27017])
    message = str(exc.value)
    assert message.startswith(
        "Error parsing command line: unrecognised option '--notARealOption'")
    assert 'tried to launch: %s' % command in message
    assert "can't start process" not in message
    assert capsys.readouterr().out == ''


def test_start_on_ports_keeps_other_startup_failures(monkeypatch):
    tool = _tool()
    command = ('mongod --dbpath "/data/db" '
               '--logpath "/tmp/no-such-mlaunch.log" --port 27017')
    tool.startup_info = {'27017': command}

    def fail(*args, **kwargs):
        raise subprocess.CalledProcessError(
            100, command,
            output='NonExistentPath: Data directory /data/db not found')

    monkeypatch.setattr(tool, '_needs_python_detach', lambda command_str: False)
    monkeypatch.setattr('mtools.mlaunch.mlaunch.subprocess.check_output', fail)
    monkeypatch.setattr('mtools.mlaunch.mlaunch.subprocess.check_call', fail)

    with pytest.raises(SystemExit) as exc:
        tool._start_on_ports([27017])
    message = str(exc.value)
    assert "can't start process, return code 100" in message
    assert command in message


@pytest.mark.skipif(shutil.which('mongod') is None,
                    reason='mongod binary not found in PATH')
def test_real_mongod_reports_an_unrecognised_option():
    tool = _tool()
    command = 'mongod --port 27999 --notARealOption'
    tool.startup_info = {'27999': command}
    with pytest.raises(SystemExit) as exc:
        tool._start_on_ports([27999])
    message = str(exc.value)
    assert message.startswith(
        "Error parsing command line: unrecognised option '--notARealOption'")
    assert 'tried to launch: %s' % command in message
