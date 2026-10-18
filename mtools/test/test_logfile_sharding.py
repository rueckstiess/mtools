import json

from mtools.util.logfile import LogFile
from mtools.util.logfile_sharding import ShardingInfoMixin
from mtools.util.logformat import LogFormat


def test_sharding_methods_stay_on_logfile():
    assert issubclass(LogFile, ShardingInfoMixin)
    for name in ('_find_sharding_info', '_find_sharding_info_legacy',
                 '_find_sharding_info_logv2'):
        assert callable(getattr(LogFile, name))


def _line(msg, attr=None, ctx='conn1', log_id=1, when='2020-02-07T01:04:26.657+00:00',
          component='SHARDING'):
    """One MongoDB 4.4+ JSON log line."""
    return {
        't': {'$date': when},
        's': 'I',
        'c': component,
        'id': log_id,
        'ctx': ctx,
        'msg': msg,
        'attr': {} if attr is None else attr,
    }


def _open_log(tmp_path, docs):
    path = tmp_path / 'logv2.log'
    text = ''.join(json.dumps(doc) + '\n' for doc in docs)
    path.write_text(text)
    return LogFile(open(path, 'rb'))


def _startup(ctx, repl_set=None, cluster_role=None):
    """Lines that identify the binary and, when given, its replica set."""
    docs = [_line('Build Info', {'buildInfo': {'version': '4.4.29'}},
                  ctx=ctx, component='CONTROL')]
    if repl_set or cluster_role:
        options = {}
        if repl_set:
            options['replication'] = {'replSetName': repl_set}
        if cluster_role:
            options['sharding'] = {'clusterRole': cluster_role}
        docs.append(_line('Options set by command line', {'options': options},
                          ctx=ctx, component='CONTROL'))
    return docs


def test_logv2_line_without_sharding_events_stays_quiet(tmp_path, capsys):
    logfile = _open_log(tmp_path, [_line('hello')])
    assert logfile.logformat == LogFormat.LOGV2
    assert logfile.shards == []
    assert logfile.csrs is None
    assert logfile.chunks_moved_from == []
    assert logfile.chunks_moved_to == []
    assert logfile.chunk_splits == []
    captured = capsys.readouterr()
    assert captured.err == ''


def test_logv2_mongos_monitors_separate_csrs_and_shards(tmp_path):
    docs = _startup('mongosMain')
    docs.append(_line(
        'Starting Replica Set Monitor',
        {'protocol': 'streamable',
         'uri': 'mongodb://localhost:27033/?replicaSet=configRepl'},
        ctx='mongosMain', log_id=4603701, component='NETWORK'))
    docs.append(_line(
        'Starting Replica Set Monitor',
        {'protocol': 'streamable',
         'uri': ('mongodb://localhost:27018,localhost:27019,localhost:27020/'
                 '?replicaSet=shard01')},
        ctx='conn4', log_id=4603701, component='NETWORK'))
    logfile = _open_log(tmp_path, docs)
    assert logfile.binary == 'mongos'
    assert logfile.csrs == ('configRepl', 'localhost:27033')
    assert logfile.shards == [
        ('shard01', 'localhost:27018,localhost:27019,localhost:27020')]


def test_logv2_config_server_config_and_shard_monitors(tmp_path):
    docs = _startup('initandlisten', repl_set='configRepl', cluster_role='configsvr')
    docs.append(_line(
        'New replica set config in use',
        {'config': {
            '_id': 'configRepl',
            'version': 1,
            'configsvr': True,
            'protocolVersion': 1,
            'members': [{'_id': 0, 'host': 'localhost:27033'}],
        }},
        ctx='conn4', log_id=21392, component='REPL'))
    docs.append(_line(
        'Starting Replica Set Monitor',
        {'uri': 'shard01/localhost:27018,localhost:27019,localhost:27020'},
        ctx='conn7', log_id=4603701, component='NETWORK'))
    logfile = _open_log(tmp_path, docs)
    assert logfile.binary == 'mongod'
    assert logfile.repl_set == 'configRepl'
    assert logfile.csrs == ('configRepl', 'localhost:27033')
    assert logfile.shards == [
        ('shard01', 'localhost:27018,localhost:27019,localhost:27020')]


def test_logv2_shard_treats_the_first_monitor_as_csrs(tmp_path):
    docs = _startup('initandlisten', repl_set='shard01', cluster_role='shardsvr')
    docs.append(_line(
        'New replica set config in use',
        {'config': {'_id': 'shard01', 'version': 1, 'members': []}},
        ctx='conn4', log_id=21392, component='REPL'))
    docs.append(_line(
        'Starting Replica Set Monitor',
        {'uri': 'configRepl/localhost:27033'},
        ctx='conn15', log_id=4603701, component='NETWORK'))
    docs.append(_line(
        'Starting Replica Set Monitor',
        {'uri': 'shard02/localhost:27021,localhost:27022'},
        ctx='shard registry reload', log_id=4603701, component='NETWORK'))
    logfile = _open_log(tmp_path, docs)
    assert logfile.repl_set == 'shard01'
    assert logfile.csrs == ('configRepl', 'localhost:27033')
    assert logfile.shards == [('shard02', 'localhost:27021,localhost:27022')]


