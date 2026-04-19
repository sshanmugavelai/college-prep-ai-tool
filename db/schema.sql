CREATE TABLE IF NOT EXISTS tests (
    id BIGSERIAL PRIMARY KEY,
    exam_type TEXT NOT NULL CHECK (exam_type IN ('SAT', 'ACT')),
    section TEXT NOT NULL CHECK (section IN ('Reading', 'Writing', 'Math')),
    num_questions INTEGER NOT NULL CHECK (num_questions > 0),
    difficulty TEXT NOT NULL CHECK (difficulty IN ('easy', 'medium', 'hard')),
    timed BOOLEAN NOT NULL DEFAULT FALSE,
    time_limit_minutes INTEGER,
    source TEXT NOT NULL DEFAULT 'ai',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS questions (
    id BIGSERIAL PRIMARY KEY,
    test_id BIGINT NOT NULL REFERENCES tests(id) ON DELETE CASCADE,
    question_order INTEGER NOT NULL,
    question_text TEXT NOT NULL,
    choices JSONB NOT NULL,
    correct_answer TEXT NOT NULL,
    explanation TEXT NOT NULL,
    topic TEXT NOT NULL,
    difficulty TEXT NOT NULL CHECK (difficulty IN ('easy', 'medium', 'hard')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (test_id, question_order)
);

CREATE TABLE IF NOT EXISTS attempts (
    id BIGSERIAL PRIMARY KEY,
    test_id BIGINT NOT NULL REFERENCES tests(id) ON DELETE CASCADE,
    status TEXT NOT NULL DEFAULT 'in_progress' CHECK (status IN ('in_progress', 'submitted')),
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    submitted_at TIMESTAMPTZ,
    correct_count INTEGER,
    total_questions INTEGER,
    score_percent NUMERIC(5, 2),
    ai_recommendation TEXT,
    practice_mode BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE TABLE IF NOT EXISTS answers (
    id BIGSERIAL PRIMARY KEY,
    attempt_id BIGINT NOT NULL REFERENCES attempts(id) ON DELETE CASCADE,
    question_id BIGINT NOT NULL REFERENCES questions(id) ON DELETE CASCADE,
    selected_answer TEXT,
    is_correct BOOLEAN,
    ai_feedback JSONB,
    answered_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (attempt_id, question_id)
);

CREATE TABLE IF NOT EXISTS mistake_journal (
    id BIGSERIAL PRIMARY KEY,
    attempt_id BIGINT NOT NULL REFERENCES attempts(id) ON DELETE CASCADE,
    question_id BIGINT NOT NULL REFERENCES questions(id) ON DELETE CASCADE,
    topic TEXT NOT NULL,
    user_answer TEXT,
    correct_answer TEXT NOT NULL,
    concept_to_learn TEXT,
    review_status TEXT NOT NULL DEFAULT 'open' CHECK (review_status IN ('open', 'reviewed')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (attempt_id, question_id)
);

CREATE TABLE IF NOT EXISTS progress (
    id BIGSERIAL PRIMARY KEY,
    attempt_id BIGINT REFERENCES attempts(id) ON DELETE SET NULL,
    tests_taken INTEGER NOT NULL,
    avg_score NUMERIC(5, 2) NOT NULL,
    weak_topics JSONB NOT NULL DEFAULT '[]'::jsonb,
    accuracy_by_topic JSONB NOT NULL DEFAULT '{}'::jsonb,
    frequent_mistakes JSONB NOT NULL DEFAULT '{}'::jsonb,
    trend_summary TEXT,
    recommended_next_practice TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
