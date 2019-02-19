from threading import RLock

from cloudbot.util.formatting import chunk_str
from cloudbot.util.sequence import chunk_iter


class Pager:
    """Multiline pager

    Takes a string with newlines and paginates it to certain size chunks
    """

    @classmethod
    def from_multiline_string(cls, s):
        r"""
        >>> pager = Pager.from_multiline_string("foo\nbar\nbaz")
        >>> list(pager)
        [['foo', 'bar (page 1/2)'], ['baz (page 2/2)']]
        >>> pager.next()
        ['foo', 'bar (page 1/2)']
        >>> pager.next()
        ['baz (page 2/2)']
        >>> repr(pager.next())
        'None'
        >>> pager.get(0)
        ['foo', 'bar (page 1/2)']
        """
        return cls(s.splitlines())

    def __init__(self, lines, chunk_size=2):
        # This lock should always be acquired when accessing data from this object
        # Added here due to extensive use of threads throughout plugins
        self.lock = RLock()
        self.chunk_size = chunk_size
        self.chunks = tuple(chunk_iter(lines, self.chunk_size))
        self.current_pos = 0

    def format_chunk(self, chunk, pagenum):
        chunk = list(chunk)
        if len(self.chunks) > 1:
            chunk[-1] += " (page {}/{})".format(pagenum + 1, len(self.chunks))

        return chunk

    def next(self):
        with self.lock:
            if self.current_pos >= len(self.chunks):
                return None

            chunk = self[self.current_pos]
            self.current_pos += 1

        return chunk

    def get(self, index):
        """Get a specific page"""
        return self[index]

    def __getitem__(self, item):
        """Get a specific page"""
        with self.lock:
            chunk = self.chunks[item]
            return self.format_chunk(chunk, item)

    def __len__(self):
        with self.lock:
            return len(self.chunks)


def paginated_list(data, delim=" \u2022 ", suffix='...', max_len=256, page_size=2):
    """
    >>> list(paginated_list(['abc', 'def']))
    [['abc \u2022 def']]
    >>> list(paginated_list(['abc', 'def'], max_len=5))
    [['abc...', 'def']]
    >>> list(paginated_list(list('foobarbaz'), max_len=2))
    [['f...', 'o... (page 1/5)'], ['o...', 'b... (page 2/5)'], ['a...', 'r... (page 3/5)'], ['b...', 'a... (page 4/5)'], ['z (page 5/5)']]
    >>> list(paginated_list(['foo', 'bar'], max_len=1))
    [['f...', 'o... (page 1/3)'], ['o...', 'b... (page 2/3)'], ['a...', 'r (page 3/3)']]
    >>> list(paginated_list(['foo', 'bar'], max_len=2))
    [['fo...', 'o... (page 1/2)'], ['ba...', 'r (page 2/2)']]
    """
    lines = [""]

    def get_delim():
        if lines[-1]:
            return delim

        return ''

    for item in data:
        if len(item) > max_len:
            # The length of a single item is longer then our max line length, split it
            lines.extend(chunk_str(item, max_len))
        elif len(lines[-1] + get_delim() + item) > max_len:
            lines.append(item)
        else:
            lines[-1] += get_delim() + item

    formatted_lines = []
    lines = [line for line in lines if line]
    while lines:
        line = lines.pop(0)
        formatted_lines.append("{}{}".format(line, suffix if lines else ""))

    return Pager(formatted_lines, chunk_size=page_size)
