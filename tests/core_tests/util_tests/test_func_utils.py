import pytest


class TestPopulateArgs:
    def test_positional_mapping(self):
        def _test(a, b, *, c=None):
            return a, b, c

        from cloudbot.util.func_utils import populate_args
        args, kwargs = populate_args(_test, {"a": 1, "b": 2, "c": 3})

        assert kwargs == {"a": 1, "b": 2, "c": 3}
        assert args == []

    def test_failed_map(self):
        def _test(a, b):
            return a, b

        from cloudbot.util.func_utils import populate_args, ParameterError
        with pytest.raises(ParameterError) as exc_info:
            populate_args(_test, {})

        exc_info.match(
            r"'a'\sis\snot\sa\svalid\sparameter,\svalid\sparameters\sare:\s\[\]"
        )

    def test_map_varargs(self):
        def _test(*args):
            pass

        from cloudbot.util.func_utils import populate_args
        with pytest.raises(TypeError):
            populate_args(_test, {})

    def test_map_var_kwargs(self):
        def _test(**kwargs):
            pass

        from cloudbot.util.func_utils import populate_args
        with pytest.raises(TypeError):
            populate_args(_test, {})
