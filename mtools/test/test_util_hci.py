from datetime import datetime, timedelta

from dateutil.tz import tzutc

from mtools.util.hci import DateTimeBoundaries


def test_dtb_within_boundaries_absolute():

    start = datetime(2012, 10, 14, tzinfo=tzutc())
    end = datetime(2013, 6, 2, tzinfo=tzutc())
    dtb = DateTimeBoundaries(start, end)
    from_dt, to_dt = dtb('Feb 18 2013', 'Feb 19 2013')
    assert from_dt == datetime(2013, 2, 18, tzinfo=tzutc())
    assert to_dt == datetime(2013, 2, 19, tzinfo=tzutc())


def test_dtb_from_before_start():

    start = datetime(2012, 10, 14, tzinfo=tzutc())
    end = datetime(2013, 6, 2, tzinfo=tzutc())
    dtb = DateTimeBoundaries(start, end)
    from_dt, to_dt = dtb('Sep 15 2012', 'Dec 1 2012')
    assert from_dt == start
    assert to_dt == datetime(2012, 12, 1, tzinfo=tzutc())


def test_dtb_to_after_end():

    start = datetime(2012, 10, 14, tzinfo=tzutc())
    end = datetime(2013, 6, 2, tzinfo=tzutc())
    dtb = DateTimeBoundaries(start, end)
    from_dt, to_dt = dtb('2013-01-15', '2016-03-02')
    assert from_dt == datetime(2013, 1, 15, tzinfo=tzutc())
    assert to_dt == end


def test_dtb_both_outside_bounds():

    start = datetime(2012, 10, 14, tzinfo=tzutc())
    end = datetime(2013, 6, 2, tzinfo=tzutc())
    dtb = DateTimeBoundaries(start, end)
    from_dt, to_dt = dtb('2000-01-01', '2050-12-31')
    assert from_dt == start
    assert to_dt == end


def test_dtb_keywords():

    start = datetime(2012, 10, 14, tzinfo=tzutc())
    end = datetime(2050, 1, 1, tzinfo=tzutc())
    dtb = DateTimeBoundaries(start, end)

    # start and end
    from_dt, to_dt = dtb('start', 'end')
    assert from_dt == start
    assert to_dt == end

    # today
    from_dt, to_dt = dtb('start', 'today')
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0,
                                   tzinfo=tzutc())
    assert to_dt == today

    # now, must be witin one second from now
    from_dt, to_dt = dtb('start', 'now')
    now = datetime.now().replace(tzinfo=tzutc())
    assert now - to_dt < timedelta(seconds=1)


