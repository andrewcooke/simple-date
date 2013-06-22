
from calendar import timegm
import datetime as dt
from itertools import islice
from collections import MutableSet, OrderedDict
from threading import local
from tzlocal import get_localzone
from pytz import timezone, country_timezones, all_timezones, FixedOffset, utc, NonExistentTimeError, common_timezones
from simpledate.fmt import strptime, reconstruct


# A wrapper around the datetime, pytz and tzlocal packages.

# (c) 2013 Andrew Cooke (andrew@acooke.org)
# Released into the public domain for any use, but with absolutely no warranty.



# Build the various formats used by SimpleDateParser.
from simpledate.utils import DebugLog, MRUSortedIterable, OrderedSet


def add_timezone(*formats):
    '''
    Add %Z and %z to formats.

    :param formats: The formats to modify
    :return: A tuple containing the given formats, repeated ending in %Z, %z
             or nothing.
    '''
    def expand():
        for fmt in formats:
            yield fmt
            yield fmt + ' %Z'
            yield fmt + ' %z'
    return tuple(expand())

RFC_2822 = EMAIL = add_timezone('%a, %d %b %Y %H:%M:%S', '%d %b %Y %H:%M:%S')
ISO_8601 = add_timezone('%Y-%m-%d %H:%M:%S.%f', '%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M', '%Y-%m-%d', '%Y')
ISO_8601_T = add_timezone('%Y-%m-%dT%H:%M:%S.%f', '%Y-%m-%dT%H:%M:%S', '%Y-%m-%dT%H:%M')
MONTH_FIRST = add_timezone('%m/%d/%Y %H:%M:%S.%f', '%m/%d/%Y %H:%M:%S', '%m/%d/%Y %H:%M', '%m/%d/%Y', '%Y')
DAY_FIRST = add_timezone('%d/%m/%Y %H:%M:%S.%f', '%d/%m/%Y %H:%M:%S', '%d/%m/%Y %H:%M', '%d/%m/%Y', '%Y')

DEFAULT_FORMAT = '%Y-%m-%d %H:%M:%S.%f %Z'
DEFAULT_FORMATS = ISO_8601 + ISO_8601_T + RFC_2822



# Various utilities to work around oddities (bugs?) in pytz and python versions.


def reapply_tzinfo(datetime, is_dst):
    '''
    Re-apply the timezone to the datetime.  This is what you might think
    pytz's normalize does, but it doesn't.  So this is like a normalize on
    steroids.  This fixes an issue where pytz's tzinfo gets stuck at the
    wrong date.

    :param datetime: The datetime (with tzinfo) that may be broken.
    :return: A new datetime, with the same tzinfo.
    '''
    return tzinfo_localize(datetime.tzinfo, datetime.replace(tzinfo=None), is_dst)


def tzinfo_astimezone(tzinfo, datetime):
    '''
    Set the timezone after conversion.

    :param tzinfo: The timezone we are targetting.
    :param datetime: The datetime to adjust and then make naive.
    :return: A naive datetime in the given timezone.
    '''
    if datetime.tzinfo:
        datetime = datetime.astimezone(tzinfo)
    if datetime.tzinfo is not tzinfo:
        datetime = datetime.replace(tzinfo=tzinfo)
    return datetime


def tzinfo_tzname(tzinfo, datetime, is_dst):
    '''
    Get the name for the timezone at this time, avoiding an error when not
    naive.

    :param tzinfo: The tzinfo whose name we want.
    :param datetime: The time at which we want the name.
    :param is_dst: To resolve ambiguities.
    :return: The name of the tzinfo at the given time.
    '''
    datetime = tzinfo_astimezone(tzinfo, datetime)
    # don't understand why we need this, but without it get very odd results.
    datetime = datetime.replace(tzinfo=None)
    # for some reason there are two APIs...
    try:
        return tzinfo.tzname(datetime, is_dst)
    except TypeError:
        name = tzinfo.tzname(datetime)
        if name is None:
            offset = tzinfo_utcoffset(tzinfo, datetime)
            # following from datetime %z formatting code
            if offset is not None:
                sign = '+'
                if offset.days < 0:
                    offset = -offset
                    sign = '-'
                h, m = divmod(offset, dt.timedelta(hours=1))
                assert not m % dt.timedelta(minutes=1), "whole minute"
                m //= dt.timedelta(minutes=1)
                name = '%c%02d%02d' % (sign, h, m)
        return name



def tzinfo_utcoffset(tzinfo, datetime):
    '''
    Get the UTC offset for the timezone at this time, avoiding an error when
    not naive.

    :param tzinfo: The tzinfo whose offset we want.
    :param datetime: The time at which we want the offset.
    :return: The UTC offset of the tzinfo at the given time.
    '''
    datetime = tzinfo_astimezone(tzinfo, datetime)
    # don't understand why we need this, but without it get very odd results.
    datetime = datetime.replace(tzinfo=None)
    return tzinfo.utcoffset(datetime)


def tzinfo_localize(tzinfo, datetime, is_dst):
    '''
    If is_dst is unsupported then ignore it.

    :param tzinfo: The tzinfo we are setting.
    :param datetime: The datetime we are converting.
    :param is_dst: Whether the date it daylight savings time.
    :return: The localized datetime.
    '''
    try:
        return tzinfo.localize(datetime, is_dst)
    except TypeError:
        return tzinfo.localize(datetime)


def datetime_timestamp(datetime):
    '''
    Equivalent to datetime.timestamp() for pre-3.3
    '''
    try:
        return datetime.timestamp()
    except AttributeError:
        utc_datetime = datetime.astimezone(utc)
        return timegm(utc_datetime.timetuple()) + utc_datetime.microsecond / 1e6



# Utilities to help with argument handling and the like.


def always_tuple(value, convert_None=True):
    '''
    Some arguments can be a single value, or a sequence (tuple or list).
    This function normalizes the input to always be a sequence.

    :param value: The value that, if non-sequence, should be converted to a
                  sequence.
    :param convert_None: Whether `None` should be converted too.
    :return: The value as a sequence.
    '''
    if not convert_None and value is None:
        return value
    # elif isinstance(value, Iterable) and not isinstance(value, str):
    elif hasattr(value, '__iter__') and not isinstance(value, str):
        return tuple(value)
    else:
        return (value,)


def always_datetime(value):
    '''
    :param value: The value to convert to datetime (datetime or SimpleDate).
    :return: A datetime.
    '''
    try:
        return value.datetime
    except AttributeError:
        return value


def names(cutoff, test, **kargs):
    '''
    Given a set of named values, select those for which `test(value)` is True
    and then, if `cutoff` or more are found, return their names.

    :param cutoff: The number of named values that must match the test.
    :param test: The test for values.
    :param kargs: The named values.
    :return: The names of values that match the test, if `cutoff` or more match,
             otherwise `None`.
    '''
    defined = {name: value for name, value in kargs.items() if test(value)}
    if len(defined) >= cutoff:
        return list(defined.keys())
    else:
        return None


def test_all(test, *args): return all(map(test, args))
def test_any(test, *args): return any(map(test, args))

def is_none(value): return value is None
def is_not_none(value): return value is not None
def is_int_or_none(value): return value is None or isinstance(value, int)


def take(n, iterable): return islice(iterable, 0, n)


