
from distutils.core import setup

setup(
    name = 'simple-date',
    url = 'https://github.com/andrewcooke/simple-date',
    requires = ['pytz', 'tzlocal'],
    install_requires = ['pytz', 'tzlocal'],
    packages = ['simpledate'],
    package_dir = {'': 'src'},
    version = '0.3.4',
    description = 'Simple dates (and times, and timezones).',
    author = 'Andrew Cooke',
    author_email = 'andrew@acooke.org',
    classifiers = ['Development Status :: 4 - Beta',
                   'Intended Audience :: Developers',
                   'License :: Public Domain',
                   'Programming Language :: Python :: 3.2',
                   'Programming Language :: Python :: 3.3',
                   'Topic :: Software Development',
                   'Topic :: Software Development :: Libraries',
                   'Topic :: Software Development :: Libraries :: Python Modules'],
    long_description = '''
A wrapper around the
`datetime <http://docs.python.org/3/library/datetime.html#module-datetime>`_,
`pytz <http://pytz.sourceforge.net/>`_ and
`tzlocal <https://pypi.python.org/pypi/tzlocal>`_
packages for Python 3.2+.
`Full docs <https://github.com/andrewcooke/simple-date>`_ on github.

Examples
--------

Just give me a UTC datetime for these dates!

::

    >>> for date in '1/6/2013 BST', '1/6/2013 EST', 'Tue, 18 Jun 2013 12:19:09 -0400':
    >>>     print(best_guess_utc(date))
    2013-05-31 23:00:00+00:00
    2013-01-06 05:00:00+00:00
    2013-06-18 16:19:09+00:00

What time is it now, in New York?

::

    >>> SimpleDate(tz='America/New_York')
    SimpleDate('2013-06-14 13:14:17.295943 EDT', tz='America/New_York')

And what time is that in the UK (the country code is for Great Britain)?

::

    >>> SimpleDate('2013-06-14 13:14:17.295943 EDT').convert(country='GB')
    SimpleDate('2013-06-14 18:14:17.295943 BST', tz='Europe/London')

What is the UTC for this email date?

::

    >>> SimpleDate('Fri, 14 Jun 2013 13:13:42 -0400').utc
    SimpleDate('Fri, 14 Jun 2013 17:13:42 +0000', tz='UTC')

What's the date a week from now (I live in Chile)?

::

    >>> SimpleDate() + timedelta(days=7)
    SimpleDate('2013-06-21 13:55:20.791519 CLT', tz='America/Santiago')

The day of the week for Xmas this year?

::

    >>> SimpleDate(2013, 12, 24).weekday
    1

And as a naive datetime?

::

    >>> SimpleDate(2013, 12, 24).naive.datetime
    datetime.datetime(2013, 12, 24, 0, 0)

What's the time in EST for epoch 1234567890?

::

    >>> SimpleDate(1234567890, tz='EST')
    AmbiguousTimezone: 3 distinct timezones found: <'EST'>; <'Australia/NSW'>; ...

Whoa!  What are those crazy Australians doing?  Let's force the USA (only)::

    >>> SimpleDate(1234567890, tz='EST', country='US')
    SimpleDate('2009-02-13 18:31:30.000000 EST')

Alternatively, we could give priority to the USA and take the first solution
we find::

    >>> SimpleDate(1234567890, tz='EST', country=prefer('US'), unsafe=True)
    SimpleDate('2009-02-13 18:31:30.000000 EST')

And what day is that?

::

    >>> SimpleDate(1234567890, tz='EST', country=prefer('US'), unsafe=True).strftime('%A')
    'Friday'

Licence
-------

(c) 2013 Andrew Cooke, andrew@acooke.org; released into the public domain
for any use, but with absolutely no warranty.
    '''
)
