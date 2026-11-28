import pytest

from cloudbot.util import func_utils


def test_call_with_args() -> None:
    args = []

    def func(
        arg1: int, arg2: int | None = None, _arg3: int | None = None
    ) -> None:
        nonlocal args
        args = [arg1, arg2, _arg3]

    func_utils.call_with_args(func, {"arg1": 1, "arg2": 3})
    assert args == [1, 3, None]

    with pytest.raises(func_utils.ParameterError):
        func_utils.call_with_args(func, {})
