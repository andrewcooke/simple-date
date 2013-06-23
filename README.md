simple-date
===========

A wrapper around the
[datetime](http://docs.python.org/3/library/datetime.html#module-datetime),
[pytz](http://pytz.sourceforge.net/) and
[tzlocal](https://pypi.python.org/pypi/tzlocal)
packages for Python 3.2+.
[Full docs](#documentation) below.

Examples
--------

Just give me a UTC datetime for these dates!

```python
>>> for date in '1/6/2013 BST', '1/6/2013 EST', 'Tue, 18 Jun 2013 12:19:09 -0400':
>>>     print(best_guess_utc(date))
2013-05-31 23:00:00+00:00
2013-01-06 05:00:00+00:00
2013-06-18 16:19:09+00:00
```

What time is it now, in New York?

```python
>>> SimpleDate(tz='America/New_York')
SimpleDate('2013-06-14 13:14:17.295943 EDT', tz='America/New_York')
```

And what time is that in the UK (the country code is for Great Britain)?

```python
>>> SimpleDate('2013-06-14 13:14:17.295943 EDT').convert(country='GB')
SimpleDate('2013-06-14 18:14:17.295943 BST', tz='Europe/London')
```

What is the UTC for this email date?

```python
>>> SimpleDate('Fri, 14 Jun 2013 13:13:42 -0400').utc
SimpleDate('Fri, 14 Jun 2013 17:13:42 +0000', tz='UTC')
```

What's the date a week from now (I live in Chile)?

```python
>>> SimpleDate() + timedelta(days=7)
SimpleDate('2013-06-21 13:55:20.791519 CLT', tz='America/Santiago')
```

The day of the week for Xmas this year?

```python
>>> SimpleDate(2013, 12, 24).weekday
1
```

And as a naive datetime?

```python
>>> SimpleDate(2013, 12, 24).naive.datetime
datetime.datetime(2013, 12, 24, 0, 0)
```

What's the time in EST for epoch 1234567890?

```python
>>> SimpleDate(1234567890, tz='EST')
AmbiguousTimezone: 3 distinct timezones found: <'EST'>; <'Australia/NSW'>; ...
```

Whoa!  What are those crazy Australians doing?  Let's force the USA (only):

```python
>>> SimpleDate(1234567890, tz='EST', country='US')
SimpleDate('2009-02-13 18:31:30.000000 EST')
```

Alternatively, we could give priority to the USA and take the first solution
we find:

```python
>>> SimpleDate(1234567890, tz='EST', country=prefer('US'), unsafe=True)
SimpleDate('2009-02-13 18:31:30.000000 EST')
```

And what day is that?

```python
>>> SimpleDate(1234567890, tz='EST', country=prefer('US'), unsafe=True).strftime('%A')
'Friday'
```

Documentation
-------------

* [Installation](#installation)
* [Common Concepts and Parameters](#common-concepts-and-parameters)
  * [Timezone - tz](#timezone---tz)
  * [Daylight Saving Time - is_dst](#daylight-saving-time---is_dst)
  * [Country Code - country](#country-code---country)
  * [TZ Factory - tz_factory](#tz-factory---tz_factory)
  * [First Found - unsafe](#first-found---unsafe)
  * [Format - format](#format---format)
  * [Date Parser - date_parser](#date-parser---date_parser)
  * [Debugging - debug](#debugging---debug)
* [Complete API](#complete-api)
  * [SimpleDate](#simpledate)
     * [Constructor](#constructor)
     * [Attributes](#attributes)
     * [Operators](#operators)
     * [Conversion](#conversion)
     * [Replacement](#replacement)
  * [SimpleDateParser](#simpledateparser)
     * [Constructor](#constructor-1)
     * [Parsing](#parsing)
  * [PyTzFactory](#pytzfactory)
     * [Constructor](#constructor-2)
     * [Timezone Search](#timezone-search)
     * [Other Methods](#other-methods)
  * [Functions for tzinfo](#functions-for-tzinfo)
  * [Best Guess UTC](#best-guess-utc)
* [FAQ](#faq)
  * [What is the Licence?](#what-is-the-licence)
  * [Are You Supporting this Code?](#are-you-supporting-this-code)
  * [Why Python 3.2+?](#why-python-32)
  * [Is the Library Thread Safe?](#is-the-library-thread-safe)
  * [Why Did I Get the Error "Could not parse ..."?](#why-did-i-get-the-error-could-not-parse-)
  * [Why Did I Get the Error "No timezone found"?](#why-did-i-get-the-error-no-timezone-found-)
  * [Why Did I Get the Error "AmbiguousTimezone: ..."?](#why-did-i-get-the-error-ambiguoustimezone-)
  * [Why Did I Get the Error "SingleInstantTzError ..."?](#why-did-i-get-the-error-singleinstanttzerror-)
  * [What is the Best Way to Use this Library?](#what-is-the-best-way-to-use-this-library)
* [Background](#background)
  * [Classifying Timezones](#classifying-timezones)
  * [The Need for Search](#the-need-for-search)

Installation
------------

Please install from [PyPI](https://pypi.python.org/pypi/simple-date).

First, optionally, make a virtualenv:

```sh
virtualenv env
source ./env/bin/activate
```

Then install all the packages:

```sh
pip install pytz tzlocal simple-date
```

Common Concepts and Parameters
------------------------------

### Timezone - tz

You can specify a timezone in various different ways (I've omitted any date
in the examples below, so the results show "now" when I was writing these docs):

* a name, as a string;

    ```python
    >>> SimpleDate(tz='EDT')
    SimpleDate('2013-06-17 19:48:35.556400 EDT')
    >>> SimpleDate(tz='America/New_York')
    SimpleDate('2013-06-17 19:48:43.662401 EDT', tz='America/New_York')
    ```

* an offset relative to UTC in minutes or as a timedelta instance (I'm
  specifying the [format](#format) to switch from name to numerical offset,
  as these tzinfo instances don't have a name);

    ```python
    >>> SimpleDate(tz=120, format='%Y-%m-%d %z')
    SimpleDate('2013-06-18 +0200', tz='pytz.FixedOffset(120)')
    >>> SimpleDate(tz=datetime.timedelta(minutes=60), format='%Y-%m-%d %z')
    SimpleDate('2013-06-18 +0100', tz='pytz.FixedOffset(60)')
    ```

* using an existing tzinfo instance;

    ```python
    >>> SimpleDate(tz=pytz.timezone('UTC'))
    SimpleDate('2013-06-17 23:50:59.141497 UTC', tz='UTC')
    ```

* and if you give a tuple, either value might be used.

    ```python
    >>> SimpleDate(tz=('CLT', 'CLST'))
    SimpleDate('2013-06-17 19:52:17.384333 CLT')
    ```

Finally, if you give a timezone that conflicts with the timezone in another
parameter, you're going to have a bad time:

```python
>>> SimpleDate('2013-06-17 EDT', tz='America/New_York')
SimpleDate('2013-06-17 EDT', tz='America/New_York')
>>> SimpleDate('2013-06-17 EDT', tz='America/Santiago')
simpledate.NoTimezone: No timezone found (timezones=['EDT', 'America/Santiago'], ...)
```

### Daylight Saving Time - is_dst

Is the date currently being processed in daylight savings?

This may seem an odd thing to specify, but is needed when the clocks "go back"
in a geographic timezone.  For example, in Chile, daylight saving time 2012
ended at midnight on Sunday, 28 April.  At that moment the clocks went back an
hour and it was 11pm again!  So the time 11:30pm on Sunday 8 September in the
timezone America/Santiago was ambiguous.  And the parameter `is_dst` will
resolve that ambiguity if you happen to need it:

```python
>>> fmt = '%H:%M %Z'
>>> SimpleDate('2012-04-28 23:30', tz='America/Santiago', is_dst=False, format=fmt)
SimpleDate('23:30 CLT', tz='America/Santiago')
>>> SimpleDate('2012-04-28 23:30', tz='America/Santiago', is_dst=True, format=fmt)
SimpleDate('23:30 CLST', tz='America/Santiago')
```

If you set this to `None`, then, when needed, you get an error:

```python
>>> SimpleDate('2012-04-28 23:30', tz='America/Santiago', is_dst=None)
pytz.exceptions.AmbiguousTimeError: 2012-04-28 23:30:00
```

So by default it is set to `False`, which avoids unexpected errors at the
cost of resolving them to normal (ie not daylight saving) time.

### Country Code - country

Giving a country code, or tuple of codes, restricts the search for a timezone
to the timezones used in those countries.

For example, the timezone EST means something different in the USA and
Australia:

```python
>>> SimpleDate('2013-01-01', tz='EST')
AmbiguousTimezone: 3 distinct timezones found: <'EST'>; <'Australia/Sydney'>.
```

We can remove this ambiguity by specifying the country code `'US'`:

```python
>>> SimpleDate('2013-01-01', tz='EST', country='US')
SimpleDate('2013-01-01')
```

Two useful helper functions are `prefer(code, code, ...)` and
`except(code, code, ...)` whose results can be passed to `country=...`.
The `prefer(...)` function returns all country codes, but places the given
codes first, while `except(...)` returns all codes except those given as
arguments.

### TZ Factory - tz_factory

Provide a [PyTzFactory](#pytzfactory) that is used to find the timezone.
By default all calls to the API used `DEAULTT_TZ_FACTORY`.

This is useful in two cases:

1. With multiple threads.  The code is *not* thread safe, so if you are
   creating [SimpleDate] instances in multiple threads then each thread *must*
   have its own factory.

   ```python
   >>> local_factory = PyTzFactory()
   >>> SimpleDate('2013-06-18', tz_factory=local_factory)
   ```

2. To give exact control over which timezones are used.  For example, to
   use only timezones with an 'x':

   ```python
   >>> x_timezones = PyTzFactory([z for z in pytz.all_timezones if 'x' in str(z)])
   >>> SimpleDate('2013-06-18 XYZ', tz_factory=x_timezones)
   ```

### First Found - unsafe

Setting `unsafe=True` will return the first timezone found.  This is dangerous
because no exception is generated for [ambiguous values](#the-need-for-search),
but it also has two advantages:

1. It's faster.  The timezone factory doesn't search all possibilities.

2. Because [country](#country-code---country) sets the order in which the
   zones are checked, this gives control over how ambiguous timezones are
   resolved.

   A good example is the timezone EST, which can be used in both the USA and
   Australia.  If we set `country=prefer('US')` then the American timezones
   are checked first:

   ```python
   >>> SimpleDate(1234567890, tz='EST')
   AmbiguousTimezone: 3 distinct timezones found: <'EST'>; <'Australia/NSW'>; ...
   >>> SimpleDate(1234567890, tz='EST', country=prefer('US'), unsafe=True)
   SimpleDate('2009-02-13 18:31:30.000000 EST')
   ```

### Format - format

The format used to parse and display strings.  For display, this is the same
as the
[standard Python format](http://docs.python.org/3/library/datetime.html#strftime-and-strptime-behavior).

For parsing, it has been extended to:

* Grouping and alternatives with `{...|...|...}`.  For example `'{%Z|%z}'`
  would match either timezone name or a numeric offset.

* Optional values with `?`.  For example `'%H ?%M'` is hours and minutes
  with an optional space between.

* Several of the directives can be modified to be more lenient by adding
  a trailing `!`.  For examples: `' !'` will match any non-word character,
  including spaces; `'%Z!'` will match a wide variety of timezone names (the
  default is to match only those know to the current locale).

When passed to the SimpleDate constructor, the format is used both to parse
dates and to format them:

   ```python
   >>> birthday = SimpleDate('19 May 2013', format='%a %b %Y')
   >>> str(birthday)
   19 May 2013
   ```

When an extended format is used for parsing, Simple Date uses the matched
data to select a format for printing.  So if `'{%H:}?%M'` matched both
hours and minutes then the format would be `'%H:%M'`, but if it matched only
minutes then the format for printing would be `'%M'`.

Whether a format is supplied or not, the formats in [SimpleDateParser] (by
default, `DEFAULT_DATE_PARSER`) can also be used to parse the string, if
necessary.  And if no format is supplied then the format in the parser that
succeeds is used for formatting output too.

See the next section for specifying multiple formats.

### Date Parser - date_parser

Give the [SimpleDateParser](#simpledateparser) that will be used when
parsing a string.  This lets you specify which date formats are used in
parsing - important because American and European date styles conflict.

For example, to parse American style (month/day/year):

```python
>>> american = SimpleDateParser(MDY + DEFAULT_FORMATS)
>>> SimpleDate('12/24/2013', date_parser=american)
SimpleDate('12/24/2013', tz='America/Santiago')
```

### Debugging - debug

Setting `debug=True` will display a *lot* of information on `stdout`.

For example, we can see why the following fails:

```python
>>> SimpleDate('2013-01-01 CLT', country='CL', debug=True)
SimpleDate: Inferring auto argument
SimpleDate: Found a string, will try to parse
SimpleDate: Using default date parser
SimpleDateParser: Raw parse results for %Y-%m-%d %Z: (2013, 1, 1, 0, 0, 0, 1, 1, 0, 'CLT', None), 0
SimpleDateParser: Parsed timezone name from date as CLT
SimpleDateParser: Combined zones are ('CLT',)
PyTzFactory: Searching (timezones=('CLT',), datetime=datetime.datetime(2013, 1, 1, 0, 0), is_dst=False, country='CL', unsafe=False)
PyTzFactory: Have country code CL
PyTzFactory: Country code CL has 2 timezones
PyTzFactory: Expanded country codes to 2 timezones
PyTzFactory: Expanding ('CLT',)
PyTzFactory: Name lookup failed for CLT
PyTzFactory: America/Santiago gave CLST
PyTzFactory: Pacific/Easter gave EASST
PyTzFactory: Expanded timezone to 0 timezones
[...traceback...]
simpledate.NoTimezone: No timezone found (timezones=('CLT',), datetime=datetime.datetime(2013, 1, 1, 0, 0), is_dst=False, country='CL', unsafe=False)
```

The format is handled correctly, but the expected timezone, America/Santiago,
is giving CLST instead of CLT - Chile is in the Southern Hemisphere so it's
summer in January.

Complete API
------------

### SimpleDate

SimpleDate is an immutable wrapper around a datetime, tzinfo, and format string.
The constructor can be used to convert *from* other formats; instance attributes
can be used to convert *to* those formats.

Here is an example that combines a date and time in the EDT timezone and
then converts the result to a datetime in UTC:

```python
>>> SimpleDate(date=date(2013, 6, 15), time=time(10, 50), tz='EDT').utc.datetime
datetime.datetime(2013, 6, 15, 14, 50, tzinfo=<UTC>)
```

#### Constructor

For something that calls itself "simple", the SimpleDate constructor is
a monster.  However, it's a lot easier to understand when you group the
parameters by functionality: there are the [numerical values](#numerical-values)
used to specify a date and time; the [conversions](#conversions) that construct
a SimpleDate from some other type; and then the standard arguments
([tz](#timezone---tz),
[is_dst](#daylight-saving-time---is_dst),
[country](#country-code---country),
[tz_factory](#tz-factory---tz_factory),
[unsafe](#first-found---unsafe),
[format](#format---format),
[date_parser](#date-parser---date_parser), and
[debug](#debugging---debug)) that were described earlier.

##### Numerical Values

These are `year`, `month`, `day`, `hour`, `minute`, `second` and `microsecond`
and they are in that order at the start of the constructor, so you don't need
to name them.  For example:

```python
>>> SimpleDate(2013, 6, 12, 0, 37, tz='EDT').local
2013-06-12 00:37:00.000000 EDT
```

You must supply at least `year`, `month` and `day`.  Missing values (on the
right) default to zero.

##### Conversions

Alternatively, instead of using numerical values, you can supply one of these
parameters:

* `simple` - Another SimpleDate instance (which will be copied)

* `datetime` - A datetime instance from the standard datetime package.

* `date` - A date instance from the standard datetime package.

* `ordinal` - A Gregorian ordinal (it's used in the standard datetime package).

* `time` - A time instance from the standard datetime package.

* `timestamp` - A Posix timestamp (Unix epoch).

In general, only one of these can be provided.  The exception is that `time`
can be combined with `date` or `ordinal`.

If only a single value is given then (except for `ordinal`) it can be given
as the first argument in the constructor - the type of the value will be used
to work out how it should be handled (the code knows it's not `year` because
there's no `month` or `day`).

For example:

```python
>>> SimpleDate(datetime(2013, 6, 12, 0, 37), tz='EDT')
SimpleDate('2013-06-12 00:37:00.000000 EDT')
```

#### Attributes

Attributes can be described as [simple](#simple-attributes) or
[complex](#complex-attributes):

##### Simple Attributes

These are all pretty obvious - the names usually match the standard Python
APIs, but everything is an attribute.

* `datetime`, `date`, `time`, `ordinal`, `timestamp`

* `year`, `month`, `day`, `hour`, `minute`, `second`, `millisecond`

* `weekday`, `isoweekday`, `isocalendar`

* `tzinfo`

* `format`

##### Complex Attributes

They return "higher level" objects with modified timzone information.

* `naive` - A wrapper around a naive datetime (one without tzinfo set).
  The wrapper contains all the attributes described above.  So, for example,
  `mysimpledate.naive.datetime` gives the naive datetime.

* `utc` - An equivalent SimpleDate in the UTC timezone.  Because this is
  another SimpleDate instance it also contains all the attributes described
  here.

* `normalized` - An equivalent SimpleDate, in UTC, with a standard format
  (so similar to `.utc`, but with the format changed too).  Useful for
  comparisons (see below).

#### Operators

SimpleDate supports similar operations to datetime: addition with timedelta;
subtraction of timedelta or other SimpleDate instances; comparison; equality.

**IMPORTANT** Equality includes the timezone and format.  So for consistent
comparison, convert to UTC with a standard format first.  The `normalized`
attribute does this (see above).

#### Conversion

For conversion to a string, SimpleDate supports `.strftime(format)` which
takes a standard format string:

```python
>>> SimpleDate(2013, 12, 24).strftime('%A')
'Tuesday'
```
For conversion to other dates, SimpleDate has a method, `.convert(...)`, which
takes the usual parameters
([tz](#timezone---tz),
[is_dst](#daylight-saving-time---is_dst),
[country](#country-code---country),
[tz_factory](#tz-factory---tz_factory),
[unsafe](#first-found---unsafe),
[format](#format---format),
[debug](#debugging---debug))
and returns a new SimpleDate with the same equivalent time, but matching the
new requirements.

So, for example, to change format:

```python
>>> default_fmt = SimpleDate(datetime(2013, 6, 17))
>>> str(default_fmt)
'2013-06-17 00:00:00.000000 CLT'
>>> short_fmt = default_fmt.convert(format='%Y-%m-%d')
>>> str(short_fmt)
'2013-06-17'
```

For conversion to other types, see [attributes](#attributes).

#### Replacement

Similar to `datetime.replace()`, SimpleDate has a `.replace(...)` method that
generates a *new* time (unlike `.convert(...)`, which is the same time in
a different timezone or format).

This combines the usual datetime arguments (year, month, day, hour, minute,
second, microsecond) with the standard SimpleDate parameters that control
timezone resolution etc
([tz](#timezone---tz),
[is_dst](#daylight-saving-time---is_dst),
[country](#country-code---country),
[tz_factory](#tz-factory---tz_factory),
[unsafe](#first-found---unsafe),
[format](#format---format),
[debug](#debugging---debug)).

For example, to move to the start of the day:

```python
>>> SimpleDate().replace(hour=0, minute=0, second=0, microsecond=0)
SimpleDate('2013-06-22 00:00:00.000000 CLT', tz='America/Santiago')
```

### SimpleDateParser

Often you need to parse dates without knowing, ahead of time, the exact date
format.  One approach is to try write code that is "smart enough" to parse
many formats.  That approach is taken by
[python-dateutil](http://labix.org/python-dateutil) (I believe).  An
alternative, which may be slower (but see below), but also more reliable,
is to try different formats in turn.  This latter approach is taken by
SimpleDateParser.

Note that the SimpleDate [constructor](#constructor) calls SimpleDateParser
automatically (either `DEFAULT_DATE_PARSER`, or the instance supplied as
`date_parser=...`).  You only need to use this class directly if you want
to use a different set of formats from the default.

#### Constructor

The constructor takes a list of formats, which will be tried until one works
(the order is not guaranteed - more successful formats are tried first).

Predefined lists include `RFC_2822` (aliased as `EMAIL`), `ISO_8601`,
`MDY` and `DMY`.

`MDY` and `DMY` are mutually exclusive - only use one at a time.

The default is `DEFAULT_FORMATS = ISO_8601 + RFC_2822`

#### Parsing

SimpleDateParser has a single method, `.parse(...)` which takes a date (as
a string) plus
the usual suspects
([tz](#timezone---tz),
[is_dst](#daylight-saving-time---is_dst),
[country](#country-code---country),
[tz_factory](#tz-factory---tz_factory),
[unsafe](#first-found---unsafe),
[format](#format---format),
[debug](#debugging---debug))
and returns a [SimpleDate](#simpledate) instance.

### PyTzFactory

The PyTzFactory is responsible for finding a timezone that matches various
constraints - things like the timezone name, the date in question, and,
perhaps, a set of countries.

Sometimes this is easy: if it's given a tzinfo instance and no other
constraints it simply returns the value.  But in general it requires a
[search](#the-need-for-search) through all the available timezones.

As with [SimpleDateParser], this is called from the SimpleDate
[constructor](#constructor) via `DEFAULT_TZ_FACTORY` (or given by
`tz_factory=...`).

#### Constructor

The constructor for PyTzFactory takes a list of timezones (by default
`pytz.common_timezones`) and countries (by default, `None`, implying all).
From this it constructs a set of common timezones that will be used to
search for values.

#### Timezone Search

The `.search(...)` method takes zero or more timezones (unnamed arguments),
a datetime instance (`datetime=...` - defining when the timezone is used),
and the standard
[is_dst](#daylight-saving-time---is_dst),
[country](#country-code---country),
[unsafe](#first-found---unsafe), and
[debug](#debugging---debug).
It searches for, and returns, a timezone (tzinfo instance) that matches the
parameters given.

The timezone arguments are typically strings, although integer minutes,
tzinfo and timedelta instances are also supported.  Also, several can be
grouped in a tuple (see below).

Each timezone is used in sequence to restrict the range of possible values
(functions as a logical AND).  A tuple timezone matches any of the values
(functions as a logical OR).  So, for example, if called as

```python
>>> PyTzFactory().search(A, (B, C))
```

then the result will be consistent with `A and (B or C)`.

#### Other Methods

These are mainly for internal use:

* `.distinct(...)` - Filter timezones, returning those with distinct offsets
  from UTC at the time given.

* `.expand_tz(...)` - Implement [search](#timezone-search) for a single
  timezone (or tuple).

* `.expand_country(...)` - Expand country codes to their associated timezones.

Functions for tzinfo
--------------------

The following functions are more robust (or perhaps I misunderstood the API)
replacements for various tzinfo methods:

* `reapply_tzinfo(datetime, is_dst)` - A more powerful `tzinfo.normalize(...)`.

* `tzinfo_astimezone(tzinfo, datetime)` - Sets `tzinfo` after conversion.

* `tzinfo_tzname(tzinfo, datetime, is_dst)` - Handles optional `is_dst` and
  returns values for fixed offsets.

* `tzinfo_utcoffset(tzinfo, datetime)` - Handles optional `is_dst`.

* `tzinfo_localize(tzinfo, datetime, is_dst)` - Handles optional `is_dst`.

Best Guess UTC
--------------

`best_guess_utc(date, debug=False)` is a helper function for the
most common use-case: given some input (in any of the formats supported by
the SimpleDate [constructor](#constructor)), return the most likely datetime
in UTC.  It is a wrapper around the other classes here which attempts to parse
American-style (month first) dates in US timezones (only).  If that fails
then it uses other timezones with European-style (day first) dates.

The implementation uses `unsafe=True` ([docs](#first-found---unsafe)) and
thread-local factories (so can be called from multiple threads).  It is
intended to be efficient and robust, but may sacrifice accuracy in
[ambiguous](#the-need-for-search) cases.

FAQ
---

### What is the Licence?

Simple Date is (c) 2013 Andrew Cooke (andrew@acooke.org).  It is released into
the public domain for any use, but with absolutely no warranty.

### Are You Supporting this Code?

Yes (contact at me at [andrew@acooke.org](mailto:andrew@acooke.org) if you
have a bug report).  BUT this is something of an experiment.  The API of
future versions could change significantly (earlier alpha versions changed
a *lot* as I understood more about timezones and the problems involved).

The challenge is to make something that is simple, general, and correct...

### Why Python 3.2+?

The code uses `OrderedDict` (3.1+) and `datetime.timezone` (3.2+).

### Is the Library Thread Safe?

**NO.**  Both SimpleDateParser and PyTzFactory mutate their contents to improve
efficiency on repeated calls.  This will give undefined behaviour if they
(ie `DEFAULT_DATE_PARSER` and `DEFAULT_TZ_FACTORY`) are called from multiple
threads.

If you do use multiple threads, you *must* create instances of those classes
for each thread and pass them to SimpleDate using `date_parser=...` and
`tz_factory=...`.

However, [best_guess_utc](#best_guess_utc) *is* thread safe (the
implementation uses the approach above via thread-local storage).

### Why Did I Get the Error "Could not parse ..."?

SimpleDate does not know the format for the string you gave.  Specify the
[format](#format) using `format=...` in the
[SimpleDate constructor](#constructor).

If you have multiple formats then you should create a new
[SimpleDateParser](#simpledateparser) and provide it via
[date_parser](#date-parser---date_parser).

By default neither American nor European formats are included (they conflict)
so if you want to parse European style dates:

```python
>>> european = SimpleDateParser(DMY + DEFAULT_FORMATS)
>>> SimpleDate('24/12/2013', date_parser=european)
SimpleDate('24/12/2013', tz='America/Santiago')
```

### Why Did I Get the Error "No timezone found"?

The timezone you gave was not found in the PyTZ database.  This may be because
it was given for a time that doesn't make sense (for example, using daylight
savings in winter).

### Why Did I Get the Error "AmbiguousTimezone: ..."?

The timezone you gave could be matched against more that one timezone in
PyTZ's database.  See [the need for search](#the-need-for-search).

### Why Did I Get the Error "SingleInstantTzError ..."?

You tried to use a tzinfo instance that is defined only for one moment in
time.  About all you can do with such dates is convert them to UTC.  See
[the need for search](#the-need-for-search).

### What is the Best Way to Use this Library?

[Parse and convert to UTC](#best-guess-utc).

Background
----------

This section tries to explain and justify the library's implementation.

### Classifying Timezones

I am no expert on timezones.  Everything I know I have inferred from
the PyTZ API.  Here I am going to impose some structure on the different kinds
of timezone.  The aim is to construct a vocabulary within which the
implementation can be explained.

Four aspects of timezones seem to be important.  The first two are:

* **Temporal Timezones** define fixed offsets from UTC.  They can be written
   like `+0300` or `UTC+3` (3 hours ahead of UTC).  Some are given names.  For
   example, `EDT` (Eastern Daylight Time) is `UTC-4`.

* **Geographical Timezones** are associated with a particular place.  They
   are typically defined by some official body and may have a *history*.  In
   particular, many geographical timezones make an adjustment (daylight saving
   time) during the summer, and the dates when that adjustment is made may
   change from year to year.  So geographical timezones are often defined in
   terms of temporal timezones.  Finally, geographical timezones can be written
   like `America/New_York`.

It follows from all this that (1) geographical timezones are defined
throughout the year (but may be ambiguous - see [is_dst](#is_dst)), and (2)
some temporal timezones may only be valid at certain times.

Here is an example of an invalid temporal timezone: "2013-06-01 CLST".  June
is the middle of winter in Chile (in the Southern Hemisphere) and so a June
date would not be expressed in terms of Chilean *Summer* Time.

But not all temporal timezones behave this way.  `UTC` is always valid, for
example.  So from this we have two more ways to classify timezones:

* **Unlimited Timezones** are always valid.  All geographical timezones, and
  some temporal timezones, are unlimited.

* **Limited Timezones** are only valid at certain times.  These are temporal
  timezones.  Daylight saving times are limited, temporal timezones, for
  example.

Now, finally, we have the tools to understand PyTZ.  The PyTZ package is
*a database of unlimited timezones*.  If we have the name of an unlimited
timezone, we can extract a tzinfo instance (tzinfo is a standard Python class
from the datetime package) that will give us the temporal timezone on any date.

That's great, and PyTZ is very useful.  But...

...unfortunately, when dates are presented as text, they typically use
*limited, temporal timezones*.  These are not provided *directly* by PyTZ -
they appear only when applying a geographical timezone to a particular
date.

As an example.  In PyTZ is easy, if we know someone is in `America/New_York`,
and that their current the date/time is `2013-06-01 12:00`, to infer that it
should be written as `EDT`.

But if someone writes `2013-06-01 12:00 EDT`, what is their geographical
timezone?  And what format timezone would they use for `2013-01-01 12:00`,
in the middle of winter?  These kinds of questions are harder to answer with
PyTZ.

[Aside: This is not the "fault" of PyTZ, as far as I can tell.  It's simply
how the Olson timezone database works, which presumably that reflects the
real-life complexities of timezones.]

### The Need for Search

If we are parsing a *limited, temporal timezones* then we cannot retrieve it
directly from PyTZ (see above).  Instead, we need to go through the the
*database of unlimited timezones*, trying each in turn, until we find an
*unlimited timezone* which, at the particular date we are parsing, uses the
*limited timezone* we have.

An example might clear things up.  When SimpleDateParser reads a date string
containing `EDT` then it calls PyTzFactory, which runs through the different
timezones from PyTZ until it finds one - `America/New_York`, for example -
that would be displayed as `EDT` on the date in question.

This process can have problems:

1. No suitable timezone is found.  In this case a NoTimezone exception
   is raised.

   ```python
   >>> SimpleDate('2013-06-17 BAD')
   NoTimezone: No timezone found (timezones=('BAD',), datetime=datetime.datetime(2013, 6, 17, 0, 0), is_dst=False, country=None, unsafe=False)
   ```

2. Multiple timezones are found, but they are all at the same offset from
   UTC.  For example, in the case of `EDT` this might include
   `America/New_York` and `America/Detroit` (amongst others).  In this case,
   a SingleInstantTz is created - a `tzinfo` instance that is valid only at
   the time we searched for.

   ```python
   >>> SimpleDate('2013-06-17 EDT', debug=True)
   ...
   PyTzFactory: New offset -1 day, 20:00:00 for America/Indiana/Marengo
   PyTzFactory: Known offset -1 day, 20:00:00 for America/Thunder_Bay
   PyTzFactory: Known offset -1 day, 20:00:00 for America/Toronto
   PyTzFactory: Known offset -1 day, 20:00:00 for America/Indiana/Winamac
   ...
   SimpleDate('2013-06-17 EDT')
   >>> SimpleDate('2013-06-17 EDT').tzinfo
   SingleInstantTz(datetime.timedelta(-1, 72000), 'EDT', datetime.datetime(2013, 6, 17, 4, 0, tzinfo=<UTC>))
   ```

3. Multiple timezones with different offsets from UTC are found.  In this
   case an AmbiguousTimezone exception is raised (unless
   [unsafe](#first-found---unsafe) is set):

   ```python
   >>> SimpleDate('2013-06-17 EST')
   AmbiguousTimezone: 2 distinct timezones found: <StaticTzInfo 'EST'>; <DstTzInfo 'Australia/Sydney' EST+10:00:00 STD> (timezones=('EST',), datetime=datetime.datetime(2013, 6, 17, 0, 0), is_dst=False, country=None, unsafe=False)
   ```

A SingleInstantTz is also returned on success when `unsafe=True` is used
(which returns the [first timezone found](#first-found---unsafe)), because it
is unclear whether the result is case 2 (or even 3, hence the name).

```python
>>> SimpleDate('2013-06-17 America/New_York').tzinfo
<DstTzInfo 'America/New_York' EDT-1 day, 20:00:00 DST>
>>> SimpleDate('2013-06-17 America/New_York', unsafe=True).tzinfo
SingleInstantTz(datetime.timedelta(-1, 72000), 'EDT', datetime.datetime(2013, 6, 17, 4, 0, tzinfo=<UTC>))
```

When a SingleInstantTz is used for *anything* except working with the date
that was used when it was created, a SingleInstantTzError is raised.  This is
because at other times case (2) above may change to case (3).  We have no way
of knowing if the timezone is ambiguous at other times.

This may be very frustrating, but it is sufficient to support one very common
pattern when processing dates: [parse and convert to UTC](#best-guess-utc).
This approach is recommended because it restricts all the complications with
timezone handling to one place in the program - handling input.  The rest of
the code can process UTC values with no concerns about further errors.
