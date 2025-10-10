"""
database - contains variables set by cloudbot to be easily access
"""

from sqlalchemy import MetaData
from sqlalchemy.engine import Engine
from sqlalchemy.orm import (
    close_all_sessions,
    declarative_base,
    scoped_session,
    sessionmaker,
)

__all__ = ("metadata", "base", "Base", "Session", "configure")


Base = declarative_base()
base = Base
metadata: MetaData = Base.metadata
Session = scoped_session(sessionmaker(future=True))


def configure(bind: Engine = None) -> None:
    close_all_sessions()
    Session.remove()
    Session.configure(bind=bind)
