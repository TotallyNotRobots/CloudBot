from types import ModuleType
from typing import Any


class MockModule(ModuleType):
    def __init__(self, name: str | None = None, **kwargs: Any) -> None:  # pyright: ignore[reportAny] # Allow any attributes to be set
        super().__init__(name or "MockModule")
        self.__dict__.update(kwargs)
