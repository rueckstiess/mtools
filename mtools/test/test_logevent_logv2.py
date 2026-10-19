from mtools.util.logevent import LogEvent
from mtools.util.logevent_logv2 import Logv2ParserMixin
from mtools.util.logformat import LogFormat


LOGV2_SLOW_QUERY = (
    '{"t":{"$date":"2022-11-22T00:00:02.933+01:00"},"s":"I","c":"COMMAND",'
    '"id":51803,"ctx":"conn1","msg":"Slow query","attr":{"type":"command",'
    '"ns":"test.foo","appName":"MongoDB Shell","command":{"find":"foo",'
    '"filter":{"a":1}},"durationMillis":5}}')


def test_logv2_parser_stays_on_logevent():
    assert issubclass(LogEvent, Logv2ParserMixin)
    assert callable(getattr(LogEvent, '_parse_logv2'))


def test_logv2_slow_query_still_parses():
    event = LogEvent(LOGV2_SLOW_QUERY)
    assert event.logformat == LogFormat.LOGV2
    assert event.namespace == 'test.foo'
    assert event.command == 'find'
    assert event.duration == 5
    assert event.app_name == 'MongoDB Shell'
