from __future__ import annotations

from contextlib import AbstractContextManager
from typing import TYPE_CHECKING, Any

from sqlalchemy import Table, create_engine
from sqlalchemy.orm import close_all_sessions, scoped_session, sessionmaker

from cloudbot.util.database import Session

if TYPE_CHECKING:
    from types import TracebackType

    from sqlalchemy import Table
    from typing import Self


class MockDB(AbstractContextManager):
    def __init__(self, path="sqlite:///:memory:", force_session=False) -> None:
        self.engine = create_engine(path, future=True)
        if force_session:
            self.session = scoped_session(
                sessionmaker(bind=self.engine, future=True)
            )
        else:
            self.session = Session

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.close()

    def close(self) -> None:
        self.session.remove()
        close_all_sessions()
        self.engine.dispose()

    def get_data(self, table):
        return self.session().execute(table.select()).fetchall()

    def add_row(self, table: Table, /, **data: Any) -> None:
        self.session().execute(table.insert().values(data))
        self.session().commit()

    def load_data(self, table: Table, data: list[dict[str, Any]]) -> None:
        with self.session() as session, session.begin():
            for item in data:
                session.execute(table.insert().values(item))
