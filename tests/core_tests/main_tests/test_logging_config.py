from copy import deepcopy
from pathlib import Path

import pytest


def _check_value(obj, keys, expected):
    try:
        for key in keys:
            obj = obj[key]
    except KeyError:
        return False

    return expected == obj


DEFAULT = {
    "logging": {
        "console_debug": False,
        "file_debug": False,
        "show_plugin_loading": False,
        "show_motd": False,
        "show_server_info": False,
        "raw_file_log": False,
        "file_log": False
    }
}


@pytest.mark.parametrize("config_data,expected", [
    (
        {"console_debug": True},
        (("handlers", "console", "level"), "DEBUG")
    ),
    (
        {"console_debug": False},
        (("handlers", "console", "level"), "INFO")
    ),
    (
        {"file_log": True},
        (("handlers", "file", "class"), "logging.handlers.RotatingFileHandler")
    ),
    (
        {"file_debug": True},
        (("handlers", "debug_file", "class"), "logging.handlers.RotatingFileHandler")
    ),
    (
        {"file_log": True, "console_debug": True},
        (("loggers", "asyncio", "handlers"), ["console", "file"])
    ),
])
def test_logging_config(config_data, expected):
    from cloudbot.__main__ import generate_logging_config
    config = deepcopy(DEFAULT)
    config['logging'].update(config_data)
    cfg = generate_logging_config(Path("logs").resolve(), config)
    assert _check_value(cfg, expected[0], expected[1])
