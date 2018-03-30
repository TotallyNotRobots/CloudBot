import sys

# check python version
if sys.version_info < (3, 4, 0):
    sys.exit("CloudBot requires Python 3.4 or newer.")

__version__ = (2, 0, 0, 'alpha', 0)

__all__ = ["clients", "util", "bot", "client", "config", "event", "hook", "permissions", "plugin", "reloader"]
