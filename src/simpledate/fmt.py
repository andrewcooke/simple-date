from functools import lru_cache

try:
    from _thread import allocate_lock as _thread_allocate_lock
except ImportError:
    from _dummy_thread import allocate_lock as _thread_allocate_lock
from _strptime import LocaleTime, _calc_julian_from_U_or_W
from collections import defaultdict
from datetime import date
import time
from re import sub, escape, compile, IGNORECASE


# extend the usual date parsing with:
# - optional matching by adding a trailing ?
# - space used to be \s+ to space? is \s*
# - nestable grouping and alternatives as {A|B|C}
#   use {} rather than () as less likely to appear in real text
# - modify matchers for textual day, month, timezone that match any string
#   by adding a trailing !
# - similarly, %z! allows ":" between H and M
# - generation of the "equivalent format" for display after parsing
# escaping is by prefixing with %.

# so the following are similar:
# ISO_8601 = add_timezone('%Y-%m-%d %H:%M:%S.%f', '%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M', '%Y-%m-%d', '%Y')
# %Y{-%m{-%d{{ |T}%H:%M{:%S{.%f}?}?}}?}? !{%Z!|%z!}?


def tokenizer(fmt):
    i = 0
    n = len(fmt)

    while i < n:
        j = i

        # if we have a symbol, include that
        if fmt[i] == '%':
            j += 1
            if j == n:
                raise ValueError('Missing token (nothing follows %)')

        # include a trailing !
        if j + 1 < n and fmt[j+1] == '!':
            j += 1

        # if we have a trailing ? then enclose anything not in parens so
        # that we generate the regexp marker to test for inclusion
        optional = j + 1 < n and fmt[j+1] == '?'
        if optional and fmt[i] != '}':
            yield '{'
        yield fmt[i:j+1]
        if optional and fmt[i] != '}':
            yield '}'
        if optional:
            yield '?'
            j += 1

        i = j + 1


def _to_regexp(fmt, substitutions=None):

    if substitutions is None:
        substitutions = DEFAULT_SUBSTITUTIONS

    # escape things that are related to regexps
    fmt = sub(r"([\\.^$*+\(\)\[\]])", r"\\\1", fmt)
    fmt = sub('\s+', ' ', fmt)

    # we build a set of templates that can be used to construct the pattern
    # that would match the data.  we do this by tracking whether each group
    # is matched (by adding a unique name that matches the empty string) and
    # substituting the template for that group when it does (that comes later -
    # here we're just constructing the templates).  see the tests for
    # examples that might help clarify how it works.
    count = 0  # latest group
    stack = [0]  # nested groups
    rebuild = defaultdict(lambda: '')  # group substitutions

    regexp = ''
    tokens = tokenizer(fmt)

    def append(read, write=None):
        nonlocal regexp
        regexp += read
        if write is None:
            write = read
        if write.endswith('!'):
            write = write[:-1]
        rebuild['G%d' % stack[-1]] += write

    try:
        while True:
            tok = next(tokens)
            if len(tok) > 1 or tok == ' ':
                if tok in substitutions:
                    append(substitutions[tok], tok)
                else:
                    raise ValueError('Unknown symbol: %s' % tok)
            elif tok == '{':
                count += 1
                append('((?P<G%d>)' % count, '%%G%d%%' % count)
                stack.append(count)
            elif tok == '|':
                if not stack.pop():
                    raise ValueError('Unexpected | (must be within {...})')
                count += 1
                append('|(?P<G%d>)' % count, '%%G%d%%' % count)
                stack.append(count)
            elif tok == '}':
                append(')', '')
                if not stack.pop():
                    raise ValueError('Unbalanced }')
            elif tok == '?':
                append('?', '')
            else:
                append(tok)
    except StopIteration:
        pass
    if stack != [0]:
        raise ValueError('Unbalanced {')

    return regexp, rebuild, compile(regexp, IGNORECASE)


TAG = compile(r'(?:^|[^%])%(G\d+)%')

def reconstruct(rebuild, found_dict):
    fmt = rebuild['G0']
    while True:
        match = TAG.search(fmt)
        if not match:
            return sub(r'\\(.)', r'\1', fmt)
        index = match.group(1)
        if found_dict.get(index) is None:
            replacement = ''
        else:
            replacement = rebuild[index]
        fmt = fmt[:match.start(1)-1] + replacement + fmt[match.end(1)+1:]


