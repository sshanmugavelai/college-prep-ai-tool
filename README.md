# College Prep AI Tool

Simple local SAT/ACT prep app for one student.  
Stack: **Python + Streamlit + Postgres + Claude API**.

No microservices. No Redis. No complex infra.

---

## 1) Simple Architecture (End-to-End)

### Streamlit UI flow
1. **Main workspace (`Dashboard.py` + `workspace_sections.py`)** — one screen with steps: **Overview**, **Generate tests**, **Take test**, **Review**.
   - *Overview*: metrics, weak topics, recent activity, recommended next practice.
   - *Generate*: exam/section/count/difficulty/timed; Claude JSON questions; list saved tests.
   - *Take test*: start attempt, one question at a time, optional timer, submit.
   - *Review*: attempt summary, per-question explanations, AI mistake feedback.
2. **Mistake Journal (`pages/1_Mistake_Journal.py`)**
   - list incorrect answers grouped/filterable by topic; retry tests from mistakes.
3. **Progress & Study Plan (`pages/2_Progress_and_Study_Plan.py`)**
   - score trend, topic accuracy, weekly AI study plan.
4. **AI Prompt Templates (`pages/3_AI_Prompts.py`)**
   - reusable prompts for generation, explanation, coaching.

### Backend logic (simple service/repository style)
- `ai/client.py`: Claude API wrapper, JSON-safe parsing.
- `ai/prompts.py`: reusable prompt templates.
- `db/repository.py`: SQL operations for tests/attempts/answers/mistakes/progress.
- `auth/google_oauth.py`: Google OAuth provider service (authorization URL, token exchange, userinfo mapping).
- `auth/policy.py`: fail-closed policy gating for admin-only controls.
- `auth/orchestrator.py`: orchestration between provider identity, DB user upsert, and auth result contract.
- `utils/validation.py`: validates Claude question JSON shape.
- `utils/session.py`: Streamlit session helpers.

### Database usage
- Postgres stores all persistent data:
  - generated tests and questions
  - student attempts and answers
  - mistake journal
  - progress snapshots and recommendations

### Claude integration
- Claude is used for:
1. question generation
2. mistake explanation
3. weekly plan generation
- Each call expects **structured JSON** and validates/parses before saving.

---

## 2) Postgres Schema (Minimal + Practical)

Schema file: `db/schema.sql`

- **tests**
  - metadata for generated tests (exam type, section, difficulty, timed)
- **questions**
  - generated question text, choices, answer key, explanation, topic
- **attempts**
  - one student run of a test, with final score
- **answers**
  - per-question answer for an attempt + correctness + optional AI feedback JSON
- **mistake_journal**
  - incorrect questions for targeted review/retry
- **progress**
  - snapshots of aggregate stats (avg score, weak topics, trends, recommendation)

### Quick schema map
- `tests (1) -> (many) questions`
- `tests (1) -> (many) attempts`
- `attempts (1) -> (many) answers`
- `answers (incorrect) -> mistake_journal`
- `attempts -> progress snapshots`

---

## 3) Folder Structure

```text
.
├── Dashboard.py
├── workspace_sections.py
├── pages/
│   ├── 1_Mistake_Journal.py
│   ├── 2_Progress_and_Study_Plan.py
│   └── 3_AI_Prompts.py
├── auth/
│   ├── contracts.py
│   ├── google_oauth.py
│   ├── orchestrator.py
│   └── policy.py
├── db/
│   ├── connection.py
│   ├── init_db.py
│   ├── repository.py
│   └── schema.sql
├── ai/
│   ├── client.py
│   └── prompts.py
├── utils/
│   ├── formatting.py
│   ├── session.py
│   └── validation.py
├── requirements.txt
├── .env.example
└── README.md
```

---

## 4) Step-by-Step Implementation Plan

This is the practical build order.

### Step 1: Basic app shell + DB
1. Create Streamlit app + pages.
2. Add Postgres connection and schema.
3. Add dashboard query stubs.

### Step 2: Test generator
1. Build Claude question-generation prompt.
2. Call Claude API.
3. Validate JSON shape.
4. Save `tests` + `questions`.

### Step 3: Test taking flow
1. Start attempt (`attempts` row).
2. Render one question at a time.
3. Save answer selections (`answers`).
4. Submit and compute score.

### Step 4: Review system
1. Show each question with selected vs correct answer.
2. Show base explanation from question payload.
3. Show attempt summary stats.

### Step 5: AI explanations
1. For wrong answers, call Claude with context.
2. Save JSON feedback into `answers.ai_feedback`.
3. Store concept in `mistake_journal`.

### Step 6: Progress tracking + coaching
1. Build trend/accuracy SQL queries.
2. Render line + bar charts.
3. Build performance summary text.
4. Generate weekly plan via Claude.

---

## 5) Starter Code Included

Implemented and ready:
- Streamlit app skeleton and multipage UI
- Postgres setup/init script + SQL schema
- Claude question generation function
- Attempt/answer persistence and scoring
- Review + AI mistake explanations
- Mistake journal and retry test generation
- Progress charts + weekly study plan generation

---

