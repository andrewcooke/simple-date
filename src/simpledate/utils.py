
from collections import MutableSet


class MRUSortedIterable:
    '''
    An iterable that re-orders the contents to move the most recently used item
    (the last accessed on the previous iteration) to the start of the sequence.

    IMPORTANT: Not thread safe.
    '''

    def __init__(self, data):
        '''
        :param data: The data to iterate over.
        :return: An iterable that adapts to provide MRU values first.
        '''
        self._data = list(data)
        self._i = 0

    def __iter__(self):
        '''
        :return: A new iterator.
        '''
        # the iterator records the last accessed value in `_i`.  when a new
        # iterable is requested that points to the last returned (and
        # presumably used) value.  so at that point we can re-order the data.
        if self._i:
            self._data[0], self._data[1:self._i+1] = self._data[self._i], self._data[0:self._i]
        for self._i, value in enumerate(self._data):
            yield value
            # reset on exhaustion.  usefully, this means that the final value was
        # not OK, so another value was requested.  in this way we can avoid
        # promoting the last value when no value was used.
        self._i = 0


class DebugLog:
    '''
    Base class supporting a simple log to stdout for debugging.  Is it possible
    to use Python logging and do the same thing?
    '''

    def _get_log(self, debug):
        '''
        :param debug: True to enable logging.
        :return: A logger that will print to stdout if `debug` is `True`
        '''
        return self._log if debug else self._drop

    def _log(self, template, *args, **kargs):
        '''
        A logger that prints to stdout.

        :param template: A string that can contain embedded {0}-style
                         formatting.
        :param args: Format arguments.
        :param kargs: Named format arguments.
        '''
        print('%s: %s' % (self.__class__.__name__, template.format(*args, **kargs)))

    def _drop(self, template, *args, **kargs):
        '''
        A null logger that discards its arguments.

        :param template: Unused.
        :param args: Unused.
        :param kargs: Unused.
        '''
        pass


class HashableDict(dict):
    # http://stackoverflow.com/questions/1151658/python-hashable-dicts

    def __hash__(self):
        return hash((frozenset(self), frozenset(self.values())))


# based on http://code.activestate.com/recipes/576694/


class OrderedSet(MutableSet):

    def __init__(self, iterable=None):
        self.end = end = []
        end += [None, end, end]         # sentinel node for doubly linked list
        self.map = {}                   # key --> [key, prev, next]
        if iterable is not None:
            self |= iterable

    def __len__(self):
        return len(self.map)

    def __contains__(self, key):
        return key in self.map

    def add(self, key):
        if key not in self.map:
            end = self.end
            curr = end[1]
            curr[2] = end[1] = self.map[key] = [key, curr, end]

    def discard(self, key):
        if key in self.map:
            key, prev, next = self.map.pop(key)
            prev[2] = next
            next[1] = prev

    def __iter__(self):
        end = self.end
        curr = end[2]
        while curr is not end:
            yield curr[0]
            curr = curr[2]

    def __reversed__(self):
        end = self.end
        curr = end[1]
        while curr is not end:
            yield curr[0]
            curr = curr[1]

    def pop(self, last=True):
        if not self:
            raise KeyError('set is empty')
        key = self.end[1][0] if last else self.end[2][0]
        self.discard(key)
        return key

    def __repr__(self):
        if not self:
            return '%s()' % (self.__class__.__name__,)
        return '%s(%r)' % (self.__class__.__name__, list(self))

    def __eq__(self, other):
        if isinstance(other, OrderedSet):
            return len(self) == len(other) and list(self) == list(other)
        return set(self) == set(other)

    # these methods added

    @staticmethod
    def union(*sets):
        union = OrderedSet()
        union.union(*sets)
        return union

    def union(self, *sets):
        for set in sets:
            self |= set

    @staticmethod
    def intersect(*sets):
        intersection = OrderedSet()
        if sets:
            first = next(iter(sets))
            for item in first:
                rest = iter(sets)
                next(rest)  # drop first
                for set in rest:
                    if item not in set:
                        break
                    intersection.add(item)
        return intersection


def set_kargs_only(**kargs):
    return dict((key, value) for (key, value) in kargs.items() if value is not None)


def always_tuple(value, none=()):
    '''
    Some arguments can be a single value, or a sequence (tuple or list).
    This function normalizes the input to always be a sequence.

    :param value: The value that, if non-sequence, should be converted to a
                  sequence
    :param none: Value returned when input is None
    :return: The value as a sequence.
    '''
    if value is None:
        return none
    # elif isinstance(value, Iterable) and not isinstance(value, str):
    elif hasattr(value, '__iter__') and not isinstance(value, str):
        return tuple(value)
    else:
        return (value,)


