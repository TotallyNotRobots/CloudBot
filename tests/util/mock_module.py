class MockModule:
    def __init__(self, name=None, **kwargs):
        self.__name__ = name or "MockModule"
        self.__dict__.update(kwargs)
