from plugins.core import log
from tests.util import with_temp_logs


@with_temp_logs()
def test_get_log_stream() -> None:
    log.stream_cache.clear()
    res = log.get_log_stream("foo", "bar")
    assert res is not None
    assert res.writable()
    assert log.stream_cache == {("foo", "bar"): (res.name, res)}
    res.close()
    log.stream_cache.clear()


@with_temp_logs()
def test_get_raw_log_stream() -> None:
    log.raw_cache.clear()
    res = log.get_raw_log_stream("foo")
    assert res is not None
    assert res.writable()
    assert log.raw_cache == {"foo": (res.name, res)}
    res.close()
    log.raw_cache.clear()
