"""
All JSON API routes for the Who Am I? game.
"""
from __future__ import annotations

import datetime
import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models import DailyChallenge, GameSession
from services.characters import get_random_character
from services.claude_service import generate_persona_prompt, validate_guess
from services.daily_challenge import get_or_create_daily
from services.fun_facts import get_facts_page, get_random_fact

router = APIRouter(prefix="/api")


# ── Schemas ──────────────────────────────────────────────────────────────────

class DailyChallengeOut(BaseModel):
    date: str
    intro_clue: str
    generated_prompt: str
    category: str

    model_config = {"from_attributes": True}


class FreePlayOut(BaseModel):
    session_id: str
    character_name: str          # kept server-side in session; returned so client can track
    intro_clue: str
    generated_prompt: str
    category: str


class GuessIn(BaseModel):
    username: str = Field(..., min_length=1, max_length=80)
    guess: str = Field(..., min_length=1, max_length=200)
    question_count: int = Field(..., ge=0)
    mode: str = Field(default="daily")                # daily | freeplay
    challenge_date: str | None = None                  # ISO date, daily mode only
    character_name: str | None = None                  # freeplay mode only


class GuessOut(BaseModel):
    correct: bool
    character_name: str
    message: str


class LeaderboardEntry(BaseModel):
    rank: int
    username: str
    question_count: int
    solved_at: str
    challenge_date: str


class FunFactsOut(BaseModel):
    facts: list[str]


# ── Daily challenge ──────────────────────────────────────────────────────────

@router.get("/daily", response_model=DailyChallengeOut)
async def get_daily(db: AsyncSession = Depends(get_db)):
    """Return today's challenge prompt and clue (character name withheld)."""
    challenge = await get_or_create_daily(db)
    return DailyChallengeOut(
        date=challenge.date.isoformat(),
        intro_clue=challenge.intro_clue,
        generated_prompt=challenge.generated_prompt,
        category=challenge.character_category,
    )


# ── Free-play ────────────────────────────────────────────────────────────────

@router.post("/generate", response_model=FreePlayOut)
async def generate_freeplay():
    """Generate a random character prompt for a free-play session."""
    character = get_random_character()
    full_prompt, intro_clue = await generate_persona_prompt(character)
    return FreePlayOut(
        session_id=str(uuid.uuid4()),
        character_name=character["name"],
        intro_clue=intro_clue,
        generated_prompt=full_prompt,
        category=character["category"],
    )


# ── Guess submission ─────────────────────────────────────────────────────────

@router.post("/guess", response_model=GuessOut)
async def submit_guess(body: GuessIn, db: AsyncSession = Depends(get_db)):
    """
    Validate the player's guess.
    For daily mode the server fetches the stored character name from DB.
    For freeplay the client sends back the character_name it received earlier.
    """
    if body.mode == "daily":
        date = (
            datetime.date.fromisoformat(body.challenge_date)
            if body.challenge_date
            else datetime.date.today()
        )
        challenge = await get_or_create_daily(db, date)
        correct_name = challenge.character_name
    elif body.mode == "freeplay":
        if not body.character_name:
            raise HTTPException(status_code=400, detail="character_name required for freeplay mode")
        correct_name = body.character_name
    else:
        raise HTTPException(status_code=400, detail="mode must be 'daily' or 'freeplay'")

    is_correct = validate_guess(correct_name, body.guess)

    # Persist the attempt
    session = GameSession(
        username=body.username,
        mode=body.mode,
        challenge_date=date if body.mode == "daily" else None,
        character_name=correct_name,
        question_count=body.question_count,
        solved=is_correct,
        solved_at=datetime.datetime.utcnow() if is_correct else None,
    )
    db.add(session)
    await db.commit()

    if is_correct:
        msg = f"🎉 Correct! It was {correct_name}. You got it in {body.question_count} question(s)!"
    else:
        msg = f"Not quite… keep asking more questions and try again!"

    return GuessOut(correct=is_correct, character_name=correct_name if is_correct else "???", message=msg)


# ── Leaderboard ──────────────────────────────────────────────────────────────

@router.get("/leaderboard", response_model=list[LeaderboardEntry])
async def get_leaderboard(
    mode: str = "daily",
    date: str | None = None,
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
):
    """
    Return the top players for the daily challenge.
    Ranked by fewest questions, then earliest solve time.
    """
    query = (
        select(GameSession)
        .where(GameSession.solved == True)  # noqa: E712
        .where(GameSession.mode == mode)
    )

    if mode == "daily":
        target_date = datetime.date.fromisoformat(date) if date else datetime.date.today()
        query = query.where(GameSession.challenge_date == target_date)

    query = query.order_by(GameSession.question_count.asc(), GameSession.solved_at.asc()).limit(limit)

    result = await db.execute(query)
    rows = result.scalars().all()

    return [
        LeaderboardEntry(
            rank=idx + 1,
            username=row.username,
            question_count=row.question_count,
            solved_at=row.solved_at.isoformat() if row.solved_at else "",
            challenge_date=row.challenge_date.isoformat() if row.challenge_date else "",
        )
        for idx, row in enumerate(rows)
    ]


# ── Fun facts ────────────────────────────────────────────────────────────────

@router.get("/funfacts", response_model=FunFactsOut)
async def get_fun_facts(count: int = 3):
    return FunFactsOut(facts=get_facts_page(count))


@router.get("/funfact", response_model=dict)
async def get_single_fact():
    return {"fact": get_random_fact()}
