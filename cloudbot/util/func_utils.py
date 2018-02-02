import inspect


class ParameterError(Exception):
    def __init__(self, name, valid_args):
        self.__init__(name, list(valid_args))

    def __str__(self):
        return "'{}' is not a valid parameter, valid parameters are: {}".format(self.args[0], self.args[1])


def call_with_args(func, arg_data):
    sig = inspect.signature(func)
    try:
        args = [arg_data[key] for key in sig.parameters.keys() if not key.startswith('_')]
    except KeyError as e:
        raise ParameterError(e.args[0], arg_data.keys()) from e

    return func(*args)