def prefer(*countries, using=set(country_timezones.keys())):
    '''
    Pull some countries to the front of the list.  When used with
    `unsafe=True` this can help select the expected timezone.

    :param countries: The countries to prefer (in order).
    :param using: The full list of countries.
    :return: All country codes, with the given ones first.
    '''
    codes = OrderedSet(countries)
    codes.union(using)
    return codes


def exclude(*countries, using=set(country_timezones.keys())):
    '''
    Drop some countries from the list.

    :param countries: The countries to prefer (in order).
    :param using: The full list of countries.
    :return: All country codes, with the given ones first.
    '''
    return OrderedSet(code for code in using if code not in countries)


# Exceptions.


class SimpleDateError(Exception):

    def __init__(self, template='', *args, **kargs):
        '''
        :param template: A message that can contain {0}-style formatting.
        :param args: Format arguments.
        :param kargs: Named format arguments.
        :return: A new instance of the exception.
        '''
        super().__init__(template.format(*args, **kargs))


class PyTzFactoryError(SimpleDateError):

    def __init__(self, message, timezones, datetime, is_dst=False, country=None, unsafe=None):
        '''
        :param message: A descriptive message.
        :param timezones: The timezones passed to the search method.
        :param datetime: The datetime passed to the search method.
        :param is_dst: The DST flag passed to the search method.
        :param country: The country code passed to the search method.
        :param unsafe: The unsafe flag passed to the search method.
        '''
        super().__init__(PyTzFactoryError.format(message, timezones, datetime, is_dst, country, unsafe))

    @staticmethod
    def format(message, timezones, datetime, is_dst, country, unsafe):
        '''
        :param message: A descriptive message.
        :param timezones: The timezones passed to the search method.
        :param datetime: The datetime passed to the search method.
        :param is_dst: The DST flag passed to the search method.
        :param country: The country code passed to the search method.
        :param unsafe: The unsafe flag passed to the search method.
        '''
        if is_dst is None and country is None and unsafe is None:
            return '{0} (timezones={1!r}, datetime={2!r})'.format(message, timezones, datetime)
        else:
            return '{0} (timezones={1!r}, datetime={2!r}, is_dst={3!r}, country={4!r}, unsafe={5!r})'.format(message, timezones, datetime, is_dst, country, unsafe)


class NoTimezone(PyTzFactoryError):

    def __init__(self, timezones, datetime, is_dst, country, unsafe):
        '''
        :param timezones: The timezones passed to the search method.
        :param datetime: The datetime passed to the search method.
        :param is_dst: The DST flag passed to the search method.
        :param country: The country code passed to the search method.
        :param unsafe: The unsafe flag passed to the search method.
        '''
        # use a list for timezones so it looks different from tuples in docs
        super().__init__('No timezone found', list(timezones), datetime, is_dst, country, unsafe)


class AmbiguousTimezone(PyTzFactoryError):

    def __init__(self, distinct, timezones, datetime, is_dst, country, unsafe):
        '''
        :param distinct: The timezones found with distinct offsets..
        :param timezones: The timezones passed to the search method.
        :param datetime: The datetime passed to the search method.
        :param is_dst: The DST flag passed to the search method.
        :param country: The country code passed to the search method.
        :param unsafe: The unsafe flag passed to the search method.
        '''
        super().__init__('{0} distinct timezones found: {1}'.format(len(distinct), '; '.join(map(repr, distinct))),
                         timezones, datetime, is_dst, country, unsafe)


class SingleInstantTzError(SimpleDateError):
    '''
    An attempt was made to use a timezone defined only for one isolated
    instant in time in a more general way.  Typically, all you can do with
    times associated with such timezones is convert them to UTC.
    '''

    def __init__(self, tzinfo, datetime, other):
        '''
        :param tzinfo: The offset and name.
        :param datetime: The time at which the timezone is defined.
        :param other: The time at which the timezone was used.
        '''
        super().__init__('Attempted to use {0} (defined only for {1}) on {2}', tzinfo, datetime, other)



# Classes implementing the core functionality.


class SingleInstantTz(dt.tzinfo):
    '''
    A timezone valid only for one particular instant.
    '''

    __slots__ = ('__tz', '__datetime')

    def __init__(self, tzinfo, datetime, is_dst):
        '''
        :param offset: The offset for the timezone (timedelta instance).
        :param name: The name of the timezone.
        :param datetime: The instant for which we know this is valid.
        :return: A tzinfo that only works for the given instant.
        '''
        offset = tzinfo_utcoffset(tzinfo, datetime)
        name = tzinfo_tzname(tzinfo, datetime, is_dst)
        self.__tz = dt.timezone(offset, name)
        # store as utc so that we can easily compare with other values.
        self.__datetime = tzinfo_astimezone(utc, tzinfo_astimezone(self.__tz, datetime))

    def __check(self, method, datetime):
        '''
        :param method: The method we want to call.
        :param datetime: The instant we want to use the timezone at.
        :return: The result from the method call, if the instant matches.
        '''
        # take care to avoid triggering recursion
        check = datetime
        if check.tzinfo is self:
            check = check.replace(tzinfo=self.__tz)
        if check.tzinfo:
            check = check.astimezone(utc)
        if check.year == self.__datetime.year and \
                check.month == self.__datetime.month and \
                check.day == self.__datetime.day and \
                check.hour == self.__datetime.hour and \
                check.minute == self.__datetime.minute and \
                check.second == self.__datetime.second and \
                check.microsecond == self.__datetime.microsecond:
            return method(datetime)
        else:
            raise SingleInstantTzError(self.__tz, self.__datetime, datetime)

    # delegate the usual API after checking (or, in some cases related to
    # conversion, check afterwards).

    def tzname(self, datetime):
        return self.__check(self.__tz.tzname, datetime)

    def utcoffset(self, datetime):
        return self.__check(self.__tz.utcoffset, datetime)

    def dst(self, datetime):
        return self.__check(self.__tz.dst, datetime)

    def fromutc(self, datetime):
        datetime = self.__tz.fromutc(datetime.replace(tzinfo=self.__tz)).replace(tzinfo=self)
        return self.__check(lambda x:x, datetime)

    def __str__(self):
        return str(self.__tz)

    def __repr__(self):
        return '{0}({1!r}, {2!r}, {3!r})'.format(self.__class__.__name__, self.__tz.utcoffset(self.__datetime), str(self.__tz), self.__datetime)

    def localize(self, datetime, is_dst=False):
        datetime = self.__localize(datetime)
        return self.__check(lambda x: x, datetime)

    def __localize(self, datetime):
        if datetime.tzinfo is not None:
            raise ValueError('Not naive datetime (tzinfo is already set)')
        return datetime.replace(tzinfo=self)

    def normalize(self, datetime, is_dst=False):
        return self.__check(self.__normalize, datetime)

    def __normalize(self, datetime, is_dst=False):
        if dt.tzinfo is None:
            raise ValueError('Naive time - no tzinfo set')
        return tzinfo_astimezone(self, datetime)


