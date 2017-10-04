"""
Wraps various asyncio functions
"""

import asyncio

import sys


def wrap_future(fut, *, loop=None):
    """
    Wraps asyncio.async()/asyncio.ensure_future() depending on the python version
    :param fut: The awaitable, future, or coroutine to wrap
    :param loop: The loop to run in
    :return: The wrapped future
    """
    if sys.version_info < (3, 4, 4):
        return asyncio.async(fut, loop=loop)

    return asyncio.ensure_future(fut, loop=loop)
