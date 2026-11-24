from __future__ import annotations

from typing import TYPE_CHECKING, Any
from unittest.mock import MagicMock, patch

import pytest

if TYPE_CHECKING:
    from collections.abc import Callable, Generator


@pytest.fixture
def patch_paste() -> Generator[MagicMock]:
    with patch("cloudbot.util.web.paste") as mock:
        yield mock


@pytest.fixture
def patch_try_shorten() -> Generator[Callable[..., Any]]:
    with patch("cloudbot.util.web.try_shorten", new=lambda x, **kwargs: x) as p:  # noqa: ARG005
        yield p
