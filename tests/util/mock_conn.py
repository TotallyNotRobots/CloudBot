from unittest.mock import MagicMock


class MockConn:
    def __init__(self, *, nick=None, name=None):
        self.nick = nick or "TestBot"
        self.name = name or "testconn"
        self.config = {}
        self.history = {}
        self.reload = MagicMock()
        self.try_connect = MagicMock()
        self.notice = MagicMock()
        self.join = MagicMock()
        self.ready = True

    def is_nick_valid(self, nick):
        return True
