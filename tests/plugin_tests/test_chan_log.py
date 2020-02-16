from itertools import chain

from plugins.core.chan_log import format_error_chain


def test_format_exception_chain():
    def _get_data(exc):
        yield repr(exc)
        yield "  args = {!r}".format(exc.args)
        yield "  with_traceback = {!r}".format(exc.with_traceback)
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
            raise err2
    except ValueError as e:
        assert list(format_error_chain(e)) == list(
            chain(_get_data(err2), _get_data(err1), _get_data(err),)
        )