def test_logv2_chunk_moves_from_changelog_events(tmp_path):
    when = '2020-02-07T01:04:26.657+00:00'
    success = _line(
        'About to log metadata event',
        {'namespace': 'changelog',
         'event': {
             'what': 'moveChunk.from',
             'ns': 'test.products',
             'details': {
                 'min': {'sku': {'$minKey': 1}},
                 'max': {'sku': 23153496},
                 'step 1 of 6': 0,
                 'step 2 of 6': 3,
                 'to': 'shard02',
                 'from': 'shard01',
                 'note': 'success',
             },
         }},
        log_id=22080, when=when)
    failed = _line(
        'About to log metadata event',
        {'namespace': 'changelog',
         'event': {
             'what': 'moveChunk.from',
             'ns': {'db': 'test', 'coll': 'products'},
             'details': {
                 'min': {'sku': 1},
                 'max': {'sku': 2},
                 'note': 'aborted',
             },
         }},
        log_id=22080, when='2020-02-07T01:05:00.000+00:00')
    received = _line(
        'About to log metadata event',
        {'namespace': 'changelog',
         'event': {
             'what': 'moveChunk.to',
             'ns': 'test.products',
             'details': {
                 'min': {'sku': 1},
                 'max': {'sku': 2},
                 'from': 'shard03',
                 'note': 'success',
                 'step 1 of 6': 204,
             },
         }},
        log_id=22080, when='2020-02-07T01:06:00.000+00:00')
    cause = _line('Chunk move failed',
                  {'error': {'code': 237, 'codeName': 'ChunkTooBig'}},
                  log_id=23777, when='2020-02-07T01:04:59.000+00:00')
    logfile = _open_log(tmp_path, [success, cause, failed, received])

    moved_from = logfile.chunks_moved_from
    assert len(moved_from) == 2
    _, chunk_range, dest, namespace, steps, note, errmsg = moved_from[0]
    assert namespace == 'test.products'
    assert dest == 'shard02'
    assert note == 'success'
    assert errmsg is None
    assert steps == [('step 1 of 6', '0'), ('step 2 of 6', '3')]
    assert '"$minKey": 1' in chunk_range
    _, _, dest, namespace, steps, note, errmsg = moved_from[1]
    assert namespace == 'test.products'
    assert dest == 'Unknown'
    assert note == 'aborted'
    assert steps is None
    assert errmsg == 'ChunkTooBig'

    moved_to = logfile.chunks_moved_to
    assert len(moved_to) == 1
    _, _, source, namespace, steps, note, errmsg = moved_to[0]
    assert source == 'shard03'
    assert namespace == 'test.products'
    assert note == 'success'
    assert errmsg is None
    assert steps == [('step 1 of 6', '204')]


def test_logv2_splits_and_jumbo_chunks(tmp_path):
    when = '2020-02-07T01:04:11.924+00:00'
    docs = [
        _line('Requested split points lookup for chunk',
              {'namespace': 'test.products',
               'minKey': {'sku': 1},
               'maxKey': {'sku': 2}},
              log_id=22107, when=when),
        _line('Slow query',
              {'type': 'command',
               'ns': 'admin.$cmd',
               'command': {
                   'splitVector': 'test.products',
                   'min': {'sku': {'$minKey': 1}},
                   'max': {'sku': {'$maxKey': 1}},
               },
               'durationMillis': 239},
              log_id=51803, when=when, component='COMMAND'),
        _line('Slow query',
              {'type': 'command',
               'command': {'find': 'test.products', 'filter': {}}},
              log_id=51803, when=when, component='COMMAND'),
        _line('autosplitted chunk',
              {'namespace': 'test.products',
               'minKey': {'sku': 1},
               'maxKey': {'sku': 2},
               'splitPoints': 2},
              log_id=21908, when=when),
        _line('Unable to auto-split chunk',
              {'namespace': 'test.products',
               'chunk': '{ sku: 1 } -->> { sku: 2 }',
               'error': {'codeName': 'CannotSplit'}},
              log_id=21910, when=when),
        _line('Marking chunk as jumbo',
              {'chunk': '[{ sku: 1.0 }, { sku: 2.0 })'},
              log_id=21873, when='2020-02-07T04:47:18.485+00:00'),
    ]
    logfile = _open_log(tmp_path, docs)
    splits = logfile.chunk_splits
    assert len(splits) == 5
    assert splits[0][2:] == ('test.products', 0, None, [], None)
    assert splits[1][2] == 'test.products'
    assert splits[1][4] is True
    assert splits[1][5] == ['239']
    assert splits[2][3:] == (2, True, [], None)
    assert splits[3][2] == 'test.products'
    assert splits[3][4] is False
    assert splits[3][6] == 'CannotSplit'
    assert splits[4][2] == ''
    assert splits[4][4] is False
    assert splits[4][6] == 'Jumbo'
    assert splits[4][1] == '[{ sku: 1.0 }, { sku: 2.0 })'


def test_logv2_sharding_scan_leaves_the_file_readable(tmp_path):
    docs = [_line('hello', log_id=1), _line('hello', log_id=2)]
    logfile = _open_log(tmp_path, docs)
    assert logfile.shards == []
    events = list(logfile)
    assert [event.doc['id'] for event in events] == [1, 2]
