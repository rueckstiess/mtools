from mtools.util.log2code import Log2CodeConverter

logline1 = ("Thu Nov 14 17:58:43.898 [rsStart] replSet info Couldn't load "
            "config yet. Sleeping 20sec and will try again.")
logline2 = ("Thu Nov 14 17:58:43.917 [initandlisten] connection accepted "
            "from 10.10.0.38:37233 #10 (4 connections now open)")

l2cc = Log2CodeConverter()


def test_log2code():
    fixed, variable = l2cc(logline1)
    assert fixed
    assert fixed.matches["r2.4.9"] == [('src/mongo/db/repl/rs.cpp', 790, 0,
                                        'log(')]
