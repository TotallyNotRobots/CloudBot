import logging
import logging.config
import os
import signal
import sys
import time
from pathlib import Path

import cloudbot
from .bot import CloudBot
from .config import Config
from .util import async_util


def generate_logging_config(log_dir, cfg):
    logging_config = cfg.get("logging", {})

    file_log = logging_config.get("file_log", False)

    dict_config = {
        "version": 1,
        "formatters": {
            "brief": {
                "format": "[%(asctime)s] [%(levelname)s] %(message)s",
                "datefmt": "%H:%M:%S"
            },
            "full": {
                "format": "[%(asctime)s] [%(levelname)s] %(message)s",
                "datefmt": "%Y-%m-%d][%H:%M:%S"
            }
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "brief",
                "level": "INFO",
                "stream": "ext://sys.stdout"
            }
        },
        "loggers": {
            "cloudbot": {
                "level": "DEBUG",
                "handlers": ["console"]
            }
        }
    }

    if file_log:
        dict_config["handlers"]["file"] = {
            "class": "logging.handlers.RotatingFileHandler",
            "maxBytes": 1000000,
            "backupCount": 5,
            "formatter": "full",
            "level": "INFO",
            "encoding": "utf-8",
            "filename": str(log_dir / "bot.log")
        }

        dict_config["loggers"]["cloudbot"]["handlers"].append("file")

    if logging_config.get("console_debug", False):
        dict_config["handlers"]["console"]["level"] = "DEBUG"
        dict_config["loggers"]["asyncio"] = {
            "level": "DEBUG",
            "handlers": ["console"]
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
            "filename": str(log_dir / "debug.log")
        }
        dict_config["loggers"]["cloudbot"]["handlers"].append("debug_file")

    return dict_config


def setup_default_logger(log_dir=None):
    """
    :type log_dir: str | Path
    """
    if log_dir is None:
        log_dir = Path("logs").resolve()

    cloudbot.logging_dir = log_dir

    logging.captureWarnings(True)
    log_dir.mkdir(parents=True, exist_ok=True)

    logging.config.dictConfig(generate_logging_config(log_dir, Config()))


def main():
    # store the original working directory, for use when restarting
    original_wd = Path().resolve()

    # Logging optimizations, doing it here because we only want to change this if we're the main file
    logging._srcfile = None
    logging.logThreads = 0
    logging.logProcesses = 0

    logger = logging.getLogger("cloudbot")

    setup_default_logger()

    logger.info("Starting CloudBot.")

    # create the bot
    _bot = CloudBot()

    # whether we are killed while restarting
    stopped_while_restarting = False

    # store the original SIGINT handler
    original_sigint = signal.getsignal(signal.SIGINT)

    # define closure for signal handling
    # The handler is called with two arguments: the signal number and the current stack frame
    # These parameters should NOT be removed
    # noinspection PyUnusedLocal
    def exit_gracefully(signum, frame):
        nonlocal stopped_while_restarting
        if not _bot:
            # we are currently in the process of restarting
            stopped_while_restarting = True
        else:
            async_util.run_coroutine_threadsafe(_bot.stop("Killed (Received SIGINT {})".format(signum)), _bot.loop)

        logger.warning("Bot received Signal Interrupt ({})".format(signum))

        # restore the original handler so if they do it again it triggers
        signal.signal(signal.SIGINT, original_sigint)

    signal.signal(signal.SIGINT, exit_gracefully)

    # start the bot master

    # CloudBot.run() will return True if it should restart, False otherwise
    restart = _bot.run()

    # the bot has stopped, do we want to restart?
    if restart:
        # remove reference to cloudbot, so exit_gracefully won't try to stop it
        _bot = None
        # sleep one second for timeouts
        time.sleep(1)
        if stopped_while_restarting:
            logger.info("Received stop signal, no longer restarting")
        else:
            # actually restart
            os.chdir(str(original_wd))
            args = sys.argv
            logger.info("Restarting Bot")
            logger.debug("Restart arguments: {}".format(args))
            for f in [sys.stdout, sys.stderr]:
                f.flush()
            # close logging, and exit the program.
            logger.debug("Stopping logging engine")
            logging.shutdown()
            os.execv(sys.executable, [sys.executable] + args)

    # close logging, and exit the program.
    logger.debug("Stopping logging engine")
    logging.shutdown()


if __name__ == '__main__':
    main()