class PyTzFactory(DebugLog):
    '''
    Generate timezones (mainly from strings, but other formats are supported
    in places, too).

    IMPORTANT: Not thread safe.
    '''

    def __init__(self, timezones=None, countries=None, debug=False):
        '''
        :param timezones: The zones to search by default.
        :param countries: Countries to use by default (None implies all).
        :param debug: If true, display debug messages to stdout.
        :return: A new instance of the factory.
        '''
        if timezones is None:
            timezones = common_timezones
        timezones = set.union(*[set(self.expand_tz(zone, debug=debug)) for zone in timezones])
        if countries:
            timezones = timezones.intersection(self.expand_country(*countries, debug=debug))
        self.__sorted_zones = MRUSortedIterable(timezones)

    def search(self, *timezones, datetime=None, is_dst=False, country=None, unsafe=False, debug=False):
        '''
        Find a single timezone consistent with the parameters given.

        To get a timezone for a given date:
        >>> from datetime import datetime
        >>> PyTzFactory().search('EDT', datetime=datetime(2013,6,1))
        SingleInstantTz(datetime.timedelta(-1, 72000), 'EDT', datetime.datetime(2013, 6, 1, 0, 0, tzinfo=<UTC>))

        To test whether GMT is a valid timezone in London in January:
        >>> PyTzFactory().search('Europe/London', 'GMT', datetime=datetime(2013,1,1))
        <DstTzInfo 'Europe/London' GMT0:00:00 STD>

        while the following will succeed at any time of year:
        >>> PyTzFactory().search('Europe/London', ('GMT', 'BST'), datetime=datetime(...))
        <DstTzInfo 'Europe/London' GMT0:00:00 STD>

        and this will fail:
        >>> PyTzFactory().search('Europe/London', 'BST', datetime=datetime(2013,1,1))
        NoTimezone: No timezone found...

        Ambiguity is an error, hence:
        >>> PyTzFactory().search('EST', datetime=datetime(2013,1,1))
        AmbiguousTimezone: 3 distinct timezones found: <DstTzInfo 'US/Eastern' EST-1 day, 19:00:00 STD>; <DstTzInfo 'Australia/Queensland' EST+10:00:00 STD>; <DstTzInfo 'Australia/Canberra' EST+10:00:00 STD>...

        but can be resolve by, for example:
        >>> PyTzFactory().search('EST', country='US', datetime=datetime(2013,1,1))
        SingleInstantTz(datetime.timedelta(-1, 68400), 'EST', datetime.datetime(2013, 1, 1, 0, 0, tzinfo=<UTC>))

        or, since PyTZ defines this as an unlimited timezone (note that `datetime` is omitted):
        >>> PyTzFactory().search('EST')
        <StaticTzInfo 'EST'>

        :param timezones: Zero or more timezones.  These can be names, offsets
                          in minutes, timedelta instances, timezone instances,
                          or tuples of those values.  Each timezone is used in
                          sequence to restrict the range of possible values
                          (functions as a logical AND).  A tuple timezone
                          matches any of the values (functions as a logical OR).
                          So, for example, if called as
                          >>> PyTzFactory().search(A, (B, C))
                          then the result will be consistent with A and (B or C).
        :param datetime: When the timezone is used.
        :param is_dst: Whether the timezone is daylight saving (used to resolve ambiguities during transition).
        :param country: A country code (or tuple of codes).  If given, only timezones in that country are considered.
        :param unsafe: Take the first timezone found.
        :param debug: Print an explanation of the process followed to stdout?
        :return: A timezone consistent with the parameters given.
        '''

        log = self._get_log(debug)
        datetime = always_datetime(datetime)
        log(PyTzFactoryError.format('Searching', timezones, datetime, is_dst, country, unsafe))

        # either start with the timezones by country or 'everything' (None).
        if country is None:
            known = None
        else:
            known = self.expand_country(*always_tuple(country), debug=debug)

        # repeatedly expand/filter.
        for tz in timezones:
            known=None if known is None else OrderedSet(known)
            known = self.expand_tz(*always_tuple(tz), known=known, datetime=datetime, is_dst=is_dst, debug=debug)

        # if we never filtered anything, we have everything.
        if known is None:
            known = set(self.__sorted_zones)

        # in the unsafe case we don't force evaluation of the complete
        # generator.  instead, we pull the first value and return as a
        # single instant timezone.  so there can be no ambiguity here.
        if unsafe:
            try:
                found = next(known)
                log('Found (unsafe) {0}', found)
                return SingleInstantTz(found, datetime, is_dst)
            except StopIteration:
                raise NoTimezone(timezones, datetime, is_dst, country, unsafe)

        # otherwise, we do expand everything (which is slower).  we can then
        # check whether we have a unique value, or whether the repeated values
        # all have the same offset.
        else:
            known = list(known)
            if not known:
                raise NoTimezone(timezones, datetime, is_dst, country, unsafe)
            elif len(known) == 1:
                found = known[0]
                log('Found {0}', found)
                return found
            else:
                distinct = list(self.distinct(known, datetime=datetime, debug=debug))
                log('Have {0} distinct timezone(s)', len(distinct))
                if len(distinct) == 1:
                    found = next(iter(distinct))
                    log('Found {0}', found)
                    return SingleInstantTz(found, datetime, is_dst)
                else:
                    raise AmbiguousTimezone(distinct, timezones, datetime, is_dst, country, unsafe)

    def distinct(self, timezones, datetime=None, debug=False):
        '''
        :param timezones: Timezones to filter
        :param datetime: The date at which we are evaluating timezones.
        :param debug: Print an explanation of the process followed to stdout?
        :return: A subset of timezones that all have distinct offsets relative to UTC.
        '''
        log = self._get_log(debug)
        datetime = always_datetime(datetime)
        offsets = set()

        for tz in timezones:
            if datetime is None:
                log('Allowing single timezone without datetime: {0}', tz)
                # this is a little tricksy, but allows us to handle a single
                # timezone (which is distinct by definition)
                if not offsets:
                    yield tz
                else:
                    raise SimpleDateError('Need datetime to filter multiple timezones')
                offsets.add(object())
            else:
                offset = tzinfo_utcoffset(tz, datetime)
                if offset not in offsets:
                    log('New offset {0} for {1}', offset, tz)
                    yield tz
                    offsets.add(offset)
                else:
                    log('Known offset {0} for {1}', offset, tz)

    def expand_tz(self, *timezones, known=None, datetime=None, is_dst=False, debug=False):
        '''
        For each timezone in turn, search for possible tzinfo instances within
        the `known` set.  If the timezone is a tuple then each value in the
        tuple is separately expanded.  So, for example, if called as
        >>> factory.expand_tz(A, (B, C))
        then the result will be consistent with A and (B or C).

        'Expand' may be misleading; it's really filtering.

        :param timezones: Zero or more timezones.  These can be names, offsets
                          in minutes, timedelta instances, timezone instances,
                          or tuples of those values.  Each timezone is used in
                          sequence to restrict the range of possible values
                          (functions as a logical AND).  A tuple timezone
                          matches any of the values (functions as a logical OR).
        :param known: The current known set of timezones (which will be filter).
                      If `None`, then all are used.
        :param datetime: When the timezone is used.
        :param is_dst: Whether the timezone is daylight saving (used to resolve
                       ambiguities during transition).
        :param debug: Print an explanation of the process followed to stdout?
        :return: A sequence of timezones consistent with the parameters given.
        '''

        log = self._get_log(debug)
        datetime = always_datetime(datetime)
        count = 0

        if known is None:
            known_set = None
            try:
                known_sorted = self.__sorted_zones
            except AttributeError:
                known_sorted = tuple()
        else:
            if not known:
                log('No known zones for {0!r}', timezones)
                return
            else:
                known_set = known
                known_sorted = known

        def check(message, tzinfo):
            nonlocal count
            # filter against `known`, if it exists.
            if known_set is None or tzinfo in known_set:
                log('{0}: found {1}', message, tzinfo)
                count += 1
                yield tzinfo
            else:
                log('{0}: excluding {1}', message, tzinfo)

        log('Expanding {0!r}', timezones)
        for tz in timezones:

            if tz is None:
                # yield from check('Locale', get_localzone())
                for tzinfo in check('Locale', get_localzone()): yield tzinfo
                continue

            if isinstance(tz, dt.tzinfo):
                # yield from check('Direct', tz)
                for tzinfo in check('Direct', tz): yield tzinfo
                continue

            if isinstance(tz, dt.timedelta):
                log('Converting {0} to minutes', tz)
                seconds = tz.total_seconds()
                if seconds % 60:
                    raise PyTzFactoryError('Time difference not a round number of minutes (%s)' % tz, timezones, datetime, is_dst)
                tz = seconds / 60
                # falls through to next section

            if isinstance(tz, int) or isinstance(tz, float):
                log('Assuming {0} is minutes', tz)
                # yield from check('Fixed offset', FixedOffset(tz))
                for tzinfo in check('Fixed offset', FixedOffset(tz)): yield tzinfo
                continue

            if isinstance(tz, str):
                try:
                    # yield from check('Name', timezone(tz))
                    for tzinfo in check('Name', timezone(tz)): yield tzinfo
                    # continue to next stage if GMT, EST or similar
                    if datetime is None or '/' in tz:
                        continue
                except KeyError:
                    log('Name lookup failed for {0}', tz)

            if isinstance(tz, str):
                if datetime is None:
                    raise PyTzFactoryError('Cannot expand limited timezone without datetime', timezones, datetime, is_dst)
                for tzinfo in known_sorted:
                    try:
                        name = tzinfo_tzname(tzinfo, datetime, is_dst)
                        if tz == name:
                            log('Found {0} using {1}', tz, tzinfo)
                            count += 1
                            yield tzinfo
                        else:
                            log('{0} gave {1}', tzinfo, name)
                    except NonExistentTimeError as e:
                        log('{0} / {1} ({2}) gave {3!r}', tz, datetime, is_dst, e)
                continue

            raise PyTzFactoryError('Cannot expand timezone {0!r}'.format(tz), timezones, datetime, is_dst)

        log('Expanded timezone to {0} timezones', count)

    def expand_country(self, *countries, debug=False):
        '''
        :param countries: Zero or more country codes.
        :param debug: Print an explanation of the process followed to stdout?
        :return: A sequence of timezones for the countries given.
        '''
        log = self._get_log(debug)
        count = 0
        for country in countries:
            log('Have country code {0}', country)
            zones = country_timezones[country]
            log('Country code {0} has {1} timezones', country, len(zones))
            # yield from map(timezone, zones)
            for tzinfo in map(timezone, zones): yield tzinfo
            count += len(zones)
        log('Expanded country codes to {0} timezones', count)

