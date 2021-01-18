from unittest.mock import MagicMock

import pytest

from cloudbot.config import Config


def test_config_load_no_file(tmp_path, capsys):
    bot = MagicMock()
    config_file = tmp_path / "config.json"
    with pytest.raises(SystemExit):
        Config(bot, filename=config_file)

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
    config_file.write_text("{}")
    bot = MagicMock()
    cfg = Config(bot, filename=config_file)
    cfg["foo"] = "bar"
    cfg.save_config()

    assert config_file.read_text() == '{\n    "foo": "bar"\n}'
