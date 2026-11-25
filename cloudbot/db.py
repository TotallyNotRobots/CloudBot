import io
import logging

import alembic.command
import alembic.config

import cloudbot
from cloudbot.bot import AbstractBot, CloudBot, bot_instance


def get_db_version(cfg: alembic.config.Config) -> str:
    sio = io.StringIO()
    original_stdout = cfg.stdout
    cfg.stdout = sio
    alembic.command.current(cfg)
    cfg.stdout = original_stdout
    return sio.getvalue()


def get_schema_version(cfg: alembic.config.Config) -> str:
    sio = io.StringIO()
    original_stdout = cfg.stdout
    cfg.stdout = sio
    alembic.command.heads(cfg)
    cfg.stdout = original_stdout
    return sio.getvalue()


def db_init(bot: AbstractBot | None = None) -> bool:
    if bot is None:
        bot = CloudBot(create_connections=False)
        bot.plugin_manager.get_plugin_tables(bot.plugin_dir)

    return upgrade_db_schema(bot)


def upgrade_db_schema(bot: AbstractBot) -> bool:
    logger = logging.getLogger("cloudbot")
    upgrade_enabled = bot.config.get("upgrade_schema", False)
    cfg = alembic.config.Config(
        "alembic.ini", "pyproject.toml", attributes={"bot": bot}
    )
    if not upgrade_enabled:
        if get_db_version(cfg) != get_schema_version(cfg):
            logger.fatal(
                'Database schema is out of date and auto-updating is disabled! Use `alembic upgrade heads` or set `"upgrade_schema": true` in the config. NOTE: ALWAYS take a backup of the database before upgrading!'
            )
            return False
    else:
        alembic.command.upgrade(cfg, "heads")

    bot_instance.set(None)
    cloudbot._setup()
    return True