## 6) Claude Prompt Templates

File: `ai/prompts.py`

### Question generation (required JSON)
```json
{
  "questions": [
    {
      "question": "...",
      "choices": ["A", "B", "C", "D"],
      "correct_answer": "B",
      "explanation": "...",
      "topic": "algebra",
      "difficulty": "medium"
    }
  ]
}
```

### Mistake explanation (required JSON)
```json
{
  "correct_explanation": "...",
  "why_user_wrong": "...",
  "concept_to_learn": "...",
  "difficulty_adjustment": "increase/decrease/same"
}
```

### Study plan (JSON)
```json
{
  "weekly_plan": [
    {
      "day": "Monday",
      "focus_topics": ["algebra"],
      "questions_target": 20,
      "schedule_tip": "..."
    }
  ],
  "overall_advice": "..."
}
```

---

## Local setup (development machine)

The app talks to **one** Postgres database: whatever you set in `DATABASE_URL`. For this project we use **[Neon](https://neon.tech)** (free tier) — not a separate database on your laptop.

### Prerequisites
- Python 3.11+
- A Neon account and project (Postgres in the cloud)
- Claude API key

### 1) Clone and install
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2) Environment variables (Neon)
```bash
cp .env.example .env
```

Edit `.env`:

1. In the **Neon Console**, open your project → **Connect** → copy the **connection string** (URI).
2. Set `DATABASE_URL` to that URI. It must include SSL, e.g.  
   `postgresql://USER:PASSWORD@ep-xxxxx.region.aws.neon.tech/neondb?sslmode=require`
3. Set `ANTHROPIC_API_KEY` and optional `ANTHROPIC_MODEL`.

There is **no** second “local Postgres” to configure for normal use. If `DATABASE_URL` points at Neon, every query and migration uses Neon.

### 3) Create tables on Neon (once per empty database)
With `.env` pointing at Neon:

```bash
python -c "from db.init_db import init_db; init_db()"
```

Or start the app and click **Initialize / Verify Database** in the sidebar (admin users only).

### 4) Run the app
```bash
streamlit run Dashboard.py
```

### Authentication (Google OAuth)
- Login is Google-based only (no local username/password prompt in UI).
- Set:
  - `GOOGLE_OAUTH_CLIENT_ID`
  - `GOOGLE_OAUTH_CLIENT_SECRET`
  - `GOOGLE_OAUTH_REDIRECT_URI`
- Per-user records are still stored in local DB (`users`), linked via `user_identities(provider, subject, email)`.
- Learner level is inferred on first login:
  - emails in `MIDDLE_SCHOOL_EMAILS` -> `middle_school`
  - everyone else -> `sat`

### Admin gating (fail-closed)
- Sidebar maintenance actions (**Initialize / Verify Database**, **Clear caches only**) are hidden unless email is in `ADMIN_EMAILS`.
- If admin list is empty, everyone is treated as non-admin (fail-closed).

### Donations
- Optional PayPal donate button appears in sidebar when `PAYPAL_DONATE_URL` is configured.

### Streamlit Community Cloud
Use the **same** `DATABASE_URL` (Neon URI) and API keys under **App settings → Secrets** — not `localhost`.

### Optional: Postgres on your own machine
Only if you explicitly want Docker/local Postgres for experiments: run a container, create a database, and set `DATABASE_URL` to that instance instead of Neon. The application code is identical.

---

## 7) Keep It Practical (design choices)

- Single Python app process
- Direct SQL via psycopg (no ORM complexity)
- No background workers
- No caching layer required
- JSON contracts for AI calls to keep storage simple

## Product architecture boundaries (for growth to 100+ users)

- **Detection/services**
  - `auth/google_oauth.py` handles provider protocol and identity extraction only.
- **Policy/gating**
  - `auth/policy.py` computes admin capability flags from config/email.
- **Orchestration**
  - `auth/orchestrator.py` coordinates callback completion and user upsert.
- **Lifecycle state**
  - `utils/session.py` owns auth session state contract (`user_id`, `email`, `is_admin`, etc.).
- **Reporting/UI**
  - `utils/auth_ui.py` renders login/account/admin/donate sidebar sections and reuses policy/orchestrator contracts.

This keeps auth/donation/admin behavior composable and avoids ad hoc logic spread across pages.

---

## Absolute Minimum Version to Build First

If you want the tiniest V1:
1. Generate questions (Claude -> save test/questions)
2. Take test (answer + submit)
3. Review score and explanations

Everything else can be layered later.

---

## How to Test Quickly

1. Start app.
2. Initialize DB.
3. Generate a 5-question SAT Math medium test.
4. Take it, intentionally miss 2 answers.
5. Open Review page and generate AI feedback.
6. Confirm Mistake Journal shows those mistakes.
7. Open Progress page and confirm score trend + topic accuracy render.

---

## Improve Step by Step

1. Add student profile support (if multiple kids later).
2. Add saved study plans and completion checkboxes.
3. Add question quality guardrails (dedupe/similarity checks).
4. Add difficulty adaptation rule tied to recent score deltas.
5. Add export (CSV/PDF) for parent review meetings.
