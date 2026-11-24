from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest

from cloudbot.config import Config

if TYPE_CHECKING:
    from collections.abc import Generator


@pytest.fixture
def mock_sleep() -> Generator[None]:
    with patch("time.sleep"):
        yield


@pytest.mark.usefixtures("mock_sleep")
def test_missing_config(tmp_path, capsys) -> None:
    config_file = tmp_path / "config.json"
    with pytest.raises(SystemExit):
        Config(filename=str(config_file))

    data = capsys.readouterr()
    assert data.out == (
        "No config file found! Bot shutting down in five "
        "seconds.\n"
        "Copy 'config.default.json' to "
        "'config.json' for defaults.\n"
        "For help, "
        "see htps://github.com/TotallyNotRobots/CloudBot. "
        "Thank you for "
        "using CloudBot!\n"
    )


@pytest.mark.usefixtures("mock_sleep")
def test_loads(tmp_path) -> None:
    config_file = tmp_path / "config.json"
    config_file.write_text('{"a":1}')
    conf = Config(filename=str(config_file))
    assert dict(conf) == {"a": 1}
