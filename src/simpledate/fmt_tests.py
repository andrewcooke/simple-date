
from unittest import TestCase
from re import compile
from simpledate.fmt import to_regexp


class RegexpTest(TestCase):

    def test_marker(self):
        # shows we can use an empty pattern to mark which option is matched
        rx = compile(r'(?P<a>)x')
        m = rx.match('x')
        assert m, 'no match'
        assert 'a' in m.groupdict(), m.groupdict()
        assert m.groupdict()['a'] is not None, m.groupdict()['a']
        rx = compile(r'((?P<a>)a|b)')
        m = rx.match('a')
        assert m, 'no match'
        assert 'a' in m.groupdict(), m.groupdict()
        assert m.groupdict()['a'] is not None, m.groupdict()['a']
        m = rx.match('b')
        assert m, 'no match'
        assert 'a' in m.groupdict(), m.groupdict()
        assert m.groupdict()['a'] is None, m.groupdict()['a']
        rx = compile(r'((?P<a>)a|(?P<b>)b)')
        m = rx.match('b')
        assert m, 'no match'
        assert 'a' in m.groupdict(), m.groupdict()
        assert m.groupdict()['a'] is None, m.groupdict()['a']
        assert 'b' in m.groupdict(), m.groupdict()
        assert m.groupdict()['b'] is not None, m.groupdict()['b']


class ParserTest(TestCase):

    def assert_regexp(self, target, expr, subs):
        result, _ = to_regexp(expr, subs)
        assert target == result, result

    def test_regexp(self):
        self.assert_regexp('abc', 'abc', {})
        self.assert_regexp('abXc', 'ab%xc', {'%x': 'X'})
        self.assert_regexp('ab((?P<1>)X)c', 'ab{%x}c', {'%x': 'X'})
        self.assert_regexp('a((?P<1>)b)?c', 'ab?c', {})

    def test_subs(self):
        self.assert_regexp('(?P<Y>\d\d\d\d)-(?P<m>1[0-2]|0[1-9]|[1-9])-(?P<d>3[0-1]|[1-2]\d|0[1-9]|[1-9]| [1-9])', '%Y-%m-%d', None)
        self.assert_regexp('((?P<1>)(?P<d>3[0-1]|[1-2]\d|0[1-9]|[1-9]| [1-9]))?', '%d?', None)

    def assert_parser(self, target_regexp, target_rebuild, expr, subs):
        regexp, rebuild = to_regexp(expr, subs)
        assert target_regexp == regexp, regexp
        assert target_rebuild == rebuild, rebuild

    def test_parser(self):
        self.assert_parser('abc', {0: 'abc'}, 'abc', {})
        self.assert_parser('abC', {0: 'abc'}, 'abc!', {'c!': 'C'})
        self.assert_parser('ab((?P<1>)xyz)c', {0: 'ab%1%c', 1: 'xyz'}, 'ab{xyz}c', {})
        self.assert_parser('ab((?P<1>)xy|(?P<2>)z)c', {0: 'ab%1%%2%c', 1: 'xy', 2: 'z'}, 'ab{xy|z}c', {})
        self.assert_parser('ab((?P<1>)c)?', {0: 'ab%1%', 1: 'c'}, 'abc?', {})
        self.assert_parser('ab((?P<1>)((?P<2>)c)?|(?P<3>)de((?P<4>)X)?)', {0: 'ab%1%%3%', 1: '%2%', 2: 'c', 3: 'de%4%', 4: '%x'}, 'ab{c?|de%x?}', {'%x': 'X'})
