from unittest.mock import patch

import pytest

from cloudbot.config import Config
from tests.util.mock_bot import MockBot


@pytest.fixture()
def mock_sleep():
    with patch("time.sleep"):
        yield


def test_missing_config(tmp_path, capsys, mock_sleep):
    config_file = tmp_path / "config.json"
    bot = MockBot()
    with pytest.raises(SystemExit):
        Config(bot, filename=str(config_file))

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


def test_save(tmp_path):
    config_file = tmp_path / "config.json"
    config_file.write_text("{}", encoding="utf-8")
    bot = MockBot()
    config = Config(bot, filename=str(config_file))
    config["foo"] = "bar"
    config.save_config()

    assert config_file.read_text(encoding="utf-8") == '{\n    "foo": "bar"\n}'
