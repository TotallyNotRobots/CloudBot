from typing import Any

from sqlalchemy import Table, create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

from cloudbot.util.database import Session


class MockDB:
    def __init__(self, path="sqlite:///:memory:", force_session=False):
        self.engine = create_engine(path)
        if force_session:
            self.session = scoped_session(
                sessionmaker(bind=self.engine, future=True)
            )
        else:
            self.session = Session

    def get_data(self, table):
        return self.session().execute(table.select()).fetchall()

    def add_row(self, table: Table, /, **data: Any) -> None:
        self.session().execute(table.insert().values(data))
        self.session().commit()

    def load_data(self, table: Table, data: list[dict[str, Any]]):
        with self.session() as session, session.begin():
            for item in data:
                session.execute(table.insert().values(item))
