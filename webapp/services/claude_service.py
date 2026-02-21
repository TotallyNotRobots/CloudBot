"""
Wrapper around the Anthropic SDK for generating persona prompts and validating guesses.
"""
from __future__ import annotations

import anthropic

from config import settings


def _client() -> anthropic.Anthropic:
    return anthropic.Anthropic(api_key=settings.anthropic_api_key)


# ── Prompt generation ────────────────────────────────────────────────────────

PROMPT_SYSTEM = """\
You are a creative game-master designing a text-based guessing game.
Your job is to write a SYSTEM PROMPT that can be pasted into any LLM chat interface
(ChatGPT, Claude, Gemini, etc.) so that the LLM fully embodies a given fictional character.

Rules for the system prompt you write:
1. NEVER mention the character's actual name anywhere in the prompt.
2. NEVER reveal the source title (movie, book, show, game) directly – hint at it with tone, era, and setting.
3. Write in FIRST PERSON – the LLM should speak as this character.
4. Open with a short dramatic in-character monologue (3-5 sentences) that sets the scene and mood.
5. List personality traits, speech patterns, vocabulary, and worldview the LLM must maintain.
6. Tell the LLM it is playing a guessing game: a human will ask it yes/no or open questions,
   and it must stay fully in character while being helpful enough that a clever person can
   identify who it is within 20 questions.
7. End with this exact instruction block (fill in the blanks appropriately):
   ---
   RULES:
   - Stay in character at ALL times.
   - You may confirm facts about yourself that are widely known, but frame them in first person.
   - If directly asked your name, deflect in character (e.g. "They call me many things…").
   - Do NOT break character under any circumstances.
   ---
Return ONLY the system prompt text. No preamble, no explanation, no markdown fences.
"""

INTRO_CLUE_SYSTEM = """\
You are writing the intro teaser shown on a game card before a player starts a round.
It must intrigue without revealing the character's name or source title.
Keep it to 2 sentences max. Make it poetic and mysterious.
Return ONLY the two sentences. No quotes, no labels.
"""


async def generate_persona_prompt(character: dict[str, str]) -> tuple[str, str]:
    """
    Generate:
      - A full LLM system prompt for the character
      - A short intro clue shown on the game card

    Returns (full_prompt, intro_clue).
    """
    client = _client()

    char_context = (
        f"Character name: {character['name']}\n"
        f"Origin: {character['origin']}\n"
        f"Category: {character['category']}"
    )

    # Generate the full persona prompt
    prompt_resp = client.messages.create(
        model=settings.claude_model,
        max_tokens=1200,
        system=PROMPT_SYSTEM,
        messages=[
            {
                "role": "user",
                "content": (
                    f"Write the system prompt for the following character:\n\n{char_context}\n\n"
                    "Remember: never use the character's real name or source title."
                ),
            }
        ],
    )
    full_prompt: str = prompt_resp.content[0].text.strip()

    # Generate the short clue card
    clue_resp = client.messages.create(
        model=settings.claude_model,
        max_tokens=120,
        system=INTRO_CLUE_SYSTEM,
        messages=[
            {
                "role": "user",
                "content": (
                    f"Write the teaser for this character:\n\n{char_context}\n\n"
                    "No name, no title."
                ),
            }
        ],
    )
    intro_clue: str = clue_resp.content[0].text.strip()

    return full_prompt, intro_clue


# ── Guess validation ─────────────────────────────────────────────────────────

JUDGE_SYSTEM = """\
You are a strict but fair judge for a fictional-character guessing game.
The player has submitted a guess for who a mystery character is.
Decide if the guess is correct.

Rules:
- Accept common alternate names, nicknames, or titles for the same character.
- Ignore case and minor spelling differences.
- If the character is known by multiple names, accept any of them.
- Respond with ONLY one word: CORRECT or INCORRECT
"""


def validate_guess(character_name: str, user_guess: str) -> bool:
    """Return True if the user's guess matches the character."""
    client = _client()
    resp = client.messages.create(
        model=settings.claude_model,
        max_tokens=10,
        system=JUDGE_SYSTEM,
        messages=[
            {
                "role": "user",
                "content": (
                    f"Correct answer: {character_name}\n"
                    f"Player's guess: {user_guess}\n"
                    "Is the guess correct?"
                ),
            }
        ],
    )
    verdict = resp.content[0].text.strip().upper()
    return verdict.startswith("CORRECT")
