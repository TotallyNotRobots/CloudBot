import inspect


class ParameterError(Exception):
    def __init__(self, name, valid_args):
        super().__init__(name, list(valid_args))

    def __str__(self):
        return "'{}' is not a valid parameter, valid parameters are: {}".format(self.args[0], self.args[1])


def _get_arg_value(param, data_map):
    """
    :type param: inspect.Parameter
    :type data_map: dict
    """
    try:
        return data_map[param.name]
    except KeyError as e:
        if param.default is param.empty:
            raise ParameterError(e.args[0], data_map.keys()) from e

        return param.default


def _populate_args(func, data_map):
    args = []
    kwargs = {}
    sig = inspect.signature(func)
    for key, param in sig.parameters.items():  # type: str, inspect.Parameter
        if param.kind is param.KEYWORD_ONLY:
            kwargs[key] = _get_arg_value(param, data_map)
        elif param.kind is param.POSITIONAL_ONLY:
            args.append(_get_arg_value(param, data_map))
        elif param.kind is param.POSITIONAL_OR_KEYWORD:
            kwargs[key] = _get_arg_value(param, data_map)
        elif param.kind is param.VAR_KEYWORD:
            raise TypeError("Unable to populate VAR_KEYWORD parameter '{}'".format(key))
        elif param.kind is param.VAR_POSITIONAL:
            raise TypeError("Unable to populate VAR_POSITIONAL parameter '{}'".format(key))
        else:
            raise TypeError("Unknown parameter type {!r}".format(param.kind))

    return args, kwargs


def call_with_args(func, arg_data):
    args, kwargs = _populate_args(func, arg_data)
    return func(*args, **kwargs)
