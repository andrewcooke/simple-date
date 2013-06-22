
from _strptime import LocaleTime
from collections import defaultdict
from re import sub, escape

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


def to_regexp(fmt, substitutions=None):

    if substitutions is None:
        substitutions = DEFAULT_SUBSTITUTIONS

    # escape things that are related to regexps
    fmt = sub(r"([\\.^$*+\(\)\[\]])", r"\\\1", fmt)
    fmt = sub('\s+', ' ', fmt)

    count = 0
    stack = [0]
    rebuild = defaultdict(lambda: '')
    regexp = ''
    tokens = tokenizer(fmt)

    def append(read, write=None):
        nonlocal regexp
        regexp += read
        if write is None:
            write = read
        if write.endswith('!'):
            write = write[:-1]
        rebuild[stack[-1]] += write

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
                append('((?P<%d>)' % count, '%%%d%%' % count)
                stack.append(count)
            elif tok == '|':
                if not stack.pop():
                    raise ValueError('Unexpected | (must be within {...})')
                count += 1
                append('|(?P<%d>)' % count, '%%%d%%' % count)
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

    return regexp, rebuild


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
    '%c': to_regexp(LOCALE_TIME.LC_date_time, BASE_SUBSTITUTIONS)[0],
    '%x': to_regexp(LOCALE_TIME.LC_date, BASE_SUBSTITUTIONS)[0],
    '%X': to_regexp(LOCALE_TIME.LC_time, BASE_SUBSTITUTIONS)[0],
})

DEFAULT_SUBSTITUTIONS = dict(PYTHON_SUBSTITUTIONS)
DEFAULT_SUBSTITUTIONS.update({
    '%a!': r'(?P<a>\w(?<=[^\d_]))',
    '%A!': r'(?P<A>\w(?<=[^\d_]))',
    '%b!': r'(?P<b>\w(?<=[^\d_]))',
    '%B!': r'(?P<B>\w(?<=[^\d_]))',
    # TODO
})
