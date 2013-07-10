
from unittest import TestCase
from pytz import timezone, utc
from simpledate import SimpleDate, SimpleDateError, SimpleDateParser, DMY, MRUSortedIterable, DEFAULT_FORMAT, DEFAULT_DATE_PARSER, DEFAULT_TZ_FACTORY, take, NoTimezone, AmbiguousTimezone, SingleInstantTz, prefer, tzinfo_utcoffset, best_guess_utc, MDY, invert, ISO_8601
import datetime as dt
import time as t


DEBUG = True


class ConstructorTest(TestCase):

    def test_ymd_etc(self):
        with self.assertRaisesRegex(SimpleDateError, 'must all be provided'):
            SimpleDate(2013, 6)
        self.assert_constructor('2013-06-08 00:00:00.000000 CLT', 2013, 6, 8)
        self.assert_constructor('2013-06-08 15:51:00.000000 CLT', 2013, 6, 8, 15, 51)
        with self.assertRaisesRegex(SimpleDateError, 'Missing values for'):
            self.assert_constructor('2013-06-08 15:51:00.000000 CLT', 2013, 6, 8, second=51)
        self.assert_constructor('2013-06-08 15:51:00.000000 UTC', 2013, 6, 8, 15, 51, tz='UTC')

    def test_alternative_types(self):
        self.assert_constructor('2013-06-08 00:00:00.000000 CLT', dt.datetime(2013, 6, 8))
        self.assert_constructor('2013-06-08 00:00:00.000000 CLT', dt.date(2013, 6, 8))
        self.assert_constructor('2009-02-13 20:31:30.000000 CLST', 1234567890)
        date = SimpleDate(dt.time(15, 51), debug=DEBUG)
        assert str(date).endswith(' 15:51:00.000000 CLT'), str(date)

    def test_inconsistencies(self):
        with self.assertRaisesRegex(SimpleDateError, 'Cannot mix time with year.'):
            SimpleDate(2013, 12, 24, time=dt.time(15, 51))
        with self.assertRaisesRegex(SimpleDateError, 'Cannot specify'):
            SimpleDate(datetime=dt.datetime(2013, 6, 8), timestamp=1234567890)

    def test_literal(self):
        self.assert_constructor('2013-06-08 00:00:00 CLT', '2013-06-08 00:00:00 CLT')
        self.assert_constructor('2013-06', '2013-06', format='%Y-%m')
        self.assert_constructor('2013-01-01 00:00:00.000000 CLST', '2013', format=DEFAULT_FORMAT)

    def test_now(self):
        date = SimpleDate(debug=DEBUG)
        delta = date.timestamp - t.time()
        assert abs(delta) < 0.1, delta
        date = SimpleDate(tz='UTC', debug=DEBUG)
        delta = date.timestamp - t.time()
        assert abs(delta) < 0.1, delta

    def test_timzeone_names(self):
        self.assert_constructor('2013-06-08 00:00:00.000000 EDT', '2013-06-08 00:00:00', tz='EDT', format=DEFAULT_FORMAT)

    def assert_constructor(self, target, *args, **kargs):
        date = SimpleDate(*args, debug=DEBUG, **kargs)
        assert target == str(date), str(date)

    def test_multiple_tz(self):
        with self.assertRaisesRegex(NoTimezone, "No timezone found"):
            for month in range(1, 13):
                SimpleDate(2013, month, 1, tz='CLT', unsafe=True)
        for month in range(1, 13):
            SimpleDate(2013, month, 1, tz=('CLT', 'CLST'), unsafe=True)

    def test_ambiguous_tz(self):
        SimpleDate('2013-01-01 EST', unsafe=True, debug=True)
        with self.assertRaisesRegex(AmbiguousTimezone, '3 distinct'):
            SimpleDate('2013-01-01 EST',)
        SimpleDate('2013-01-01 EST', country='US', debug=True)
        with self.assertRaisesRegex(AmbiguousTimezone, '3 distinct'):
            SimpleDate('2013-01-01 EST', country=('US', 'AU'),)
        date = SimpleDate('2013-01-01 EST', country=('US', 'AU'), unsafe=True, debug=True)
        assert date.tzinfo.utcoffset(date.datetime) == dt.timedelta(-1, 68400), repr(date.tzinfo.utcoffset(date.datetime))
        date = SimpleDate('2013-01-01 EST', country=('AU', 'US'), unsafe=True, debug=True)
        assert date.tzinfo.utcoffset(date.datetime) != dt.timedelta(-1, 68400), repr(date.tzinfo.utcoffset(date.datetime))
        with self.assertRaisesRegex(AmbiguousTimezone, '3 distinct'):
            SimpleDate('2013-01-01 EST', country=prefer('US'),)
        date = SimpleDate('2013-01-01 EST', country=prefer('US'), unsafe=True, debug=True)
        assert date.tzinfo.utcoffset(date.datetime) == dt.timedelta(-1, 68400), repr(date.tzinfo.utcoffset(date.datetime))


    def test_ny_bug(self):
        SimpleDate('2013-06-11 19:15 America/New_York', debug=DEBUG)

    def test_now_bug(self):
        SimpleDate(tz='EDT', debug=True)

    def test_dst_bug(self):
        tz = timezone('America/Santiago')
        ambiguous = dt.datetime(2012, 4, 28, 23, 30)
        assert tz.tzname(ambiguous, is_dst=False) == 'CLT', tz.tzname(ambiguous, is_dst=False)
        assert tz.tzname(ambiguous, is_dst=True) == 'CLST', tz.tzname(ambiguous, is_dst=True)
        clt = SimpleDate('2012-04-28 23:30 CLT', tz='America/Santiago', is_dst=False, country='CL', format=DEFAULT_FORMAT)
        assert str(clt) =='2012-04-28 23:30:00.000000 CLT'
        clst = SimpleDate('2012-04-28 23:30 CLST', tz='America/Santiago', is_dst=True, country='CL', format=DEFAULT_FORMAT, debug=DEBUG)
        assert str(clst) =='2012-04-28 23:30:00.000000 CLST'
        clt = SimpleDate('2012-04-28 23:30', tz='America/Santiago', is_dst=False, country='CL', format=DEFAULT_FORMAT)
        assert str(clt) =='2012-04-28 23:30:00.000000 CLT'
        clst = SimpleDate('2012-04-28 23:30', tz='America/Santiago', is_dst=True, country='CL', format=DEFAULT_FORMAT, debug=DEBUG)
        assert str(clst) =='2012-04-28 23:30:00.000000 CLST'

    def test_formats(self):
        self.assert_constructor('23/06/2013 11:49', '23-6-2013 11:49', format=DMY)
        self.assert_constructor('06/23/2013 11:49', '6-23-2013 11:49', format=MDY)

    def test_invert_bug(self):
        self.assert_constructor('2013-07-04 18:53 CST', '2013-07-04 18:53 CST', country='CN', format=ISO_8601)