DEFAULT_TZ_FACTORY = PyTzFactory()


class SimpleDateParser(DebugLog):
    '''
    Automate the parsing of SimpleDate instances from strings using a series
    of formats (until one works).

    IMPORTANT: Not thread safe.
    '''

    def __init__(self, formats=DEFAULT_FORMATS):
        if isinstance(formats, str): formats = [formats]  # allow single string arg
        self._formats = MRUSortedIterable(formats)

    def parse(self, date,
              tz=None, is_dst=False, country=None, tz_factory=DEFAULT_TZ_FACTORY,
              format=None, unsafe=False, debug=False):
        '''
        Attempt to parse the string `date` using each format in turn, until
        success.  Once a parse succeeds, find the `dt.tzinfo` instance that is
        associated with the parse data (and/or supplied value, which must
        be consistent if provided).  The date is then converted to UTC.
        Finally, create a Date instance that combines the date, timezone and
        format.

        :param date: The date string to parse.
        :param tz: A time zone to use if none available in the date (`None` is
                   local).
        :param is_dst: Is the date known to be summertime?  (`None` is
                       'unknown').
        :param country: A country code (or list of codes) to restrict the
                        choice of timezone.
        :param tz_factory: Converts from the timezone text, offset, etc, to a
                           `dt.tzinfo` instance.
        :param format: `None`, or a format to store in the final Date (`None`
                       will use the format that parsed the data).
        :param unsafe: Take the first timezone found.
        :param debug: If true, print a description of the logic followed.
        :return: A SimpleDate instance, constructed from the given data.
        '''

        log = self._get_log(debug)

        for fmt in self._formats:
            try:

                tt, fraction, write_fmt = strptime(date, fmt)
                log('Raw parse results for {0}: {1!r}, {2!r}', fmt, tt, fraction)
                datetime = dt.datetime(*(tt[:6] + (fraction,)))

                zone = tt[-2]
                if zone is not None:
                    log('Parsed timezone name from date as {0}', zone)
                elif tt[-1]:
                        zone = dt.timedelta(seconds=tt[-1])
                        log('Parsed timezone offset from date as {0}', zone)

                zones = ()
                if zone is not None: zones += (zone,)
                if tz is not None: zones += (tz,)
                if not zones: zones += (None,)  # use locale
                log('Combined zones are {0}', zones)

                tzinfo = tz_factory.search(*zones, datetime=datetime, is_dst=is_dst, country=country, unsafe=unsafe, debug=debug)
                log('Resolved timezone as {0}', tzinfo)

                datetime = tzinfo_localize(tzinfo, datetime, is_dst)
                log('Parsed {0} with {1} to give {2} / {3}', date, fmt, datetime, tzinfo)
                return SimpleDate(datetime=datetime, format=write_fmt if (format is None or fmt is format) else format, unsafe=unsafe, debug=debug)

            except ValueError as e:
                log('Failed to parse {0} with {1} ({2})', date, fmt, e)
        raise SimpleDateError('Could not parse {0}', date)

DEFAULT_DATE_PARSER = SimpleDateParser()