LOCALE_TIME = LocaleTime()


def seq_to_re(to_convert, directive):
    '''Copied from strptime method'''
    to_convert = sorted(to_convert, key=len, reverse=True)
    for value in to_convert:
        if value != '':
            break
    else:
        return ''
    regex = '|'.join(escape(stuff) for stuff in to_convert)
    regex = '(?P<%s>%s' % (directive, regex)
    return '%s)' % regex


BASE_SUBSTITUTIONS = {
    ' ': '\s+',
    '%a': seq_to_re(LOCALE_TIME.a_weekday, 'a'),
    '%A': seq_to_re(LOCALE_TIME.f_weekday, 'A'),
    '%b': seq_to_re(LOCALE_TIME.a_month[1:], 'b'),
    '%B': seq_to_re(LOCALE_TIME.f_month[1:], 'B'),
    '%d': r'(?P<d>3[0-1]|[1-2]\d|0[1-9]|[1-9]| [1-9])',
    '%f': r'(?P<f>[0-9]{1,6})',
    '%H': r'(?P<H>2[0-3]|[0-1]\d|\d)',
    '%I': r'(?P<I>1[0-2]|0[1-9]|[1-9])',
    '%j': r'(?P<j>36[0-6]|3[0-5]\d|[1-2]\d\d|0[1-9]\d|00[1-9]|[1-9]\d|0[1-9]|[1-9])',
    '%m': r'(?P<m>1[0-2]|0[1-9]|[1-9])',
    '%p': seq_to_re(LOCALE_TIME.am_pm, 'p'),
    '%M': r'(?P<M>[0-5]\d|\d)',
    '%S': r'(?P<S>6[0-1]|[0-5]\d|\d)',
    '%U': r'(?P<U>5[0-3]|[0-4]\d|\d)',
    '%w': r'(?P<w>[0-6])',
    '%W': r'(?P<W>5[0-3]|[0-4]\d|\d)',
    '%y': r'(?P<y>\d\d)',
    '%Y': r'(?P<Y>\d\d\d\d)',
    '%z': r'(?P<z>[+-]\d\d[0-5]\d)',
    '%Z': r'(?P<Z>[A-Z][A-Za-z_]+(?:/[A-Z][A-Za-z_]+)+|[A-Z]{3,})',
    '%%': '%',
}

PYTHON_SUBSTITUTIONS = dict(BASE_SUBSTITUTIONS)
PYTHON_SUBSTITUTIONS.update({
    '%c': _to_regexp(LOCALE_TIME.LC_date_time, BASE_SUBSTITUTIONS)[0],
    '%x': _to_regexp(LOCALE_TIME.LC_date, BASE_SUBSTITUTIONS)[0],
    '%X': _to_regexp(LOCALE_TIME.LC_time, BASE_SUBSTITUTIONS)[0],
})

DEFAULT_SUBSTITUTIONS = dict(PYTHON_SUBSTITUTIONS)
DEFAULT_SUBSTITUTIONS.update({
    ' !': r'[^\w]+',
    '%a!': r'(?P<a>\w(?<=[^\d_]))',
    '%A!': r'(?P<A>\w(?<=[^\d_]))',
    '%b!': r'(?P<b>\w(?<=[^\d_]))',
    '%B!': r'(?P<B>\w(?<=[^\d_]))',
    '%Z!': r'(?P<Z>[A-Z][A-Za-z_]+(?:/[A-Z][A-Za-z_]+)+|[A-Z]{3,})',
})



CACHE_MAX_SIZE = 100
_CACHE_LOCK = _thread_allocate_lock()
_CACHED_REGEXP = lru_cache(maxsize=CACHE_MAX_SIZE)(_to_regexp)

def to_regexp(fmt, substitutions=None):
    with _CACHE_LOCK:
        return _CACHED_REGEXP(fmt, substitutions)


def int_or_default(dict_value, default):
    return default if dict_value is None else int(dict_value)



