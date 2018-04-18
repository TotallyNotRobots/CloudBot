import json
from contextlib import redirect_stdout
from io import StringIO
from tempfile import NamedTemporaryFile
from unittest import mock

import pytest


def test_config_load():
    data = {"a": ["b", "c"]}
    with redirect_stdout(StringIO()), NamedTemporaryFile() as cfg_file:
        cfg_file.file.write(json.dumps(data).encode() + b'\n')
        cfg_file.file.flush()
        filename_prop = property(lambda *args: cfg_file.name, lambda *args: None)
        with mock.patch('cloudbot.config.Config.filename', filename_prop, create=True):
            from cloudbot.config import Config
            assert data == Config()


def test_failed_config_load():
    with mock.patch('os.path.exists', lambda *args, **kwargs: False), \
         mock.patch('time.sleep', lambda *args, **kwargs: None), \
         pytest.raises(SystemExit), redirect_stdout(StringIO()):
        from cloudbot.config import Config
        Config()
