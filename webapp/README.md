# Who Am I? – LLM Persona Guessing Game

A free, fun guessing game where you figure out a fictional character by
interrogating a mystery persona through any LLM chatbot.

## Quick Start

```bash
cd webapp

# 1. Install dependencies
pip install -r requirements.txt

# 2. Create your .env file
cp .env.example .env
# Edit .env and set ANTHROPIC_API_KEY

# 3. Run
uvicorn main:app --reload --port 8000
```

Open **http://localhost:8000** in your browser.

## How to play

1. Click **Daily Challenge** or **Free Play** to generate a mystery persona prompt.
2. Copy the prompt and paste it as the **system prompt** in ChatGPT, Claude, Gemini, etc.
3. Ask the LLM yes/no questions to figure out who the character is.
4. Come back here, enter your question count and guess, then submit.
5. Correct? You're on the leaderboard!

## Project layout

```
webapp/
├── main.py                  # FastAPI entry point
├── config.py                # Settings (env vars)
├── database.py              # SQLAlchemy async engine
├── models.py                # ORM models
├── services/
│   ├── characters.py        # 90+ character pool + daily seeding
│   ├── claude_service.py    # Anthropic API: prompt gen + guess validation
│   ├── daily_challenge.py   # DB-backed daily challenge management
│   └── fun_facts.py         # Static LLM fun facts
├── routers/
│   └── api.py               # All /api/* JSON endpoints
├── templates/
│   └── index.html           # Single-page UI
├── static/
│   ├── css/style.css
│   └── js/app.js
├── requirements.txt
└── .env.example
```

## Environment variables

| Variable           | Required | Default                                  |
|--------------------|----------|------------------------------------------|
| `ANTHROPIC_API_KEY`| ✅ Yes   | —                                        |
| `DATABASE_URL`     | No       | `sqlite+aiosqlite:///./whoami.db`        |
| `DEBUG`            | No       | `false`                                  |

## API Reference

| Method | Path                     | Description                       |
|--------|--------------------------|-----------------------------------|
| GET    | `/api/daily`             | Today's challenge prompt & clue   |
| POST   | `/api/generate`          | Random free-play character prompt |
| POST   | `/api/guess`             | Submit and validate a guess       |
| GET    | `/api/leaderboard`       | Top scores for daily challenge    |
| GET    | `/api/funfacts?count=N`  | N random LLM fun facts            |
| GET    | `/api/funfact`           | Single random fact                |
| GET    | `/health`                | Health check                      |
