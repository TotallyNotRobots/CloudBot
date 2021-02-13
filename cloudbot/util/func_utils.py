import inspect


class ParameterError(Exception):
    def __init__(self, name, valid_args):
        super().__init__(
            "{!r} is not a valid parameter, valid parameters are: {}".format(
                name, list(valid_args)
            )
        )
        self.name = name
        self.valid_args = list(valid_args)


def call_with_args(func, arg_data):
    sig = inspect.signature(func, follow_wrapped=False)
    try:
        args = [
            arg_data[key]
            for key in sig.parameters.keys()
            if not key.startswith("_")
        ]
    except KeyError as e:
        raise ParameterError(e.args[0], arg_data.keys()) from e

    return func(*args)