def test_dtb_string2dt():

    start = datetime(2000, 1, 1, tzinfo=tzutc())
    end = datetime(2015, 6, 13, tzinfo=tzutc())
    dtb = DateTimeBoundaries(start, end)

    # without lower bound
    assert dtb.string2dt('') == start
    assert dtb.string2dt('2013') == datetime(2013, 1, 1, 0, 0,
                                             tzinfo=tzutc())
    assert dtb.string2dt('Aug 2011') == datetime(2011, 8, 1, 0, 0,
                                                 tzinfo=tzutc())
    assert dtb.string2dt('29 Sep 1978') == datetime(1978, 9, 29, 0, 0,
                                                    tzinfo=tzutc())

    # no year given, choose end year if still in log file, else year before
    assert dtb.string2dt('20 Mar') == datetime(2015, 3, 20, 0, 0,
                                               tzinfo=tzutc())
    assert dtb.string2dt('20 Aug') == datetime(2014, 8, 20, 0, 0,
                                               tzinfo=tzutc())

    # weekdays, always use last week of log file end
    assert dtb.string2dt('Sat') == datetime(2015, 6, 13, 0, 0, tzinfo=tzutc())
    assert dtb.string2dt('Wed') == datetime(2015, 6, 10, 0, 0, tzinfo=tzutc())
    assert dtb.string2dt('Sun') == datetime(2015, 6, 7, 0, 0, tzinfo=tzutc())

    # constants
    assert dtb.string2dt('start') == start
    assert dtb.string2dt('end') == end
    assert dtb.string2dt('today') == datetime.now().replace(hour=0, minute=0,
                                                            second=0,
                                                            microsecond=0,
                                                            tzinfo=tzutc())
    assert dtb.string2dt('yesterday') == (datetime.now()
                                          .replace(hour=0, minute=0, second=0,
                                                   microsecond=0,
                                                   tzinfo=tzutc()) -
                                          timedelta(days=1))

    # times
    assert dtb.string2dt('29 Sep 1978 13:06') == datetime(1978, 9, 29, 13, 6,
                                                          tzinfo=tzutc())
    assert dtb.string2dt('29 Sep 13:06') == datetime(2014, 9, 29, 13, 6,
                                                     tzinfo=tzutc())
    assert dtb.string2dt('13:06') == datetime(2000, 1, 1, 13, 6,
                                              tzinfo=tzutc())
    assert dtb.string2dt('13:06:15') == datetime(2000, 1, 1, 13, 6, 15,
                                                 tzinfo=tzutc())
    assert dtb.string2dt('13:06:15.214') == datetime(2000, 1, 1, 13, 6, 15,
                                                     214000, tzinfo=tzutc())
    assert dtb.string2dt('Wed 13:06:15') == datetime(2015, 6, 10, 13, 6, 15,
                                                     tzinfo=tzutc())

    # offsets
    assert dtb.string2dt('2013 +1d') == datetime(2013, 1, 2, 0, 0,
                                                 tzinfo=tzutc())
    assert dtb.string2dt('Sep 2011 +1mo') == datetime(2011, 10, 1, 0, 0,
                                                      tzinfo=tzutc())
    assert dtb.string2dt('29 Sep 1978 +3hours') == datetime(1978, 9, 29, 3, 0,
                                                            tzinfo=tzutc())
    assert dtb.string2dt('20 Mar +5min') == datetime(2015, 3, 20, 0, 5,
                                                     tzinfo=tzutc())
    assert dtb.string2dt('20 Aug -2day') == datetime(2014, 8, 18, 0, 0,
                                                     tzinfo=tzutc())
    assert dtb.string2dt('Sat -1d') == datetime(2015, 6, 12, 0, 0,
                                                tzinfo=tzutc())
    assert dtb.string2dt('Wed +4sec') == datetime(2015, 6, 10, 0, 0, 4,
                                                  tzinfo=tzutc())
    assert dtb.string2dt('Sun -26h') == datetime(2015, 6, 5, 22, 0,
                                                 tzinfo=tzutc())
    assert dtb.string2dt('29 Sep 1978 13:06 +59s') == datetime(1978, 9, 29,
                                                               13, 6, 59,
                                                               tzinfo=tzutc())
    assert dtb.string2dt('29 Sep 13:06 +120secs') == datetime(2014, 9, 29,
                                                              13, 8,
                                                              tzinfo=tzutc())
    # assert dtb.string2dt('13:06 -1week') == datetime(2014, 12, 25, 13, 6,
    #                                                  tzinfo=tzutc())
    # print dtb.string2dt('13:06:15 -16sec')
    # assert dtb.string2dt('13:06:15 -16sec') == datetime(2014, 1, 1, 13, 5,
    #                                                     59, tzinfo=tzutc())
    # assert dtb.string2dt('13:06:15.214 +1h') == datetime(2014, 1, 1, 14, 6,
    #                                                      15, 214000,
    #                                                      tzinfo=tzutc())
    assert dtb.string2dt('Wed 13:06:15 -1day') == datetime(2015, 6, 9, 13, 6,
                                                           15, tzinfo=tzutc())

    print(dtb.string2dt('start +3h'))
    assert dtb.string2dt('start +3h') == start + timedelta(hours=3)

    # offset only
    assert dtb.string2dt('-2d') == datetime(2015, 6, 11, tzinfo=tzutc())

    # test presence / absence of year and behavior for adjustment
    assert dtb.string2dt('July 30 2015') == datetime(2015, 7, 30,
                                                     tzinfo=tzutc())
    assert dtb.string2dt('July 30') == datetime(2014, 7, 30,
                                                tzinfo=tzutc())
    assert dtb.string2dt('1899 Nov 1') == datetime(1899, 11, 1, tzinfo=tzutc())

    # isoformat
    from_dt = datetime(2014, 8, 5, 20, 57, 7, tzinfo=tzutc())
    assert dtb.string2dt(from_dt.isoformat()) == datetime(2014, 8, 5, 20, 57,
                                                          7, tzinfo=tzutc())
    trydate = '2014-04-28T16:17:18.192Z'
    assert dtb.string2dt(trydate) == datetime(2014, 4, 28, 16, 17, 18, 192000,
                                              tzinfo=tzutc())

    # with lower_bounds
    lower = datetime(2013, 5, 2, 16, 21, 58, 123, tzinfo=tzutc())
    assert dtb.string2dt('', lower) == end
    assert dtb.string2dt('2013', lower) == datetime(2013, 1, 1, 0, 0,
                                                    tzinfo=tzutc())
    assert dtb.string2dt('Aug', lower) == datetime(2014, 8, 1, 0, 0,
                                                   tzinfo=tzutc())
    assert dtb.string2dt('+3sec', lower) == lower + timedelta(seconds=3)
    assert dtb.string2dt('+4min', lower) == lower + timedelta(minutes=4)
    assert dtb.string2dt('-5hours', lower) == lower - timedelta(hours=5)


if __name__ == '__main__':
    test_dtb_string2dt()
