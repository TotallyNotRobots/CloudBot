from typing import Any
from unittest.mock import MagicMock


class AsyncMock(MagicMock):
    async def __call__(self, *args: Any, **kwargs: Any) -> Any:  # pyright: ignore[reportAny] # TODO: is this still necessary? default mocks support async now?
        return super().__call__(*args, **kwargs)