def to_time_tuple(found_dict):
    year = None
    month = day = 1
    hour = minute = second = fraction = 0
    tz = -1
    tzoffset = None
    # Default to -1 to signify that values not known; not critical to have
    week_of_year = -1
    week_of_year_start = -1
    # weekday and julian defaulted to -1 so as to signal need to calculate
    weekday = julian = -1
    for group_key in found_dict.keys():
        # Directives not explicitly handled below:
        #   c, x, X
        #      handled by making out of other directives
        #   U, W
        #      worthless without day of the week
        if group_key == 'y':
            year = int_or_default(found_dict['y'], year)
            # Open Group specification for strptime() states that a %y
            #value in the range of [00, 68] is in the century 2000, while
            #[69,99] is in the century 1900
            if year <= 68:
                year += 2000
            else:
                year += 1900
        elif group_key == 'Y':
            year = int_or_default(found_dict['Y'], year)
        elif group_key == 'm':
            month = int_or_default(found_dict['m'], month)
        elif group_key == 'B':
            month = LOCALE_TIME.f_month.index(found_dict['B'].lower())
        elif group_key == 'b':
            month = LOCALE_TIME.a_month.index(found_dict['b'].lower())
        elif group_key == 'd':
            day = int_or_default(found_dict['d'], day)
        elif group_key == 'H':
            hour = int_or_default(found_dict['H'], hour)
        elif group_key == 'I':
            hour = int_or_default(found_dict['I'], hour)
            ampm = found_dict.get('p', '').lower()
            # If there was no AM/PM indicator, we'll treat this like AM
            if ampm in ('', LOCALE_TIME.am_pm[0]):
                # We're in AM so the hour is correct unless we're
                # looking at 12 midnight.
                # 12 midnight == 12 AM == hour 0
                if hour == 12:
                    hour = 0
            elif ampm == LOCALE_TIME.am_pm[1]:
                # We're in PM so we need to add 12 to the hour unless
                # we're looking at 12 noon.
                # 12 noon == 12 PM == hour 12
                if hour != 12:
                    hour += 12
        elif group_key == 'M':
            minute = int_or_default(found_dict['M'], minute)
        elif group_key == 'S':
            second = int_or_default(found_dict['S'], second)
        elif group_key == 'f':
            s = found_dict['f']
            # Pad to always return microseconds.
            s += "0" * (6 - len(s))
            fraction = int(s)
        elif group_key == 'A':
            weekday = LOCALE_TIME.f_weekday.index(found_dict['A'].lower())
        elif group_key == 'a':
            weekday = LOCALE_TIME.a_weekday.index(found_dict['a'].lower())
        elif group_key == 'w':
            weekday = int_or_default(found_dict['w'], weekday)
            if weekday == 0:
                weekday = 6
            else:
                weekday -= 1
        elif group_key == 'j':
            julian = int_or_default(found_dict['j'], julian)
        elif group_key in ('U', 'W'):
            week_of_year = int_or_default(found_dict[group_key], week_of_year)
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
            for value, tz_values in enumerate(LOCALE_TIME.timezone):
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
    # Cannot pre-calculate date() since can change in Julian
    # calculation and thus could have different value for the day of the week
    # calculation.
    if julian == -1:
        # Need to add 1 to result since first day of the year is 1, not 0.
        julian = date(year, month, day).toordinal() - \
                  date(year, 1, 1).toordinal() + 1
    else:  # Assume that if they bothered to include Julian day it will
           # be accurate.
        datetime_result = date.fromordinal((julian - 1) + date(year, 1, 1).toordinal())
        year = datetime_result.year
        month = datetime_result.month
        day = datetime_result.day
    if weekday == -1:
        weekday = date(year, month, day).weekday()
    # Add timezone info
    tzname = found_dict.get('Z')
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


def strptime(data_string, format="%a %b %d %H:%M:%S %Y"):
    '''Closely based on _strptime in standard Python.'''

    for index, arg in enumerate([data_string, format]):
        if not isinstance(arg, str):
            msg = "strptime() argument {} must be str, not {}"
            raise TypeError(msg.format(index, type(arg)))

    _, rebuild, format_regex = to_regexp(format)
    found = format_regex.match(data_string)
    if not found:
        raise ValueError("time data %r does not match format %r" %
                         (data_string, format))
    if len(data_string) != found.end():
        raise ValueError("unconverted data remains: %s" %
                          data_string[found.end():])

    date_time, fraction = to_time_tuple(found.groupdict())
    write_format = reconstruct(rebuild, found.groupdict())

    return date_time, fraction, write_format
