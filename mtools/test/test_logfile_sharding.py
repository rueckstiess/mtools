import json

from mtools.util.logfile import LogFile
from mtools.util.logfile_sharding import ShardingInfoMixin
from mtools.util.logformat import LogFormat


def test_sharding_methods_stay_on_logfile():
    assert issubclass(LogFile, ShardingInfoMixin)
    for name in ('_find_sharding_info', '_find_sharding_info_legacy',
                 '_find_sharding_info_logv2'):
        assert callable(getattr(LogFile, name))


def test_logv2_sharding_stays_a_stub(tmp_path, capsys):
    doc = {'t': {'$date': '2019-06-09T02:18:02.194+00:00'},
           's': 'I', 'c': 'SHARDING', 'id': 1, 'ctx': 'initandlisten',
           'msg': 'hello'}
    path = tmp_path / 'logv2.log'
    path.write_text(json.dumps(doc) + '\n')
    logfile = LogFile(open(path, 'rb'))
    assert logfile.logformat == LogFormat.LOGV2
    assert logfile.shards == []
    assert logfile.chunks_moved_from == []
    assert logfile.chunks_moved_to == []
    captured = capsys.readouterr()
    assert 'not yet supported' in captured.err
