from __future__ import annotations

import datetime
from sqlalchemy import String, Integer, Boolean, Date, DateTime, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from database import Base


class DailyChallenge(Base):
    """One record per calendar day storing the chosen character and generated prompt."""

    __tablename__ = "daily_challenges"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    date: Mapped[datetime.date] = mapped_column(Date, unique=True, nullable=False, index=True)
    character_name: Mapped[str] = mapped_column(String(200), nullable=False)
    character_category: Mapped[str] = mapped_column(String(100), nullable=False)  # movie, book, game, etc.
    generated_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    intro_clue: Mapped[str] = mapped_column(Text, nullable=False)  # short teaser shown to user
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class GameSession(Base):
    """Tracks every user attempt – both daily and free-play sessions."""

    __tablename__ = "game_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    mode: Mapped[str] = mapped_column(String(20), nullable=False, default="daily")  # daily | freeplay
    challenge_date: Mapped[datetime.date | None] = mapped_column(Date, nullable=True, index=True)
    character_name: Mapped[str] = mapped_column(String(200), nullable=False)
    question_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    solved: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    solved_at: Mapped[datetime.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
