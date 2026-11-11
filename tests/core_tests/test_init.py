import json
import logging

import cloudbot


def test_add_path(tmp_path) -> None:
    cloudbot.logging_info.dir = tmp_path / "logs"
    path = cloudbot.logging_info.add_path("raw.log")
    assert path == str(tmp_path / "logs" / "raw.log")


def test_setup(tmp_path) -> None:
    cloudbot._setup(tmp_path)
    logger = logging.getLogger("cloudbot")
    assert len(logger.handlers) == 1
    assert logger.handlers[0].name == "console"
    assert logger.level == logging.INFO
    assert logger.filters == []


def test_setup_with_config(tmp_path) -> None:
    (tmp_path / "config.json").write_text("{}")
    cloudbot._setup(tmp_path)
    logger = logging.getLogger("cloudbot")
    assert len(logger.handlers) == 1
    assert logger.handlers[0].name == "console"
    assert logger.level == logging.INFO
    assert logger.filters == []


def test_setup_with_config_console_debug(tmp_path) -> None:
    (tmp_path / "config.json").write_text(
        json.dumps({"logging": {"console_debug": True}})
    )
    cloudbot._setup(tmp_path)
    logger = logging.getLogger("cloudbot")
    assert len(logger.handlers) == 1
    assert logger.handlers[0].name == "console"
    assert logger.level == logging.DEBUG
    assert logger.filters == []


def test_setup_with_config_console_log_info_false(tmp_path) -> None:
    (tmp_path / "config.json").write_text(
        json.dumps({"logging": {"console_log_info": False}})
    )
    cloudbot._setup(tmp_path)
    logger = logging.getLogger("cloudbot")
    assert len(logger.handlers) == 1
    assert logger.handlers[0].name == "console"
    assert logger.level == logging.WARNING
    assert logger.filters == []


def test_setup_with_config_file_log(tmp_path) -> None:
    (tmp_path / "config.json").write_text(
        json.dumps({"logging": {"file_log": True}})
    )
    cloudbot._setup(tmp_path)
    logger = logging.getLogger("cloudbot")
    assert len(logger.handlers) == 2
    assert logger.handlers[0].name == "console"
    assert logger.handlers[1].name == "file"
    assert logger.level == logging.INFO
    assert logger.filters == []


def test_setup_with_config_file_debug(tmp_path) -> None:
    (tmp_path / "config.json").write_text(
        json.dumps({"logging": {"file_debug": True}})
    )
    cloudbot._setup(tmp_path)
    logger = logging.getLogger("cloudbot")
    assert len(logger.handlers) == 2
    assert logger.handlers[0].name == "console"
    assert logger.handlers[1].name == "debug_file"
    assert logger.level == logging.DEBUG
    assert logger.filters == []
