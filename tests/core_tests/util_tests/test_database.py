import pytest
from sqlalchemy import Column, Integer, Table
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.declarative import declarative_base


def test_database():
    from cloudbot.util.database import metadata, base
    assert metadata is None
    assert base is None


@pytest.fixture(scope='session')
def db_base():
    return declarative_base()


@pytest.fixture(scope='session')
def db_metadata(db_base):
    return db_base.metadata


@pytest.fixture(scope='session')
def table(db_metadata):
    table = Table(
        'test_table',
        db_metadata,
        Column('test', Integer, unique=True),
    )
    return table


@pytest.fixture(scope='session')
def db_engine(db_metadata, table):
    from sqlalchemy import create_engine
    engine = create_engine("sqlite:///:memory:")
    db_metadata.bind = engine

    db_metadata.create_all()

    return engine


@pytest.fixture(scope='session')
def db_session(db_engine):
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.orm import scoped_session
    db_factory = sessionmaker(bind=db_engine)
    session = scoped_session(db_factory)
    return session


@pytest.fixture
def session_factory(db_session):
    from cloudbot.util.database import ContextSession
    return lambda: ContextSession(db_session())


def test_session(table, session_factory):
    with session_factory() as session:
        session.execute(table.delete())

    with session_factory() as session:
        results = session.execute(table.select()).fetchall()
        assert len(results) == 0

    with session_factory() as session:
        session.execute(table.insert().values(test=5))

    with session_factory() as session:
        results = session.execute(table.select()).fetchall()
        assert len(results) == 1
        assert results[0]['test'] == 5

    with pytest.raises(IntegrityError):
        with session_factory() as session:
            session.execute(table.insert().values(test=5))

    with session_factory() as session:
        results = session.execute(table.select()).fetchall()
        assert len(results) == 1
        assert results[0]['test'] == 5

    with pytest.raises(IntegrityError):
        with session_factory() as session:
            session.execute(table.insert().values(test=5))
            session.commit()

    with session_factory() as session:
        results = session.execute(table.select()).fetchall()
        assert len(results) == 1
        assert results[0]['test'] == 5
