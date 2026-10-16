from dateutil.parser import parse

from mtools.util.logevent import LogEvent
from mtools.util.logevent_profile import ProfileParserMixin
from mtools.util.logformat import LogFormat


def test_profile_parser_stays_on_logevent():
    assert issubclass(LogEvent, ProfileParserMixin)
    assert callable(getattr(LogEvent, '_parse_profile_doc'))


def test_profile_doc_still_parses():
    doc = {"op": "query", "ns": "test.foo",
           "thread": "test.system.profile",
           "query": {"query": {"test": 1},
                     "orderby": {"field": 1}},
           "ntoreturn": 0, "nscanned": 4, "numYield": 2,
           "nreturned": 1, "millis": 3,
           "lockStats": {"timeLockedMicros": {"r": 461, "w": 0},
                         "timeAcquiringMicros": {"r": 4, "w": 3}},
           "ts": parse("2014-03-20T04:04:21.231Z")}
    event = LogEvent(doc)
    assert event.logformat == LogFormat.PROFILE
    assert event.pattern == '{"test": 1}'
    assert event.sort_pattern == '{"field": 1}'
    assert event.namespace == 'test.foo'
    assert event.operation == 'query'
    assert event.thread == 'test.system.profile'
    assert event.nscanned == 4
    assert 'query test.foo' in event.line_str
    assert 'nscanned:4' in event.line_str