class ParserTest(TestCase):

    def test_parse(self):
        self.assert_parse('2013')
        self.assert_parse('2013-06-08')
        self.assert_parse('2013-06-08 15:51:00')
        self.assert_parse('2013-06-08 15:51:00 UTC')
        self.assert_parse('2013-06-08 15:51:00 CLT')

    def test_day_first(self):
        parser = SimpleDateParser(DMY)
        self.assert_parse('2013', parser=parser)
        self.assert_parse('08/06/2013', parser=parser, month=6)
        self.assert_parse('08/06/2013 15:51:00', parser=parser, month=6)
        self.assert_parse('08/06/2013 15:51:00 UTC', parser=parser, month=6)

    def test_weird(self):
        # will parse "2 Jun" but is reconstructed with leading 0
        self.assert_parse('Sun, 02 Jun 2013 13:26:58 -0300', SimpleDateParser('%a, %d %b %Y %H:%M:%S %z'))

    def assert_parse(self, s, parser=DEFAULT_DATE_PARSER, month=None):
        dt, _, fmt = parser.parse(s, debug=DEBUG)
        date = SimpleDate(dt, format=fmt)
        assert s == str(date), str(date)
        if month is not None:
            assert date.month == month, date.month

    def test_regexp(self):
        date = SimpleDate('2013-01-01PST', format='%Y-%m-%d%Z')
        assert str(date) == '2013-01-01PST', str(date)
        date = SimpleDate('2013-01-01PST', format=r'%Y-%m-%d %?%Z')
        assert str(date) == '2013-01-01PST', str(date)
        date = SimpleDate('%59!{|}', format='%%%M!{|}', debug=DEBUG)
        assert date.format == '%%%M!{|}', date.format
        assert str(date) == '%59!{|}', str(date)
        date = SimpleDate('%59!(|)', format='%%%M!(|)', debug=DEBUG)
        assert date.format == '%%%M!(|)', date.format
        assert str(date) == '%59!(|)', str(date)

    def test_asn1(self):
        date = SimpleDate('130706062100Z')
        assert str(date) == '130706062100Z', str(date)
        date = SimpleDate('20130706062100Z')
        assert str(date) == '20130706062100Z', str(date)
        year = SimpleDate('501111111111Z').year
        assert year == 1950, year
        year = SimpleDate('490101000000Z').year
        assert year == 2049, year
        date = SimpleDate('May 25 23:59:59 2012 GMT')
        assert str(date) == 'May 25 23:59:59 2012 GMT', str(date)
        with self.assertRaisesRegex(SimpleDateError, 'Could not parse'):
            SimpleDate('50111111111Z')  # one digit shorter than above

    def test_rfc3339(self):
        # http://www.lshift.net/blog/2010/05/20/rfc3339-simple-canonical-date-parsing-and-formatting-for-python
        midnightUTC = SimpleDate("2008-08-24T00:00:00Z").normalized
        oneamBST = SimpleDate("2008-08-24T01:00:00+01:00", debug=True).normalized
        assert oneamBST == midnightUTC

