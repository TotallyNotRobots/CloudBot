import json
import logging
import logging.config
from pathlib import Path
from typing import cast

__version__ = "1.5.0"
version = tuple(__version__.split("."))

__all__ = (
    "clients",
    "util",
    "bot",
    "client",
    "config",
    "event",
    "hook",
    "permissions",
    "plugin",
    "reloader",
    "logging_info",
    "version",
    "__version__",
)


class LoggingInfo:
    dir = Path("logs")

    def make_dir(self) -> None:
        self.dir.mkdir(exist_ok=True, parents=True)

    def add_path(self, *paths: str) -> str:
        p = self.dir
        for part in paths:
            p = p / part

        return str(p)


logging_info = LoggingInfo()


def _setup(base_path: Path | None = None) -> None:
    base_path = base_path or Path().resolve()
    cfg_file = base_path / "config.json"
    if cfg_file.exists():
        with open(cfg_file, encoding="utf-8") as config_file:
            json_conf = json.load(config_file)
        logging_config = json_conf.get("logging", {})
    else:
        logging_config = {}

    logger_names = ["cloudbot", "plugins"]
    if logging_config.get("console_debug", False):
        console_level = logging.DEBUG
        logger_names.append("asyncio")
    elif logging_config.get("console_log_info", True):
        console_level = logging.INFO
    else:
        console_level = logging.WARNING

    logging_info.dir = base_path / "logs"

    logging_info.make_dir()

    logging.captureWarnings(True)

    default_handlers = ["console"]
    handler_configs = {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "brief",
            "level": console_level,
            "stream": "ext://sys.stdout",
        }
    }

    file_log = logging_config.get("file_log", False)
    if file_log:
        handler_configs["file"] = {
            "class": "logging.handlers.RotatingFileHandler",
            "maxBytes": 1000000,
            "backupCount": 5,
            "formatter": "full",
            "level": "INFO",
            "encoding": "utf-8",
            "filename": logging_info.add_path("bot.log"),
        }

        default_handlers.append("file")

    if logging_config.get("file_debug", False):
        handler_configs["debug_file"] = {
            "class": "logging.handlers.RotatingFileHandler",
            "maxBytes": 1000000,
            "backupCount": 5,
            "formatter": "full",
            "encoding": "utf-8",
            "level": "DEBUG",
            "filename": logging_info.add_path("debug.log"),
        }

        default_handlers.append("debug_file")

    def _get_level_value(level: str | int) -> int:
        if isinstance(level, str):
            return cast("int", getattr(logging, level))

        return level

    # This will drasticly reduce the logging performance hit by ensuring calls
    # that would route nowhere don't get made
    default_logger_level = min(
        [
            _get_level_value(cast("str | int", handler["level"]))
            for handler in handler_configs.values()
        ]
        + [logging.WARNING]
    )

    dict_config = {
        "version": 1,
        "formatters": {
            "brief": {
                "format": "[%(asctime)s] [%(levelname)s] %(message)s",
                "datefmt": "%H:%M:%S",
            },
            "full": {
                "format": "[%(asctime)s] [%(levelname)s] %(message)s",
                "datefmt": "%Y-%m-%d][%H:%M:%S",
            },
        },
        "handlers": handler_configs.copy(),
        "loggers": {
            name: {
                "level": default_logger_level,
                "handlers": default_handlers.copy(),
                "propagate": False,
            }
            for name in logger_names
        },
        "root": {
            "level": default_logger_level,
            "handlers": default_handlers.copy(),
        },
    }

    logging.config.dictConfig(dict_config)


_setup()
