import asyncio
from unittest.mock import MagicMock

import pytest


@pytest.mark.parametrize('text', [
    'VERSION',
    'PING 1',
    'TIME',
])
def test_ctcp_handler(text):
    loop = asyncio.get_event_loop()
    from plugins.core.core_ctcp import ctcp_version
    notice = MagicMock()
    loop.run_until_complete(ctcp_version(notice, text))

    assert notice.called