class TZFactoryTest(TestCase):

    def test_country(self):
        with self.assertRaisesRegex(AmbiguousTimezone, "2 distinct timezones"):
            DEFAULT_TZ_FACTORY.search(datetime=dt.datetime(2012, 5, 19, 12), country='CL', debug=DEBUG)
        tz = DEFAULT_TZ_FACTORY.search('EDT', datetime=dt.datetime(2012, 5, 19, 12), country='US', debug=DEBUG)
        assert repr(tz) == "SingleInstantTz(datetime.timedelta(-1, 72000), 'EDT', datetime.datetime(2012, 5, 19, 16, 0, tzinfo=<UTC>))", repr(tz)
        tz = DEFAULT_TZ_FACTORY.search('EDT', datetime=dt.datetime(2012, 5, 19, 12), debug=DEBUG)
        assert repr(tz) == "SingleInstantTz(datetime.timedelta(-1, 72000), 'EDT', datetime.datetime(2012, 5, 19, 16, 0, tzinfo=<UTC>))", repr(tz)

    def test_epoch0_bug(self):
        with self.assertRaisesRegex(SimpleDateError, "No timezone found"):
            tz = DEFAULT_TZ_FACTORY.search('CLT', datetime=dt.datetime(1970, 1, 1), debug=DEBUG)
        tz = DEFAULT_TZ_FACTORY.search('CLST', datetime=dt.datetime(1970, 1, 1), debug=DEBUG)

    def test_ambiguous(self):
        date = SimpleDate(1234567890, tz=utc)
        assert str(date) == '2009-02-13 23:31:30.000000 UTC', str(date)
        with self.assertRaisesRegex(AmbiguousTimezone, '3 distinct'):
            DEFAULT_TZ_FACTORY.search(('Australia/NSW', 'Australia/Queensland', 'EST'), datetime=date.datetime, debug=True)

        tz_nsw = timezone('Australia/NSW')
        offset_nsw = tzinfo_utcoffset(tz_nsw, date.datetime)
        # /usr/sbin/zdump -v -c 2014 Australia/NSW
        # Australia/NSW  Sat Oct  4 16:00:00 2008 UTC = Sun Oct  5 03:00:00 2008 EST isdst=1 gmtoff=39600
        # Australia/NSW  Sat Apr  4 15:59:59 2009 UTC = Sun Apr  5 02:59:59 2009 EST isdst=1 gmtoff=39600
        assert offset_nsw == dt.timedelta(seconds=39600)

        tz_qns = timezone('Australia/Queensland')
        offset_qns = tzinfo_utcoffset(tz_qns, date.datetime)
        # /usr/sbin/zdump -v Australia/Queensland
        # Australia/Queensland  Sat Feb 29 16:00:00 1992 UTC = Sun Mar  1 02:00:00 1992 EST isdst=0 gmtoff=36000
        # (last entry)
        assert offset_qns == dt.timedelta(seconds=36000)

        tz_est = timezone('EST')
        offset_est = tzinfo_utcoffset(tz_est, date.datetime)
        # zdump shows no transitions, but this is used in the USA so we expect
        # it to differ from the Australian ones
        assert offset_nsw != offset_qns != offset_est != offset_nsw