class DateTimeWrapper:
    '''
    Provide consistent, attribute-based access to a datetime instances.
    '''

    __slots__ = ('__datetime', '__format')

    def __init__(self, datetime, format):
        self.__datetime = datetime
        self.__format = format

    @property
    def datetime(self):
        return self.__datetime

    @property
    def format(self):
        return self.__format

    @property
    def year(self):
        return self.__datetime.year

    @property
    def month(self):
        return self.__datetime.month

    @property
    def day(self):
        return self.__datetime.day

    @property
    def weekday(self):
        return self.__datetime.weekday()

    @property
    def isoweekday(self):
        return self.__datetime.isoweekday()

    @property
    def isocalendar(self):
        return self.__datetime.isocalendar()

    @property
    def hour(self):
        return self.__datetime.hour

    @property
    def minute(self):
        return self.__datetime.minute

    @property
    def second(self):
        return self.__datetime.second

    @property
    def microsecond(self):
        return self.__datetime.microsecond

    @property
    def date(self):
        return self.__datetime.date()

    @property
    def ordinal(self):
        return self.__datetime.toordinal()

    @property
    def time(self):
        return self.__datetime.timetz()

    @property
    def timestamp(self):
        # return self.__datetime.timestamp()
        return datetime_timestamp(self.__datetime)

    @property
    def tzinfo(self):
        return self.__datetime.tzinfo

    def __str__(self):
        return self.__datetime.strftime(self.__format)

    def __repr__(self):
        if isinstance(self.__datetime.tzinfo, SingleInstantTz):
            return '{0}({1!r})'.format(self.__class__.__name__, str(self))
        else:
            return '{0}({1!r}, tz={2!r})'.format(self.__class__.__name__, str(self), str(self.__datetime.tzinfo))

    def strftime(self, format):
        return self.__datetime.strftime(format)

    def __eq__(self, other):
        return isinstance(other, DateTimeWrapper) and self.__datetime == other.datetime and self.__format == other.__format

    @property
    def naive(self):
        return DateTimeWrapper(self.__datetime.replace(tzinfo=None), self.__format)

    def __lt__(self, other):
        if isinstance(other, DateTimeWrapper):
            return self.__datetime < other.__datetime or \
                   (self.__datetime == other.__datetime and self != other and repr(self) < repr(other))
        else:
            return NotImplemented

    def __gt__(self, other):
        if isinstance(other, DateTimeWrapper):
            return self.__datetime > other.__datetime or \
                   (self.__datetime == other.__datetime and self != other and repr(self) > repr(other))
        else: return NotImplemented

    def __le__(self, other):
        if isinstance(other, DateTimeWrapper): return self < other or self == other
        else: return NotImplemented

    def __ge__(self, other):
        if isinstance(other, DateTimeWrapper): return self > other or self == other
        else: return NotImplemented

    def __add__(self, other):
        if isinstance(other, dt.timedelta):
            return SimpleDate(datetime=self.__datetime+other, format=self.__format)
        else: return NotImplemented

    __radd__ = __add__

    def __sub__(self, other):
        if isinstance(other, DateTimeWrapper): return self.__datetime - other.__datetime
        elif isinstance(other, dt.timedelta):
            return SimpleDate(datetime=self.datetime-other, format=self.format)
        else: return NotImplemented


