import pytest


def test_call_with_args():
    args = []

    def func(arg1, arg2=None, _arg3=None):
        nonlocal args
        args = [arg1, arg2, _arg3]

    from cloudbot.util.func_utils import ParameterError, call_with_args

    call_with_args(func, {"arg1": 1, "arg2": 3})
    assert args == [1, 3, None]

    with pytest.raises(ParameterError):
        call_with_args(func, {})