class FixedTimeTimezoneTest(TestCase):

    def test_from(self):
        date = SimpleDate(2013, 2, 2, tz='CLST', debug=DEBUG)
        tz = timezone('America/New_York')
        target = date.datetime - date.datetime.utcoffset()
        target = target.replace(tzinfo=tz)
        target = tz.fromutc(target)
        assert str(target) == '2013-02-01 22:00:00-05:00', str(target)
        target = date.convert(tz)
        assert str(target) == '2013-02-01 22:00:00.000000 EST', str(target)

    def test_to(self):
        date = SimpleDate(2013, 2, 2, tz=timezone('America/Santiago'), debug=DEBUG)
        tz = DEFAULT_TZ_FACTORY.search('EST', country='US', datetime=date, debug=DEBUG)
        target = date.datetime - date.datetime.utcoffset()
        target = target.replace(tzinfo=tz)
        target = tz.fromutc(target)
        assert str(target) == '2013-02-01 22:00:00-05:00', str(target)
        target = date.convert(tz)
        assert str(target) == '2013-02-01 22:00:00.000000 EST', str(target)

    def test_to2(self):
        date = SimpleDate(2013, 6, 2, tz=timezone('America/Santiago'), debug=DEBUG)
        tz = DEFAULT_TZ_FACTORY.search('EDT', country='US', datetime=date, debug=DEBUG)
        target = date.datetime - date.datetime.utcoffset()
        target = target.replace(tzinfo=tz)
        target = tz.fromutc(target)
        assert str(target) == '2013-06-02 00:00:00-04:00', str(target)
        target = date.convert(tz)
        assert str(target) == '2013-06-02 00:00:00.000000 EDT', str(target)

    def test_both(self):
        date = SimpleDate(2013, 2, 2, tz='CLST', debug=DEBUG)
        tz = DEFAULT_TZ_FACTORY.search('EST', country='US', datetime=date)
        target = date.datetime - date.datetime.utcoffset()
        target = target.replace(tzinfo=tz)
        target = tz.fromutc(target)
        assert str(target) == '2013-02-01 22:00:00-05:00', str(target)
        target = date.convert(tz)
        assert str(target) == '2013-02-01 22:00:00.000000 EST', str(target)


