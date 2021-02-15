import logging

import cloudbot


def test_add_path(tmp_path):
    cloudbot.logging_info.dir = tmp_path / "logs"
    path = cloudbot.logging_info.add_path("raw.log")
    assert path == str(tmp_path / "logs" / "raw.log")


def test_setup(tmp_path):
    cloudbot._setup(tmp_path)
    logger = logging.getLogger("cloudbot")
    assert len(logger.handlers) == 1
    assert logger.handlers[0].name == "console"
    assert logger.level == logging.DEBUG
    assert logger.filters == []


def test_setup_with_config(tmp_path):
    (tmp_path / "config.json").write_text("{}")
    cloudbot._setup(tmp_path)
    logger = logging.getLogger("cloudbot")
    assert len(logger.handlers) == 1
    assert logger.handlers[0].name == "console"
    assert logger.level == logging.DEBUG
    assert logger.filters == []
