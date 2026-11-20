"""
database - contains variables set by cloudbot to be easily access
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy.orm import (
    DeclarativeBase,
    MappedAsDataclass,
    close_all_sessions,
    scoped_session,
    sessionmaker,
)

if TYPE_CHECKING:
    from sqlalchemy import MetaData
    from sqlalchemy.engine import Engine

__all__ = ("metadata", "base", "Base", "Session", "configure")


class Base(MappedAsDataclass, DeclarativeBase):  # pyright: ignore[reportUnsafeMultipleInheritance]
    pass


base = Base

metadata: MetaData = Base.metadata
Session = scoped_session(sessionmaker(future=True))


def configure(bind: Engine | None = None) -> None:
    close_all_sessions()
    Session.remove()
    Session.configure(bind=bind)
