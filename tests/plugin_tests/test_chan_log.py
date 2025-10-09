from itertools import chain

from plugins.core import chan_log


def test_format_exception_chain():
    def _get_data(exc):
        yield repr(exc)
        if hasattr(exc, "add_note"):  # pragma: no cover
            yield f"  add_note = {exc.add_note!r}"

        yield f"  args = {exc.args!r}"
        yield f"  with_traceback = {exc.with_traceback!r}"
        yield ""

    err = ValueError("Test")
    err1 = ValueError("Test 2")
    err2 = ValueError("Test 3")
    try:
        try:
            try:
                raise err
            except ValueError as e:
                raise err1 from e
        except ValueError:
            raise err2 from None
    except ValueError as e:
        assert list(chan_log.format_error_chain(e)) == list(
            chain(
                _get_data(err2),
                _get_data(err1),
                _get_data(err),
            )
        )
