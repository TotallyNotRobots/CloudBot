import importlib
from unittest import mock

import pytest


def test_python_version_check():
    with mock.patch('sys.version_info', (3, 3, 0)):
        with pytest.raises(SystemExit):
            import cloudbot
            importlib.reload(cloudbot)
