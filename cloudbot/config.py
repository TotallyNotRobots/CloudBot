import json
import logging
import os
import sys
import time
from collections import OrderedDict

logger = logging.getLogger("cloudbot")


class Config(OrderedDict):
    """
    :type filename: str
    :type path: str
    """

    def __init__(self, *args, **kwargs):
        """
        :type args: list
        :type kwargs: dict
        """
        super().__init__(*args, **kwargs)
        self.filename = "config.json"
        self.path = os.path.abspath(self.filename)
        self.update(*args, **kwargs)

        # populate self with config data
        self.load_config()

    def load_config(self):
        """(re)loads the bot config from the config file"""
        if not os.path.exists(self.path):
            # if there is no config, show an error and die
            logger.critical("No config file found, bot shutting down!")
            print("No config file found! Bot shutting down in five seconds.")
            print("Copy 'config.default.json' to 'config.json' for defaults.")
            print("For help, see http://git.io/cloudbotirc. Thank you for using CloudBot!")
            time.sleep(5)
            sys.exit()

        with open(self.path) as f:
            data = json.load(f, object_pairs_hook=OrderedDict)

        self.update(data)
        logger.debug("Config loaded from file.")

    def save_config(self):
        """saves the contents of the config dict to the config file"""
        with open(self.path, 'w') as f:
            json.dump(self, f, indent=4)

        logger.info("Config saved to file.")
