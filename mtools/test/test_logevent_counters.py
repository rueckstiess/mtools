from mtools.util.logevent import LogEvent
from mtools.util.logevent_counters import CountersMixin
from mtools.util.logformat import LogFormat


def test_counters_stay_on_logevent():
    assert issubclass(LogEvent, CountersMixin)
    for name in ('nscanned', 'nreturned', 'numYields', 'allowDiskUse', 'w'):
        assert isinstance(getattr(LogEvent, name), property)
    assert callable(getattr(LogEvent, '_extract_counters'))


def test_legacy_counters_still_parse():
    line = ("Mon Oct 21 12:14:21.888 [conn4] query test.docs query: "
            "{ foo: 23432.0 } ntoreturn:0 ntoskip:0 nscanned:316776 "
            "keyUpdates:0 numYields: 2405 locks(micros) r:743292 "
            "nreturned:2 reslen:2116 451ms")
    event = LogEvent(line)
    assert event.logformat == LogFormat.LEGACY
    assert event.nscanned == 316776
    assert event.numYields == 2405
    assert event.nreturned == 2
    assert event.ntoreturn == 0
