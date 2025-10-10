from unittest.mock import patch

import pytest

from cloudbot.config import Config


@pytest.fixture()
def mock_sleep():
    with patch("time.sleep"):
        yield


def test_missing_config(
    tmp_path,
    capsys,
    mock_sleep,
    mock_bot,
):
    config_file = tmp_path / "config.json"
    bot = mock_bot
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


def test_save(mock_bot, tmp_path):
    config_file = tmp_path / "config.json"
    config_file.write_text("{}", encoding="utf-8")
    bot = mock_bot
    config = Config(bot, filename=str(config_file))
    config["foo"] = "bar"
    config.save_config()

    assert config_file.read_text(encoding="utf-8") == '{\n    "foo": "bar"\n}'