class SimpleDate(DateTimeWrapper, DebugLog):
    '''
    A formatted date and time, associated with a timezone.
    '''

    __slots__ = ()

    def __init__(self, year_or_auto=None, month=None, day=None, hour=None, minute=None, second=None, microsecond=None,
                 simple=None, datetime=None, date=None, ordinal=None, time=None, timestamp=None,
                 tz=None, is_dst=False, country=None, tz_factory=DEFAULT_TZ_FACTORY, unsafe=False,
                 format=None, date_parser=None, debug=False):
        '''
        Simple use may only require passing the first parameter, which will
        be interpreted according to its type: a string will be parsed, while
        other types behave like setting the equivalent parameter.  So passing
        a `dt.date` instance as the first argument is equivalent to calling
        with `date=...`.

        For more flexible parsing of dates in strings, consider using
        `DateParser`.

        A timestamp defines an exact time; for a timestamp the `tz` parameter
        functions as a conversion.

        All other values are defined relative to some timezone.  If this
        is present in the value then it must be consistent with any given `tz`.
        If no timezone is present in the value, and none is given, then
        the local default is used.

        So, for example:

          >>> SimpleDate(timestamp=0, tz='CLST')
          SimpleDate('1969-12-31 21:00:00.000000 CLST', tz='America/Santiago')

        will convert the UTC date for midnight, Jan 1 1970 (the Unix origin)
        to Chilean summer time (which, it turns out, is 9pm the evening before).

        In contrast, for other inputs, the given value is taken as being
        a literal value in that timezone:

          >>> SimpleDate(dt.datetime(2012, 5, 19, 12, 0, tzinfo=timezone('US/Eastern')))
          SimpleDate('2012-05-19 12:00:00.000000 EST', tz='US/Eastern')

        A string with timezone will be handled similarly:

          >>> SimpleDate('2012-05-19 12:00 EDT')
          SimpleDate('2012-05-19 12:00 EDT')

        But if the string did not have a timezone (ie just '2012-05-19 12:00')
        then it would have been assumed to have been in the timezone given:

          >>> SimpleDate('2012-05-19 12:00', tz='CLT', format=DEFAULT_FORMAT)
          SimpleDate('2012-05-19 12:00:00.000000 CLT')

        Similarly:

          >>> SimpleDate(2012, 5, 19, 12, 0, tz='CLT')
          SimpleDate('2012-05-19 12:00:00.000000 CLT')

        The `format` parameter describes the output format, used for display.
        If `None`, then an ISO-8601-like format is used, unless the value is
        parsed from a string, in which case the format used for parsing is
        preserved.

        :param year_or_auto: Either the year (if month and day also present) or a value that will be interpreted by type.
        :param month: The month, if an explicit date is being given.
        :param day: The day, if an explicit date is being given.
        :param hour: The hour, if an explicit date is being given (default 0).
        :param minute: The minute, if an explicit date is being given (default 0).
        :param second: The second, if an explicit date is being given (default 0).
        :param microsecond:  Microseconds, if an explicit date is being given (default 0).
        :param simple: An existing instance, which will be copied.
        :param datetime: A `dt.datetime`.
        :param date: A `dt.date` instance, which will be combined with `time` (default today).
        :param ordinal: A Gregorian ordinal, which will be combined with `time`.
        :param time: A `dt.time` instance, which will be combined with `date` or `ordinal` (default midnight).
        :param timestamp: A Posix timestamp (aka Unix epoch).
        :param tz: A time zone to use if none available in the date (`None` is local).
        :param is_dst: Whether the time being processed is DST (used in some corner cases to get the timezone correct - see pytz docs).
        :param country: A country code (or list of codes) (`None` means derive from `tz`).
        :param quality: Controls how the timezone is selected from multiple values: HIGH requires a unique match; MEDIUM accepts ambiguity if all offsets are the same; LOW takes the first value found.
        :param tz_factory: Used to convert `tz`, and also anything parsed from an input string, to a `dt.tzinfo` instance (default DEFAULT_TZ_FACTORY).
        :param format: The format used for output (also used to parse input string if `date_parser` is `None`).
        :param date_parser: Used to parse an input string (default DEFAULT_DATE_PARSER, combined with `format` if given).
        :param equality: How do we compare values?  See SimpleDate.EQUALITY.  Default is DEFAULT_EQUALITY unless `simple` given (in which case it is copied).
        :param unsafe: Take the first timezone found.
        :param debug: If true, print a description of the logic followed.
        :return: A Date instance, containing the given data.
        '''

        log = self._get_log(debug)

        # gentle reader, this may look like a huge, impenetrable block of
        # code, but it's actually not doing anything clever - just many small
        # steps to support the different ways the constructor can be called.

        # if none of the other 'main' arguments (that define the datetime)
        # are defined, then the `year_or_auto` parameter is treated as 'auto'
        # (if it were a year, `month` and `day` are also required).  so here we
        # examine the type and set the implicit argument, erasing year_or_auto
        # when we do so.  in this way, at the end of this section, we are in a
        # state 'as if' the constructor had been called with the correct
        # parameter set.  for example, if `year_or_auto` is a `dt.date`
        # instance we will set `date`.

        if test_all(is_none, month, day, hour, minute, second, microsecond,
                simple, time, date, datetime, timestamp, ordinal):
            log('Inferring auto argument')
            if isinstance(year_or_auto, SimpleDate):
                log('Found a DTime instance')
                simple, year_or_auto = year_or_auto, None
            # ordering important here as issubclass(datetime, date)
            elif isinstance(year_or_auto, dt.datetime):
                log('Found a datetime instance')
                datetime, year_or_auto = year_or_auto, None
            elif isinstance(year_or_auto, dt.date):
                log('Found a date instance')
                date, year_or_auto = year_or_auto, None
            elif isinstance(year_or_auto, dt.time):
                log('Found a time instance')
                time, year_or_auto = year_or_auto, None
            elif isinstance(year_or_auto, int) or isinstance(year_or_auto, float):
                log('Found a numeric value, will use as Unix epoch')
                timestamp, year_or_auto = year_or_auto, None
            elif isinstance(year_or_auto, str):
                # if we have a string, use `date_parser` to create a SimpleDate
                # instance (passing `tz`, `format`, etc) and then clear
                # everything else.
                log('Found a string, will try to parse')
                if date_parser is None:
                    if format:
                        log('Creating date parser with given format plus defaults')
                        date_parser = SimpleDateParser((format,) + DEFAULT_FORMATS)
                    else:
                        log('Using default date parser')
                        date_parser = DEFAULT_DATE_PARSER
                else:
                    log('Using given date parser')
                simple = date_parser.parse(year_or_auto, tz=tz, is_dst=is_dst, country=country, format=format, tz_factory=tz_factory, unsafe=unsafe, debug=debug)
                year_or_auto, format, tz = None, None, None  # clear tz so it's not re-checked later
            elif year_or_auto is not None:
                raise SimpleDateError('Cannot convert {0!r} for year_or_auto', year_or_auto)

        # so now the 'auto' parameter has been converted and we can address
        # the different cases the constructor handles in turn.

        # if all the date components are missing then we must process the
        # more complex types (`date`, `time`, etc).  in general, only one of
        # those is supported at a time, but there are a couple of special
        # case pairs (basically, combining dates and time) that we handle first
        # by combining them to datetime and then deleting the original
        # (similar to the way 'auto' was handled above).

        if test_all(is_none, year_or_auto, month, day, hour, minute, second, microsecond):

            # special case - convert `ordinal` to `date` and then fall through
            # to next case below (combining with time).
            if date is None and ordinal is not None:
                date = dt.date.fromordinal(ordinal)
                log('Converted ordinal {0} to date {1}', ordinal, date)
                ordinal = None

            # special case - combine date and/or time into datetime
            if datetime is None and (date is not None or time is not None):
                # the tricky part here is bootstrapping tz correctly.  we start
                # by making sure that `time` has a value.
                if time is None:
                    # we know date is defined, so use a zero time in the
                    # datetime to bootstrap the tz
                    tzinfo = tz_factory.search(tz, datetime=dt.datetime.combine(date, dt.time()), is_dst=is_dst, country=country, unsafe=unsafe, debug=debug)
                    log('Have a date, but no time, so using midnight in {0}', tzinfo)
                    time = dt.time(tzinfo=tzinfo)
                elif time.tzinfo is None:
                    # similarly, fix a naive time (TODO - we use today's UTC date - that may not be right?)
                    tzinfo = tz_factory.search(tz, datetime=dt.datetime.combine(dt.datetime.utcnow().date(), time), is_dst=is_dst, country=country, unsafe=unsafe, debug=debug)
                    log('Setting timezone for time to {0}', tzinfo)
                    time = time.replace(tzinfo=tzinfo)
                # so now we have a time that is guaranteed to exist and have
                # a valid tzinfo
                if date is None:
                    log('Have a time, but no date, so using today')
                    date = dt.datetime.now(tz=time.tzinfo).date()
                log('Combining date and time')
                datetime = reapply_tzinfo(dt.datetime.combine(date, time), is_dst)
                date, time = None, None

            # move simple to datetime here so that we can check tz below
            if simple is not None:
                datetime = simple.datetime
                log('Using datetime from simple: {0}', datetime)
                if format is None:
                    format = simple.format
                    log('Using format from simple: {0}', format)
                simple = None

            # with the special cases handled (and reduced to a single
            # `datetime`) we should have only a single parameter remaining
            # (all other combinations are unsupported).

            multiple = names(2, is_not_none, simple=simple, time=time, date=date, datetime=datetime, epoch=timestamp)
            if multiple:
                args = ', '.join(multiple)
                log('Too many, possibly contradicting, values: {0}', args)
                raise SimpleDateError('Cannot specify ' + args + ' together')

            # pick off the remaining parameters, one by one.

            if datetime is not None and tz is not None:
                # we need to check that a tzinfo that was implicit in other
                # parameters is consistent with the explicit value
                tz_factory.search(datetime.tzinfo, tz, datetime=datetime, is_dst=is_dst, country=country, unsafe=unsafe, debug=debug)
            elif time is not None:
                raise SimpleDateError('Inconsistent code: time should already have been converted')
            elif date is not None:
                raise SimpleDateError('Inconsistent code: date should already have been converted')
            elif timestamp is not None:
                log('Converting Unix epoch to datetime')
                datetime = dt.datetime.fromtimestamp(timestamp, tz=utc)
                tzinfo = tz_factory.search(tz, datetime=datetime, is_dst=is_dst, country=country, unsafe=unsafe, debug=debug)
                datetime, timestamp = dt.datetime.fromtimestamp(timestamp, tz=tzinfo), None
                datetime.replace(tzinfo=tzinfo)
            elif ordinal is not None:
                raise SimpleDateError('Inconsistent code: ordinal should already have been converted')
            elif datetime is None:
                log('Constructing a new datetime using now')
                datetime = dt.datetime.utcnow().replace(tzinfo=utc)
                tzinfo = tz_factory.search(tz, datetime=datetime, is_dst=is_dst, country=country, unsafe=unsafe, debug=debug)
                datetime = datetime.astimezone(tzinfo)

        else:

            # if we are here, then the user specified some of year, month, day
            # etc.  so we check that no conflicting parameters were given and
            # then add defaults for missing values (zeroes are supplied "from
            # the right", starting at microseconds, but it's an error to have
            # gaps, and you must have at least year, month and day).

            extra = names(1, is_not_none, simple=simple, date=date, ordinal=ordinal, time=time, timstamp=timestamp, datetime=datetime)
            if extra:
                if isinstance(year_or_auto, int):
                    raise SimpleDateError('Cannot mix {0} with year.',  ', '.join(extra))
                else:
                    raise SimpleDateError('Name multiple parameters if they are not year, month, day etc.')

            log('Constructor was called with explicit year, month, day, etc.')
            if test_any(is_none, year_or_auto, month, day):
                if test_all(is_int_or_none, year_or_auto, month, day):
                    raise SimpleDateError('The year, month and day must all be provided')
                else:
                    raise SimpleDateError('Name multiple parameters if they are not year, month, day etc.')

            spec = OrderedDict([('microsecond', microsecond), ('second', second), ('minute', minute),
                                ('hour', hour), ('day', day), ('month', month), ('year', year_or_auto)])
            for name, value in spec.items():
                if value is None:
                    log('Default ' + name + ' to zero')
                    spec[name] = 0
                else: break  # don't allow gaps
            error = names(1, is_none, **spec)
            if error: raise SimpleDateError('Missing value{0} for {1}', 's' if len(error) > 1 else '', ', '.join(error))

            log('Constructing datetime from: {0}', '; '.join('%s: %s' % (name, value) for name, value in reversed(list(spec.items()))))
            datetime = dt.datetime(**spec)
            year_or_auto, month, day, hour, minute, second, microsecond = None, None, None, None, None, None ,None

        # we should have reduced the input to a datetime and format so we do
        # some sanity checks and, if not tzinfo or format were set, use the
        # defaults.

        error = names(1, is_not_none,
                      year_or_auto=year_or_auto, month=month, day=day,
                      hour=hour, minute=minute, second=second, microsecond=microsecond,
                      simple=simple, time=time, date=date, epoch=timestamp)
        if error: raise SimpleDateError('Inconsistent code: {0} unprocessed', ', '.join(error))
        if datetime is None: raise SimpleDateError('Inconsistent code: no datetime')

        if datetime.tzinfo is None:
            tzinfo = tz_factory.search(tz, datetime=datetime, is_dst=is_dst, country=country, unsafe=unsafe, debug=debug)
            datetime = tzinfo_localize(tzinfo, datetime, is_dst)

        if format is None:
            log('Using default format ({0})', DEFAULT_FORMAT)
            format = DEFAULT_FORMAT

        super().__init__(datetime, format)

        log('Created {0}', self)

    def convert(self, tz=None, format=None, is_dst=False, country=None, tz_factory=DEFAULT_TZ_FACTORY, unsafe=False, debug=False):
        if tz is None and country is None:
            # avoid expanding this, because it might be a SingleInstantTimezone
            tz = self.tzinfo
        else:
            zones = () if tz is None else (tz,)
            tz = tz_factory.search(*zones, datetime=self.datetime, is_dst=is_dst, country=country, unsafe=unsafe, debug=debug)
        if format is None: format = self.format
        return SimpleDate(datetime=tz.normalize(self.datetime.astimezone(tz)), format=format)

    @property
    def utc(self):
        return self.convert(utc)

    @property
    def normalized(self):
        return self.convert(utc, format=DEFAULT_FORMAT)


