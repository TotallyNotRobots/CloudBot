"""
database - contains variables set by cloudbot to be easily access
"""
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import scoped_session, sessionmaker

__all__ = ("metadata", "base", "Base", "Session", "configure")


Base = declarative_base()
base = Base
metadata = Base.metadata
Session = scoped_session(sessionmaker())


def configure(bind=None):
    metadata.bind = bind
    Session.configure(bind=bind)
