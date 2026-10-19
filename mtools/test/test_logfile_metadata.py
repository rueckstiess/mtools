import json

from mtools.util.logfile import LogFile
from mtools.util.logfile_metadata import MetadataMixin
from mtools.util.logformat import LogFormat


def test_metadata_methods_stay_on_logfile():
    assert issubclass(LogFile, MetadataMixin)
    for name in ('_extract_metadata_legacy', '_extract_metadata_logv2',
                 '_check_for_restart_legacy', '_check_for_restart_logv2'):
        assert callable(getattr(LogFile, name))
    assert 'states' in LogFile.__dict__
    assert 'PRIMARY' in LogFile.states


def test_legacy_restart_still_detected(tmp_path):
    line = ('2015-03-10T14:21:24.485+1100 I CONTROL  [initandlisten] '
            'db version v3.0.0\n')
    path = tmp_path / 'legacy.log'
    path.write_text(line)
    logfile = LogFile(open(path, 'rb'))
    assert logfile.logformat == LogFormat.LEGACY
    assert logfile.binary == 'mongod'
    assert logfile.versions == ['3.0.0']


def test_logv2_restart_still_detected(tmp_path):
    doc = {'t': {'$date': '2022-11-22T00:00:02.933+01:00'},
           's': 'I', 'c': 'CONTROL', 'id': 23403, 'ctx': 'initandlisten',
           'msg': 'Build Info',
           'attr': {'buildInfo': {'version': '6.0.1'}}}
    path = tmp_path / 'logv2.log'
    path.write_text(json.dumps(doc) + '\n')
    logfile = LogFile(open(path, 'rb'))
    assert logfile.logformat == LogFormat.LOGV2
    assert logfile.binary == 'mongod'
    assert logfile.versions == ['6.0.1']
    assert logfile.storage_engine == 'wiredTiger'