class MethodTest(TestCase):

    def test_repr(self):
        date = SimpleDate(2013, 6, 8, 15, 51, debug=DEBUG)
        assert repr(date) == "SimpleDate('2013-06-08 15:51:00.000000 CLT', tz='America/Santiago')", repr(date)
        assert date == eval(repr(date)), eval(repr(date))
        date = SimpleDate(timestamp=1234567890, debug=DEBUG)
        assert repr(date) == "SimpleDate('2009-02-13 20:31:30.000000 CLST', tz='America/Santiago')", repr(date)
        assert date == eval(repr(date)), eval(repr(date))

    def test_convert(self):
        date1 = SimpleDate('2013-06-08 12:34:56.789 CLT', debug=True)
        # date1b = date1.convert(utc, debug=True)
        date2 = date1.convert(format='%Y/%m/%d', debug=True)
        assert str(date2) == '2013/06/08', str(date2)
        date3 = date1.convert('PST')
        assert str(date3) != '2013-06-08 12:34:56.789000 PST', str(date3)
        assert str(date3).endswith('PST'), str(date3)
        assert str(date3) == '2013-06-08 08:34:56.789000 PST', str(date3)
        date4 = SimpleDate('2013-06-14 13:14:17.295943 EDT').convert(country='GB')
        assert str(date4) == '2013-06-14 18:14:17.295943 BST', date4

    def test_wrapper(self):
        date = SimpleDate('2013-06-08 12:34:56.789 CLT', debug=True)

        assert date.year == 2013, date.year
        assert date.month == 6, date.month
        assert date.day == 8, date.day
        assert date.hour == 12, date.hour
        assert date.minute == 34, date.minute
        assert date.second == 56, date.second
        assert date.microsecond == 789000, date.microsecond

        assert date.date == dt.date(2013, 6, 8), date.date
        assert date.ordinal == 735027, date.ordinal
        assert date.time == dt.time(12, 34, 56, 789000, tzinfo=date.tzinfo), date.time
        assert date.timestamp == 1370709296.789, date.timestamp

        assert str(date) == "2013-06-08 12:34:56.789000 CLT", str(date)
        assert str(date.naive) == "2013-06-08 12:34:56.789000 ", str(date.naive)

        assert date.utc.year == 2013, date.utc.year
        assert date.utc.month == 6, date.utc.month
        assert date.utc.day == 8, date.utc.day
        assert date.utc.hour == 16, date.utc.hour
        assert date.utc.minute == 34, date.utc.minute
        assert date.utc.second == 56, date.utc.second
        assert date.utc.microsecond == 789000, date.utc.microsecond

        assert date.utc.date == dt.date(2013, 6, 8), date.utc.date
        assert date.utc.ordinal == 735027, date.utc.ordinal
        assert date.utc.time == dt.time(16, 34, 56, 789000, tzinfo=utc), date.utc.time
        assert date.utc.timestamp == 1370709296.789, date.utc.timestamp

        assert str(date.utc) == "2013-06-08 16:34:56.789000 UTC", str(date.utc)
        assert str(date.utc.naive) == "2013-06-08 16:34:56.789000 ", str(date.utc.naive)

    def test_normalized(self):
        dates = [SimpleDate('2012-01-01', tz='EST', country='US').normalized,
                 SimpleDate('2012-01-02', tz='EST', country='US').normalized,
                 SimpleDate('2012-01-01', tz='EST', country='US').normalized]
        dates.sort()
        assert dates[0] == dates[1]
        assert dates[0] != dates[2]

    def test_naive_bug(self):
        now = SimpleDate(2013, 6, 10, debug=DEBUG)
        now.convert('PDT', debug=DEBUG)  # threw exception

    def test_timetamp_bug(self):
        n = 1370115240
        date = SimpleDate(n, tz='PDT')
        assert date.timestamp == n, date.timestamp
        assert str(date) == '2013-06-01 12:34:00.000000 PDT', str(date)
        assert SimpleDate('2013-06-01 12:34:00.000000 PDT').timestamp == n, SimpleDate('2013-06-01 12:34:00.000000 PDT').timestamp

        
