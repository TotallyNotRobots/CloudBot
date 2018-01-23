import inspect


def call_with_args(func, arg_data):
    sig = inspect.signature(func)
    args = [arg_data[key] for key in sig.parameters.keys() if not key.startswith('_')]
    return func(*args)
