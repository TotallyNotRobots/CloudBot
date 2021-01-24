from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker


class MockDB:
    def __init__(self, path="sqlite:///:memory:"):
        self.engine = create_engine(path)
        self.session = scoped_session(sessionmaker(self.engine))

    def get_data(self, table):
        return self.session().execute(table.select()).fetchall()

    def add_row(self, *args, **data):
        table = args[0]
        self.session().execute(table.insert().values(data))
        self.session().commit()