class OperationsTest(TestCase):
    
    def test_arithmetic(self):
        date1 = SimpleDate(2013, 6, 8, 12)
        date2 = SimpleDate(2013, 6, 8, 11)
        diff = date1 - date2
        assert diff == dt.timedelta(hours=1), diff
        date3 = date1 - diff
        assert date3 == date2, date3
        date4 = date2 + diff
        assert date4 == date1, date4

    def test_tz(self):
        date = SimpleDate('2013-06-08 15:51:00 America/Santiago')
        delta = date.datetime - date.utc.datetime
        assert delta.total_seconds() == 0, delta.total_seconds()
        delta = date.datetime.replace(tzinfo=utc) - date.utc.datetime
        assert delta == date.tzinfo.utcoffset(date.utc.datetime.replace(tzinfo=None)), (delta, date.tzinfo.utcoffset(date.utc.datetime.replace(tzinfo=None)))
        assert delta == date.tzinfo.utcoffset(date.utc.naive.datetime), (delta, date.tzinfo.utcoffset(date.utc.naive.datetime))
        assert delta.total_seconds() == -14400, delta.total_seconds()

        date = SimpleDate('2013-06-08 15:51:00 CLT')
        delta = date.datetime - date.utc.datetime
        assert delta.total_seconds() == 0, delta.total_seconds()
        delta = date.datetime.replace(tzinfo=utc) - date.utc.datetime
        # not possible due to SingleInstantTimezone
        # assert delta == date.tz.utcoffset(date.utc.datetime.replace(tzinfo=None)), (delta, date.tz.utcoffset(date.utc.datetime.replace(tzinfo=None)))
        # assert delta == date.tz.utcoffset(date.utc.naive.datetime), (delta, date.tz.utcoffset(date.utc.naive.datetime))
        assert delta.total_seconds() == -14400, delta.total_seconds()


class BestGuessUtcTest(TestCase):

    def assert_utc(self, value, target):
        target = target.replace(tzinfo=utc)
        result = best_guess_utc(value)
        assert result == target, result

    def test_various(self):
        self.assert_utc('1/6/2013 UTC', dt.datetime(2013, 1, 6))
        self.assert_utc('1/6/2013 EST', dt.datetime(2013, 1, 6, 5))
        self.assert_utc('1/6/2013 BST', dt.datetime(2013, 5, 31, 23))
        self.assert_utc('Tue, 18 Jun 2013 12:19:09 -0400', dt.datetime(2013, 6, 18, 16, 19, 9))


class DocsTest(TestCase):

    def test_old_inline(self):
        result = SimpleDate(timestamp=0, tz='CLST')
        assert str(result) == "1969-12-31 21:00:00.000000 CLST", result
        with self.assertRaises(NoTimezone):
            SimpleDate(dt.datetime(2012, 5, 19, 12, 0, tzinfo=timezone('US/Eastern')), tz='ignored', debug=True)
        result = SimpleDate('2012-05-19 12:00 EDT')
        assert str(result) == "2012-05-19 12:00 EDT", result


class MRUSortedIterableTest(TestCase):

    def test_sorting(self):
        iterable = MRUSortedIterable([1,2,3,4])
        one, two = take(2, iterable)
        assert (one, two) == (1, 2), (one, two)
        two = list(take(1, iterable))[-1]
        assert two == 2, two
        assert iterable._data == [2,1,3,4], iterable._data
        list(iterable)
        next(iter(iterable))  # force sort
        assert iterable._data == [2,1,3,4], iterable._data  # unchanged as we over-ran
        four = list(take(4, iterable))[-1]
        assert four == 4, four
        next(iter(iterable))  # force sort
        assert iterable._data == [4,2,1,3], iterable._data


class StackOverflowTest(TestCase):

    def test_17248250(self):
        t = SimpleDate('56', format='%(%(%H:%)%?%M:%)%?%S').time
        assert t == dt.time(0, 0, 56), t
        t = SimpleDate('34:56', format=invert('((H:)?M:)?S')).time
        assert t == dt.time(0, 34, 56), t
        t = SimpleDate('12:34:56', format=invert('((H:)?M:)?S')).time
        assert t == dt.time(12, 34, 56), t

    def test_12165691(self):
        now_utc = SimpleDate('2013-01-02 12:34:56', tz='UTC')
        now_tz = now_utc.convert(tz='CST6CDT')
        begin_day = now_tz.replace(hour=0, minute=0, second=0, microsecond=0)
        assert now_utc.timestamp == 1357130096, now_utc.timestamp
        assert now_tz.timestamp == 1357130096, now_tz.timestamp
        assert begin_day.timestamp == 1357106400, begin_day.timestamp

    def test_7562868(self):
        date = SimpleDate('20111014T090000', tz='America/Los_Angeles')
        assert date.timestamp == 1318608000.0, date.timestamp