FACTORIES = local()

def get_local(name, builder):
    '''
    Helper for thread local data.

    :param name: The name of the attribute to get.
    :param builder: A thunk to evaluate to generate the default value if missing.
    :return: The current value of the attribute.
    '''
    value = getattr(FACTORIES, name, None)
    if value is None:
        value = builder()
        setattr(FACTORIES, name, value)
    return value

def best_guess_utc(date, debug=False):
    '''
    Try US timezones with US formats, then everything else.

    :param date: A date to parse.
    :param debug: If true, print a description of the logic followed.
    :return: A UTC datetime.
    '''
    us_date_parser = get_local('us_date_parser', lambda: SimpleDateParser(MONTH_FIRST + DEFAULT_FORMATS))
    eu_date_parser = get_local('eu_date_parser', lambda: SimpleDateParser(DAY_FIRST + DEFAULT_FORMATS))
    us_tz_factory = get_local('us_tz_factory', lambda: PyTzFactory(all_timezones, countries=['US']))
    eu_tz_factory = get_local('eu_tz_factory', lambda: PyTzFactory(all_timezones, countries=exclude('US')))
    try:
        date = SimpleDate(date, date_parser=us_date_parser, tz_factory=us_tz_factory, unsafe=True, debug=debug)
    except SimpleDateError:
        date = SimpleDate(date, date_parser=eu_date_parser, tz_factory=eu_tz_factory, unsafe=True, debug=debug)
    return date.utc.datetime



# the routines below are copied from _strptime.py, except that the
# definition for timezone (Z) is changed from a list of specific options
# to a general pattern.

try:
    from _thread import allocate_lock as _thread_allocate_lock
except ImportError:
    from _dummy_thread import allocate_lock as _thread_allocate_lock
from _strptime import _getlang, LocaleTime, _calc_julian_from_U_or_W
from datetime import (date as datetime_date)
import time
from re import compile as re_compile
from re import escape as re_escape
from re import IGNORECASE

class TimeRE(dict):
    """Handle conversion from format directives to regexes."""

    def __init__(self, locale_time=None):
        """Create keys/values.

        Order of execution is important for dependency reasons.

        """
        if locale_time:
            self.locale_time = locale_time
        else:
            self.locale_time = LocaleTime()
        base = super()
        base.__init__({
            # The " \d" part of the regex is to make %c from ANSI C work
            'd': r"(?P<d>3[0-1]|[1-2]\d|0[1-9]|[1-9]| [1-9])",
            'f': r"(?P<f>[0-9]{1,6})",
            'H': r"(?P<H>2[0-3]|[0-1]\d|\d)",
            'I': r"(?P<I>1[0-2]|0[1-9]|[1-9])",
            'j': r"(?P<j>36[0-6]|3[0-5]\d|[1-2]\d\d|0[1-9]\d|00[1-9]|[1-9]\d|0[1-9]|[1-9])",
            'm': r"(?P<m>1[0-2]|0[1-9]|[1-9])",
            'M': r"(?P<M>[0-5]\d|\d)",
            'S': r"(?P<S>6[0-1]|[0-5]\d|\d)",
            'U': r"(?P<U>5[0-3]|[0-4]\d|\d)",
            'w': r"(?P<w>[0-6])",
            # W is set below by using 'U'
            'y': r"(?P<y>\d\d)",
            #XXX: Does 'Y' need to worry about having less or more than
            #     4 digits?
            'Y': r"(?P<Y>\d\d\d\d)",
            'z': r"(?P<z>[+-]\d\d[0-5]\d)",
            'A': self.__seqToRE(self.locale_time.f_weekday, 'A'),
            'a': self.__seqToRE(self.locale_time.a_weekday, 'a'),
            'B': self.__seqToRE(self.locale_time.f_month[1:], 'B'),
            'b': self.__seqToRE(self.locale_time.a_month[1:], 'b'),
            'p': self.__seqToRE(self.locale_time.am_pm, 'p'),
            'Z': r"(?P<Z>[A-Z][A-Za-z_]+(?:/[A-Z][A-Za-z_]+)+|[A-Z]{3,})",
            '%': '%'})
        base.__setitem__('W', base.__getitem__('U').replace('U', 'W'))
        base.__setitem__('c', self.pattern(self.locale_time.LC_date_time))
        base.__setitem__('x', self.pattern(self.locale_time.LC_date))
        base.__setitem__('X', self.pattern(self.locale_time.LC_time))

    def __seqToRE(self, to_convert, directive):
        """Convert a list to a regex string for matching a directive.

        Want possible matching values to be from longest to shortest.  This
        prevents the possibility of a match occuring for a value that also
        a substring of a larger value that should have matched (e.g., 'abc'
        matching when 'abcdef' should have been the match).

        """
        to_convert = sorted(to_convert, key=len, reverse=True)
        for value in to_convert:
            if value != '':
                break
        else:
            return ''
        regex = '|'.join(re_escape(stuff) for stuff in to_convert)
        regex = '(?P<%s>%s' % (directive, regex)
        return '%s)' % regex

    def pattern(self, format):
        """Return regex pattern for the format string.

        Need to make sure that any characters that might be interpreted as
        regex syntax are escaped.

        """
        processed_format = ''
        # The sub() call escapes all characters that might be misconstrued
        # as regex syntax.  Cannot use re.escape since we have to deal with
        # format directives (%m, etc.).
        regex_chars = re_compile(r"([\\.^$*+?\(\){}\[\]|])")
        format = regex_chars.sub(r"\\\1", format)
        whitespace_replacement = re_compile('\s+')
        format = whitespace_replacement.sub('\s+', format)
        while '%' in format:
            directive_index = format.index('%')+1
            processed_format = "%s%s%s" % (processed_format,
                                           format[:directive_index-1],
                                           self[format[directive_index]])
            format = format[directive_index+1:]
        return "%s%s" % (processed_format, format)

    def compile(self, format):
        """Return a compiled re object for the format string."""
        return re_compile(self.pattern(format), IGNORECASE)

