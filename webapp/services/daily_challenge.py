"""
Manages the daily challenge: fetches from DB or generates a new one via Claude.
"""
from __future__ import annotations

import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models import DailyChallenge
from services.characters import get_daily_character
from services.claude_service import generate_persona_prompt


async def get_or_create_daily(db: AsyncSession, date: datetime.date | None = None) -> DailyChallenge:
    """Return today's DailyChallenge, generating it if it doesn't exist yet."""
    if date is None:
        date = datetime.date.today()

    result = await db.execute(select(DailyChallenge).where(DailyChallenge.date == date))
    challenge = result.scalar_one_or_none()

    if challenge is not None:
        return challenge

    # Not generated yet – pick character and ask Claude
    character = get_daily_character(date)
    full_prompt, intro_clue = await generate_persona_prompt(character)

    challenge = DailyChallenge(
        date=date,
        character_name=character["name"],
        character_category=character["category"],
        generated_prompt=full_prompt,
        intro_clue=intro_clue,
    )
    db.add(challenge)
    await db.commit()
    await db.refresh(challenge)
    return challenge
