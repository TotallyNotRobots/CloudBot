import json
import logging
import sys
import time
from collections import OrderedDict
from pathlib import Path

logger = logging.getLogger("cloudbot")


class Config(OrderedDict):
    def __init__(self, bot, *, filename="config.json"):
        super().__init__()
        self.filename = filename
        self.path = Path(self.filename).resolve()
        self.bot = bot

        self._api_keys = {}

        # populate self with config data
        self.load_config()

    def get_api_key(self, name, default=None):
        try:
            return self._api_keys[name]
        except LookupError:
            self._api_keys[name] = value = self.get("api_keys", {}).get(
                name, default
            )
            return value

    def load_config(self):
        """(re)loads the bot config from the config file"""
        self._api_keys.clear()
        if not self.path.exists():
            # if there is no config, show an error and die
            logger.critical("No config file found, bot shutting down!")
            print("No config file found! Bot shutting down in five seconds.")
            print("Copy 'config.default.json' to 'config.json' for defaults.")
            print(
                "For help, see htps://github.com/TotallyNotRobots/CloudBot. "
                "Thank you for using CloudBot!"
            )
            time.sleep(5)
            sys.exit()

        with self.path.open(encoding="utf-8") as f:
            data = json.load(f, object_pairs_hook=OrderedDict)

        self.update(data)
        logger.debug("Config loaded from file.")

    def save_config(self):
        """saves the contents of the config dict to the config file"""
        with self.path.open("w", encoding="utf-8") as f:
            json.dump(self, f, indent=4)

        logger.info("Config saved to file.")
