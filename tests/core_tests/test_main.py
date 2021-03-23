import logging
from unittest.mock import patch

from cloudbot.__main__ import main


def test_main():
    with patch("cloudbot.__main__.CloudBot") as mocked:
        mocked().run.return_value = False
        main()
        assert logging._srcfile is None
        assert not logging.logThreads
        assert not logging.logProcesses
