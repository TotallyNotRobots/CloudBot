import asyncio as _asyncio
from concurrent.futures import Future as _ConcurrentFuture

try:
    isfuture = _asyncio.isfuture
except AttributeError:
    def isfuture(obj):
        return isinstance(obj, _asyncio_future_init)

_asyncio_isfuture = isfuture
_asyncio_iscoroutine = _asyncio.iscoroutine
_asyncio_iscoroutinefunction = _asyncio.iscoroutinefunction

_asyncio_get_event_loop = _asyncio.get_event_loop
_asyncio_future_init = _asyncio.Future

try:
    _asyncio_async = getattr(_asyncio, "async")
except AttributeError:
    def _asyncio_async(*args, **kwargs):
        raise NotImplementedError

try:
    ensure_future = _asyncio.ensure_future
except AttributeError:
    def ensure_future(coro_or_future, *, loop=None):
        return _asyncio_async(coro_or_future, loop=loop)


try:
    run_coroutine_threadsafe = _asyncio.run_coroutine_threadsafe
except AttributeError:
    def _is_future_not_concurrent(fut):
        return _asyncio_isfuture(fut) and not isinstance(fut, _ConcurrentFuture)


    def _copy_future_state(source, dest):
        """Internal helper to copy state from another Future.

        The other Future may be a concurrent.futures.Future.
        """
        assert source.done()
        if dest.cancelled():
            return

        assert not dest.done()
        if source.cancelled():
            dest.cancel()
        else:
            exception = source.exception()
            if exception is not None:
                dest.set_exception(exception)
            else:
                result = source.result()
                dest.set_result(result)


    def _set_concurrent_future_state(concurrent, source):
        """Copy state from a future to a concurrent.futures.Future."""
        assert source.done()
        if source.cancelled():
            concurrent.cancel()

        if not concurrent.set_running_or_notify_cancel():
            return

        exception = source.exception()
        if exception is not None:
            concurrent.set_exception(exception)
        else:
            result = source.result()
            concurrent.set_result(result)


    def _chain_future(source, destination):
        if not _is_future_not_concurrent(source):
            raise TypeError('A future is required for source argument')

        if not _is_future_not_concurrent(destination):
            raise TypeError('A future is required for destination argument')

        source_loop = getattr(source, '_loop', None) if _asyncio_isfuture(source) else None
        dest_loop = getattr(destination, '_loop', None) if _asyncio_isfuture(destination) else None

        def _set_state(future, other):
            if _asyncio_isfuture(future):
                _copy_future_state(other, future)
            else:
                _set_concurrent_future_state(future, other)

        def _call_check_cancel(destination):
            if destination.cancelled():
                if source_loop is None or source_loop is dest_loop:
                    source.cancel()
                else:
                    source_loop.call_soon_threadsafe(source.cancel)

        def _call_set_state(source):
            if dest_loop is None or dest_loop is source_loop:
                _set_state(destination, source)
            else:
                dest_loop.call_soon_threadsafe(_set_state, destination, source)

        destination.add_done_callback(_call_check_cancel)
        source.add_done_callback(_call_set_state)


    def run_coroutine_threadsafe(coro, loop):
        """Submit a coroutine object to a given event loop.

        Return a concurrent.futures.Future to access the result.
        """
        if not _asyncio_iscoroutine(coro):
            raise TypeError('A coroutine object is required')

        future = _ConcurrentFuture()

        def callback():
            try:
                _chain_future(ensure_future(coro, loop=loop), future)
            except Exception as exc:
                if future.set_running_or_notify_cancel():
                    future.set_exception(exc)

                raise

        loop.call_soon_threadsafe(callback)
        return future


def create_future(loop=None):
    if loop is None:
        loop = _asyncio_get_event_loop()

    try:
        f = loop.create_future
    except AttributeError:
        return _asyncio_future_init(loop=loop)
    else:
        return f()
