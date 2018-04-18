import pytest


class TestPopulateArgs:
    def test_positional_mapping(self):
        def _test(a, b):
            return a, b

        from cloudbot.util.func_utils import populate_args
        args, kwargs = populate_args(_test, {"a": 1, "b": 2})

        assert kwargs == {"a": 1, "b": 2}
        assert args == []

    def test_failed_map(self):
        def _test(a, b):
            return a, b

        from cloudbot.util.func_utils import populate_args, ParameterError
        with pytest.raises(ParameterError):
            populate_args(_test, {})