_cache_lock = _thread_allocate_lock()
# DO NOT modify _TimeRE_cache or _regex_cache without acquiring the cache lock
# first!
_TimeRE_cache = TimeRE()
_CACHE_MAX_SIZE = 5 # Max number of regexes stored in _regex_cache
_regex_cache = {}

def _strptime(data_string, format="%a %b %d %H:%M:%S %Y"):
    """Return a 2-tuple consisting of a time struct and an int containing
    the number of microseconds based on the input string and the
    format string."""

    for index, arg in enumerate([data_string, format]):
        if not isinstance(arg, str):
            msg = "strptime() argument {} must be str, not {}"
            raise TypeError(msg.format(index, type(arg)))

    global _TimeRE_cache, _regex_cache
    with _cache_lock:

        if _getlang() != _TimeRE_cache.locale_time.lang:
            _TimeRE_cache = TimeRE()
            _regex_cache.clear()
        if len(_regex_cache) > _CACHE_MAX_SIZE:
            _regex_cache.clear()
        locale_time = _TimeRE_cache.locale_time
        format_regex = _regex_cache.get(format)
        if not format_regex:
            try:
                format_regex = _TimeRE_cache.compile(format)
            # KeyError raised when a bad format is found; can be specified as
            # \\, in which case it was a stray % but with a space after it
            except KeyError as err:
                bad_directive = err.args[0]
                if bad_directive == "\\":
                    bad_directive = "%"
                del err
                raise ValueError("'%s' is a bad directive in format '%s'" %
                                    (bad_directive, format))
            # IndexError only occurs when the format string is "%"
            except IndexError:
                raise ValueError("stray %% in format '%s'" % format)
            _regex_cache[format] = format_regex
    found = format_regex.match(data_string)
    if not found:
        raise ValueError("time data %r does not match format %r" %
                         (data_string, format))
    if len(data_string) != found.end():
        raise ValueError("unconverted data remains: %s" %
                          data_string[found.end():])

    year = None
    month = day = 1
    hour = minute = second = fraction = 0
    tz = -1
    tzoffset = None
    # Default to -1 to signify that values not known; not critical to have,
    # though
    week_of_year = -1
    week_of_year_start = -1
    # weekday and julian defaulted to -1 so as to signal need to calculate
    # values
    weekday = julian = -1
    found_dict = found.groupdict()
    for group_key in found_dict.keys():
        # Directives not explicitly handled below:
        #   c, x, X
        #      handled by making out of other directives
        #   U, W
        #      worthless without day of the week
        if group_key == 'y':
            year = int(found_dict['y'])
            # Open Group specification for strptime() states that a %y
            #value in the range of [00, 68] is in the century 2000, while
            #[69,99] is in the century 1900
            if year <= 68:
                year += 2000
            else:
                year += 1900
        elif group_key == 'Y':
            year = int(found_dict['Y'])
        elif group_key == 'm':
            month = int(found_dict['m'])
        elif group_key == 'B':
            month = locale_time.f_month.index(found_dict['B'].lower())
        elif group_key == 'b':
            month = locale_time.a_month.index(found_dict['b'].lower())
        elif group_key == 'd':
            day = int(found_dict['d'])
        elif group_key == 'H':
            hour = int(found_dict['H'])
        elif group_key == 'I':
            hour = int(found_dict['I'])
            ampm = found_dict.get('p', '').lower()
            # If there was no AM/PM indicator, we'll treat this like AM
            if ampm in ('', locale_time.am_pm[0]):
                # We're in AM so the hour is correct unless we're
                # looking at 12 midnight.
                # 12 midnight == 12 AM == hour 0
                if hour == 12:
                    hour = 0
            elif ampm == locale_time.am_pm[1]:
                # We're in PM so we need to add 12 to the hour unless
                # we're looking at 12 noon.
                # 12 noon == 12 PM == hour 12
                if hour != 12:
                    hour += 12
        elif group_key == 'M':
            minute = int(found_dict['M'])
        elif group_key == 'S':
            second = int(found_dict['S'])
        elif group_key == 'f':
            s = found_dict['f']
            # Pad to always return microseconds.
            s += "0" * (6 - len(s))
            fraction = int(s)
        elif group_key == 'A':
            weekday = locale_time.f_weekday.index(found_dict['A'].lower())
        elif group_key == 'a':
            weekday = locale_time.a_weekday.index(found_dict['a'].lower())
        elif group_key == 'w':
            weekday = int(found_dict['w'])
            if weekday == 0:
                weekday = 6
            else:
                weekday -= 1
        elif group_key == 'j':
            julian = int(found_dict['j'])
        elif group_key in ('U', 'W'):
            week_of_year = int(found_dict[group_key])
            if group_key == 'U':
                # U starts week on Sunday.
                week_of_year_start = 6
            else:
                # W starts week on Monday.
                week_of_year_start = 0
        elif group_key == 'z':
            z = found_dict['z']
            tzoffset = int(z[1:3]) * 60 + int(z[3:5])
            if z.startswith("-"):
                tzoffset = -tzoffset
        elif group_key == 'Z':
            # Since -1 is default value only need to worry about setting tz if
            # it can be something other than -1.
            found_zone = found_dict['Z'].lower()
            for value, tz_values in enumerate(locale_time.timezone):
                if found_zone in tz_values:
                    # Deal with bad locale setup where timezone names are the
                    # same and yet time.daylight is true; too ambiguous to
                    # be able to tell what timezone has daylight savings
                    if (time.tzname[0] == time.tzname[1] and
                       time.daylight and found_zone not in ("utc", "gmt")):
                        break
                    else:
                        tz = value
                        break
    leap_year_fix = False
    if year is None and month == 2 and day == 29:
        year = 1904  # 1904 is first leap year of 20th century
        leap_year_fix = True
    elif year is None:
        year = 1900
    # If we know the week of the year and what day of that week, we can figure
    # out the Julian day of the year.
    if julian == -1 and week_of_year != -1 and weekday != -1:
        week_starts_Mon = True if week_of_year_start == 0 else False
        julian = _calc_julian_from_U_or_W(year, week_of_year, weekday,
                                            week_starts_Mon)
    # Cannot pre-calculate datetime_date() since can change in Julian
    # calculation and thus could have different value for the day of the week
    # calculation.
    if julian == -1:
        # Need to add 1 to result since first day of the year is 1, not 0.
        julian = datetime_date(year, month, day).toordinal() - \
                  datetime_date(year, 1, 1).toordinal() + 1
    else:  # Assume that if they bothered to include Julian day it will
           # be accurate.
        datetime_result = datetime_date.fromordinal((julian - 1) + datetime_date(year, 1, 1).toordinal())
        year = datetime_result.year
        month = datetime_result.month
        day = datetime_result.day
    if weekday == -1:
        weekday = datetime_date(year, month, day).weekday()
    # Add timezone info
    tzname = found_dict.get("Z")
    if tzoffset is not None:
        gmtoff = tzoffset * 60
    else:
        gmtoff = None

    if leap_year_fix:
        # the caller didn't supply a year but asked for Feb 29th. We couldn't
        # use the default of 1900 for computations. We set it back to ensure
        # that February 29th is smaller than March 1st.
        year = 1900

    return (year, month, day,
            hour, minute, second,
            weekday, julian, tz, tzname, gmtoff), fraction
