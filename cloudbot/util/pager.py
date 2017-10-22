from threading import RLock

from cloudbot.util.sequence import chunk_iter


class Pager:
    """Multiline pager

    Takes a string with newlines and paginates it to certain size chunks
    """

    @classmethod
    def from_multiline_string(cls, s):
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
    lines = [""]
    for item in data:
        if len(item) > max_len:
            # The length of a single item is longer then our max line length, split it
            lines.append(item[:max_len])
            lines.append(item[max_len:])
        elif len(lines[-1]) + len(item) > max_len:
            lines.append(item)
        else:
            if lines[-1]:
                lines[-1] += delim

            lines[-1] += item

    formatted_lines = []
    while lines:
        line = lines.pop(0)
        formatted_lines.append("{}{}".format(line, suffix if lines else ""))

    return Pager(formatted_lines, chunk_size=page_size)
