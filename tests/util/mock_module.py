from typing import Any


class MockModule:
    def __init__(self, name: str | None = None, **kwargs: Any) -> None:  # pyright: ignore[reportAny] # Allow any attributes to be set
        self.__name__: str = name or "MockModule"
        self.__dict__.update(kwargs)
