from threading import RLock
from typing import Iterable, List, Tuple

from cloudbot.util.formatting import chunk_str
from cloudbot.util.sequence import chunk_iter


class Pager:
    """Multiline pager

    Takes a string with newlines and paginates it to certain size chunks

    >>> p = Pager(['a', 'b', 'c', 'd', 'e'], 2)
    >>> p.next()
    ['a', 'b (page 1/3)']
    >>> p.next()
    ['c', 'd (page 2/3)']
    >>> p.next()
    ['e (page 3/3)']
    >>> p.next()

    >>> p1 = Pager(['a', 'b', 'c', 'd', 'e'], 0)
    >>> p1.next()
    ['a', 'b', 'c', 'd', 'e']
    >>> p1.next()
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
        self.chunks: Tuple[str, ...]
        if self.chunk_size == 0:
            self.chunks = (lines,)
        else:
            self.chunks = tuple(chunk_iter(lines, self.chunk_size))

        self.current_pos = 0

    def format_chunk(self, chunk: Iterable[str], pagenum: int) -> List[str]:
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

    def __getitem__(self, item) -> List[str]:
        """Get a specific page"""
        with self.lock:
            chunk = self.chunks[item]
            return self.format_chunk(chunk, item)

    def __len__(self):
        with self.lock:
            return len(self.chunks)


class CommandPager(Pager):
    """
    A `Pager` which is designed to be used with one of the .more* commands
    """

    def handle_lookup(self, text) -> List[str]:
        if text:
            try:
                index = int(text)
            except ValueError:
                return ["Please specify an integer value."]

            if index < 0:
                index += len(self) + 1

            if index < 1:
                out = "Please specify a valid page number between 1 and {}."
                return [out.format(len(self))]

            try:
                page = self[index - 1]
            except IndexError:
                out = "Please specify a valid page number between 1 and {}."
                return [out.format(len(self))]

            return page

        page = self.next()
        if page is not None:
            return page

        return [
            "All pages have been shown. "
            "You can specify a page number or do a new search."
        ]


def paginated_list(
    data,
    delim=" \u2022 ",
    suffix="...",
    max_len=256,
    page_size=2,
    pager_cls=Pager,
):
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

        return ""

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

    return pager_cls(formatted_lines, chunk_size=page_size)
