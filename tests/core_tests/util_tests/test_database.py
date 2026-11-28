from __future__ import annotations

from typing import TYPE_CHECKING

from cloudbot.util import database

if TYPE_CHECKING:
    from tests.util.mock_db import MockDB


def test_database(mock_db: MockDB) -> None:
    database.configure()
    assert database.Session().bind is None
    engine = mock_db.engine
    database.configure(engine)
    assert database.Session().bind is engine
