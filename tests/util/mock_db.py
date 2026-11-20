from __future__ import annotations

from contextlib import AbstractContextManager
from typing import TYPE_CHECKING, Any

from sqlalchemy import Table, create_engine, insert, inspect, select
from sqlalchemy.orm import close_all_sessions, scoped_session, sessionmaker

from cloudbot.util.database import Base, Session

if TYPE_CHECKING:
    from collections.abc import Sequence
    from types import TracebackType
    from typing import Self

    from sqlalchemy.engine.row import Row


class MockDB(AbstractContextManager):
    def __init__(
        self, path: str = "sqlite:///:memory:", force_session: bool = False
    ) -> None:
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

    def _get_table(self, table: Table | type[Base]) -> Table:
        if not isinstance(table, Table):
            inspector = inspect(table)
            local_table = inspector.local_table
            if not isinstance(local_table, Table):
                raise TypeError(f"Can't get Table from {table.__name__}")
            return local_table
        return table

    def create_table(self, table: Table | type[Base]) -> None:
        self._get_table(table).create(self.engine, checkfirst=True)

    def close(self) -> None:
        self.session.remove()
        close_all_sessions()
        self.engine.dispose()

    def get_data(self, table: Table | type[Base]) -> Sequence[Row[Any]]:
        return self.session().execute(select(self._get_table(table))).fetchall()

    def add_row(self, table: Table | type[Base], /, **data: Any) -> None:  # pyright: ignore[reportAny]
        self.session().execute(insert(table).values(data))
        self.session().commit()

    def load_data(
        self, table: Table | type[Base], data: list[dict[str, Any]]
    ) -> None:
        with self.session() as session, session.begin():
            for item in data:
                session.execute(insert(table).values(item))
