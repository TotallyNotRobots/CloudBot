from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

from cloudbot.util.database import Session


class MockDB:
    def __init__(self, path="sqlite:///:memory:", force_session=False):
        self.engine = create_engine(path)
        if force_session:
            self.session = scoped_session(sessionmaker(bind=self.engine))
        else:
            self.session = Session

    def get_data(self, table):
        return self.session().execute(table.select()).fetchall()

    def add_row(self, *args, **data):
        table = args[0]
        self.session().execute(table.insert().values(data))
        self.session().commit()
