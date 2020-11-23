import json
import logging
import logging.config
import os
import sys

# check python version
if sys.version_info < (3, 6):
    print("CloudBot requires Python 3.6 or newer.")
    sys.exit(1)


version = (1, 3, 0)
__version__ = ".".join(str(i) for i in version)

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
    dir = "logs"

    def make_dir(self):
        if not os.path.exists(self.dir):
            os.makedirs(self.dir)

    def add_path(self, *paths):
        return os.path.join(self.dir, *paths)


logging_info = LoggingInfo()


def _setup():
    if os.path.exists(os.path.abspath("config.json")):
        with open(os.path.abspath("config.json")) as config_file:
            json_conf = json.load(config_file)
        logging_config = json_conf.get("logging", {})
    else:
        logging_config = {}

    file_log = logging_config.get("file_log", False)
    console_level = (
        "INFO" if logging_config.get("console_log_info", True) else "WARNING"
    )

    logging_info.dir = os.path.join(os.path.abspath(os.path.curdir), "logs")

    logging_info.make_dir()

    logging.captureWarnings(True)

    logger_names = ["cloudbot", "plugins"]

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
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "brief",
                "level": console_level,
                "stream": "ext://sys.stdout",
            }
        },
        "loggers": {
            name: {"level": "DEBUG", "handlers": ["console"]}
            for name in logger_names
        },
    }

    if file_log:
        dict_config["handlers"]["file"] = {
            "class": "logging.handlers.RotatingFileHandler",
            "maxBytes": 1000000,
            "backupCount": 5,
            "formatter": "full",
            "level": "INFO",
            "encoding": "utf-8",
            "filename": logging_info.add_path("bot.log"),
        }

        for name in logger_names:
            dict_config["loggers"][name]["handlers"].append("file")

    if logging_config.get("console_debug", False):
        dict_config["handlers"]["console"]["level"] = "DEBUG"
        dict_config["loggers"]["asyncio"] = {
            "level": "DEBUG",
            "handlers": ["console"],
        }
        if file_log:
            dict_config["loggers"]["asyncio"]["handlers"].append("file")

    if logging_config.get("file_debug", False):
        dict_config["handlers"]["debug_file"] = {
            "class": "logging.handlers.RotatingFileHandler",
            "maxBytes": 1000000,
            "backupCount": 5,
            "formatter": "full",
            "encoding": "utf-8",
            "level": "DEBUG",
            "filename": logging_info.add_path("debug.log"),
        }
        for name in logger_names:
            dict_config["loggers"][name]["handlers"].append("debug_file")

    logging.config.dictConfig(dict_config)


_setup()
