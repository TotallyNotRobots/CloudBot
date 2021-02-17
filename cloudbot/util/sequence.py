"""
Sequence utilities - Various util functions for working with lists, sets, tuples, etc
"""


def chunk_iter(data, chunk_size):
    """
    Splits a sequence in to chunks
    :param data: The sequence to split
    :param chunk_size: The maximum size of each chunk
    :return: An iterable of all the chunks of the sequence
    """
    for i in range(0, len(data), chunk_size):
        yield data[i : i + chunk_size]
