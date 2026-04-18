from __future__ import annotations

from dataclasses import dataclass
from statistics import mean
from typing import Any

from psycopg.rows import dict_row
from psycopg.types.json import Json

from db.connection import get_conn


@dataclass
class DashboardStats:
    total_tests_taken: int
    average_score: float
    weak_topics: list[str]
    recommended_next_practice: str


def create_test_with_questions(
    exam_type: str,
    section: str,
    num_questions: int,
    difficulty: str,
    timed: bool,
    time_limit_minutes: int | None,
    questions: list[dict[str, Any]],
    source: str = "ai",
) -> int:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO tests (exam_type, section, num_questions, difficulty, timed, time_limit_minutes, source)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING id
                """,
                (exam_type, section, num_questions, difficulty, timed, time_limit_minutes, source),
            )
            test_id = cur.fetchone()[0]

            for idx, question in enumerate(questions, start=1):
                cur.execute(
                    """
                    INSERT INTO questions (
                        test_id, question_order, question_text, choices, correct_answer, explanation, topic, difficulty
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        test_id,
                        idx,
                        question["question"],
                        Json(question["choices"]),
                        question["correct_answer"],
                        question["explanation"],
                        question["topic"],
                        question.get("difficulty", difficulty),
                    ),
                )
        conn.commit()
        return test_id


def list_tests(limit: int = 100) -> list[dict[str, Any]]:
    with get_conn() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                SELECT
                    t.*,
                    COUNT(a.id) FILTER (WHERE a.status = 'submitted') AS submitted_attempts
                FROM tests t
                LEFT JOIN attempts a ON a.test_id = t.id
                GROUP BY t.id
                ORDER BY t.created_at DESC
                LIMIT %s
                """,
                (limit,),
            )
            return cur.fetchall()


def get_test(test_id: int) -> dict[str, Any] | None:
    with get_conn() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute("SELECT * FROM tests WHERE id = %s", (test_id,))
            return cur.fetchone()


def get_test_questions(test_id: int) -> list[dict[str, Any]]:
    with get_conn() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                SELECT
                    id AS question_id,
                    question_order,
                    question_text,
                    choices,
                    correct_answer,
                    explanation,
                    topic,
                    difficulty
                FROM questions
                WHERE test_id = %s
                ORDER BY question_order
                """,
                (test_id,),
            )
            return cur.fetchall()


def get_test_with_questions(test_id: int) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
    with get_conn() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute("SELECT * FROM tests WHERE id = %s", (test_id,))
            test_row = cur.fetchone()
            if not test_row:
                return None, []
            cur.execute(
                """
                SELECT
                    id AS question_id,
                    question_order,
                    question_text,
                    choices,
                    correct_answer,
                    explanation,
                    topic,
                    difficulty
                FROM questions
                WHERE test_id = %s
                ORDER BY question_order
                """,
                (test_id,),
            )
            questions = cur.fetchall()
            return test_row, questions


def create_attempt(test_id: int) -> int:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO attempts (test_id, status)
                VALUES (%s, 'in_progress')
                RETURNING id
                """,
                (test_id,),
            )
            attempt_id = cur.fetchone()[0]
        conn.commit()
        return attempt_id


def list_in_progress_attempts(limit: int = 100) -> list[dict[str, Any]]:
    with get_conn() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                SELECT
                    a.id,
                    a.started_at,
                    t.exam_type,
                    t.section,
                    t.difficulty,
                    t.timed,
                    t.time_limit_minutes
                FROM attempts a
                JOIN tests t ON t.id = a.test_id
                WHERE a.status = 'in_progress'
                ORDER BY a.started_at DESC
                LIMIT %s
                """,
                (limit,),
            )
            return cur.fetchall()


def get_attempt(attempt_id: int) -> dict[str, Any] | None:
    with get_conn() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                SELECT
                    a.*,
                    t.exam_type,
                    t.section,
                    t.difficulty,
                    t.timed,
                    t.time_limit_minutes
                FROM attempts a
                JOIN tests t ON t.id = a.test_id
                WHERE a.id = %s
                """,
                (attempt_id,),
            )
            return cur.fetchone()


def get_attempt_questions(attempt_id: int) -> list[dict[str, Any]]:
    with get_conn() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                SELECT
                    q.id AS question_id,
                    q.question_order,
                    q.question_text,
                    q.choices,
                    q.correct_answer,
                    q.explanation,
                    q.topic,
                    q.difficulty,
                    ans.id AS answer_id,
                    ans.selected_answer,
                    ans.is_correct,
                    ans.ai_feedback
                FROM attempts a
                JOIN questions q ON q.test_id = a.test_id
                LEFT JOIN answers ans ON ans.attempt_id = a.id AND ans.question_id = q.id
                WHERE a.id = %s
                ORDER BY q.question_order
                """,
                (attempt_id,),
            )
            return cur.fetchall()


def save_answer(attempt_id: int, question_id: int, selected_answer: str) -> None:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO answers (attempt_id, question_id, selected_answer)
                VALUES (%s, %s, %s)
                ON CONFLICT (attempt_id, question_id)
                DO UPDATE SET selected_answer = EXCLUDED.selected_answer, answered_at = NOW()
                """,
                (attempt_id, question_id, selected_answer),
            )
        conn.commit()


def submit_attempt(attempt_id: int) -> dict[str, Any]:
    with get_conn() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute("SELECT test_id FROM attempts WHERE id = %s", (attempt_id,))
            row = cur.fetchone()
            if not row:
                raise ValueError(f"Attempt {attempt_id} not found.")
            test_id = row["test_id"]

            cur.execute(
                """
                INSERT INTO answers (attempt_id, question_id, selected_answer, is_correct)
                SELECT %s, q.id, NULL, FALSE
                FROM questions q
                LEFT JOIN answers a ON a.attempt_id = %s AND a.question_id = q.id
                WHERE q.test_id = %s AND a.id IS NULL
                """,
                (attempt_id, attempt_id, test_id),
            )

            cur.execute(
                """
                UPDATE answers a
                SET is_correct = COALESCE(a.selected_answer = q.correct_answer, FALSE)
                FROM questions q
                WHERE a.attempt_id = %s AND q.id = a.question_id
                """,
                (attempt_id,),
            )

            cur.execute(
                """
                SELECT
                    COUNT(*)::int AS total_questions,
                    COUNT(*) FILTER (WHERE a.is_correct = TRUE)::int AS correct_count
                FROM answers a
                WHERE a.attempt_id = %s
                """,
                (attempt_id,),
            )
            score_row = cur.fetchone()
            total_questions = score_row["total_questions"]
            correct_count = score_row["correct_count"]
            score_percent = (correct_count / total_questions * 100.0) if total_questions else 0.0

            cur.execute(
                """
                UPDATE attempts
                SET
                    status = 'submitted',
                    submitted_at = NOW(),
                    correct_count = %s,
                    total_questions = %s,
                    score_percent = %s
                WHERE id = %s
                """,
                (correct_count, total_questions, round(score_percent, 2), attempt_id),
            )

            cur.execute(
                """
                INSERT INTO mistake_journal (
                    attempt_id, question_id, topic, user_answer, correct_answer, concept_to_learn
                )
                SELECT
                    a.attempt_id,
                    q.id,
                    q.topic,
                    a.selected_answer,
                    q.correct_answer,
                    COALESCE(a.ai_feedback->>'concept_to_learn', '')
                FROM answers a
                JOIN questions q ON q.id = a.question_id
                WHERE a.attempt_id = %s AND COALESCE(a.is_correct, FALSE) = FALSE
                ON CONFLICT (attempt_id, question_id) DO NOTHING
                """,
                (attempt_id,),
            )

            cur.execute(
                """
                UPDATE mistake_journal mj
                SET review_status = 'reviewed'
                FROM answers a
                WHERE a.attempt_id = %s
                  AND a.question_id = mj.question_id
                  AND a.is_correct = TRUE
                  AND mj.review_status = 'open'
                """,
                (attempt_id,),
            )

            _insert_progress_snapshot(cur, attempt_id=attempt_id)

        conn.commit()

    return get_attempt(attempt_id) or {}


def update_ai_feedback(attempt_id: int, question_id: int, feedback: dict[str, Any]) -> None:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE answers
                SET ai_feedback = %s
                WHERE attempt_id = %s AND question_id = %s
                """,
                (Json(feedback), attempt_id, question_id),
            )
            cur.execute(
                """
                UPDATE mistake_journal
                SET concept_to_learn = %s
                WHERE attempt_id = %s AND question_id = %s
                """,
                (feedback.get("concept_to_learn", ""), attempt_id, question_id),
            )
        conn.commit()


def get_review_attempts(limit: int = 100) -> list[dict[str, Any]]:
    with get_conn() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                SELECT
                    a.id,
                    a.status,
                    a.correct_count,
                    a.total_questions,
                    a.score_percent,
                    a.started_at,
                    a.submitted_at,
                    t.exam_type,
                    t.section,
                    t.difficulty
                FROM attempts a
                JOIN tests t ON t.id = a.test_id
                ORDER BY a.started_at DESC
                LIMIT %s
                """,
                (limit,),
            )
            return cur.fetchall()


def get_dashboard_stats() -> DashboardStats:
    with get_conn() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                SELECT
                    COUNT(*)::int AS total_tests_taken,
                    COALESCE(AVG(score_percent), 0)::float8 AS average_score
                FROM attempts
                WHERE status = 'submitted'
                """
            )
            basic = cur.fetchone()

            cur.execute(
                """
                SELECT
                    q.topic,
                    AVG(CASE WHEN a.is_correct THEN 1.0 ELSE 0.0 END) AS accuracy
                FROM answers a
                JOIN attempts att ON att.id = a.attempt_id AND att.status = 'submitted'
                JOIN questions q ON q.id = a.question_id
                GROUP BY q.topic
                ORDER BY accuracy ASC
                LIMIT 5
                """
            )
            weak = [r["topic"] for r in cur.fetchall()]

            cur.execute(
                """
                SELECT recommended_next_practice
                FROM progress
                ORDER BY created_at DESC
                LIMIT 1
                """
            )
            rec = cur.fetchone()
            recommendation = (
                rec["recommended_next_practice"]
                if rec and rec["recommended_next_practice"]
                else "Start with 10 medium questions in your weakest topic."
            )

    return DashboardStats(
        total_tests_taken=basic["total_tests_taken"],
        average_score=basic["average_score"],
        weak_topics=weak,
        recommended_next_practice=recommendation,
    )


def get_recent_activity(limit: int = 10) -> list[dict[str, Any]]:
    with get_conn() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                SELECT
                    a.id AS attempt_id,
                    t.exam_type,
                    t.section,
                    t.difficulty,
                    a.score_percent,
                    a.status,
                    COALESCE(a.submitted_at, a.started_at) AS activity_time
                FROM attempts a
                JOIN tests t ON t.id = a.test_id
                ORDER BY activity_time DESC
                LIMIT %s
                """,
                (limit,),
            )
            return cur.fetchall()


def list_mistakes(
    exam_type: str | None = None,
    section: str | None = None,
    topic: str | None = None,
    only_open: bool = True,
) -> list[dict[str, Any]]:
    query = """
        SELECT
            mj.id,
            mj.attempt_id,
            mj.question_id,
            mj.topic,
            mj.user_answer,
            mj.correct_answer,
            mj.concept_to_learn,
            mj.review_status,
            mj.created_at,
            t.exam_type,
            t.section,
            q.question_text,
            q.choices,
            q.explanation
        FROM mistake_journal mj
        JOIN attempts a ON a.id = mj.attempt_id
        JOIN tests t ON t.id = a.test_id
        JOIN questions q ON q.id = mj.question_id
        WHERE 1=1
    """
    params: list[Any] = []

    if exam_type:
        query += " AND t.exam_type = %s"
        params.append(exam_type)
    if section:
        query += " AND t.section = %s"
        params.append(section)
    if topic:
        query += " AND mj.topic = %s"
        params.append(topic)
    if only_open:
        query += " AND mj.review_status = 'open'"

    query += " ORDER BY mj.created_at DESC"

    with get_conn() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(query, tuple(params))
            return cur.fetchall()


def create_retry_test_from_mistakes(
    exam_type: str,
    section: str,
    topic: str | None = None,
    max_questions: int = 10,
) -> int | None:
    mistakes = list_mistakes(exam_type=exam_type, section=section, topic=topic, only_open=True)
    unique_by_question: dict[int, dict[str, Any]] = {}
    for m in mistakes:
        qid = m["question_id"]
        if qid not in unique_by_question:
            unique_by_question[qid] = m
        if len(unique_by_question) >= max_questions:
            break

    selected = list(unique_by_question.values())
    if not selected:
        return None

    questions_payload = []
    for item in selected:
        questions_payload.append(
            {
                "question": item["question_text"],
                "choices": item["choices"],
                "correct_answer": item["correct_answer"],
                "explanation": item["explanation"],
                "topic": item["topic"],
                "difficulty": "medium",
            }
        )

    return create_test_with_questions(
        exam_type=exam_type,
        section=section,
        num_questions=len(questions_payload),
        difficulty="medium",
        timed=False,
        time_limit_minutes=None,
        questions=questions_payload,
        source="mistake_retry",
    )


def get_progress_over_time() -> list[dict[str, Any]]:
    with get_conn() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                SELECT
                    id AS attempt_id,
                    submitted_at,
                    score_percent
                FROM attempts
                WHERE status = 'submitted'
                ORDER BY submitted_at
                """
            )
            return cur.fetchall()


def get_accuracy_by_topic() -> list[dict[str, Any]]:
    with get_conn() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                SELECT
                    q.topic,
                    COUNT(*)::int AS total,
                    SUM(CASE WHEN a.is_correct THEN 1 ELSE 0 END)::int AS correct,
                    ROUND(AVG(CASE WHEN a.is_correct THEN 1.0 ELSE 0.0 END) * 100.0, 2) AS accuracy_pct
                FROM answers a
                JOIN attempts att ON att.id = a.attempt_id AND att.status = 'submitted'
                JOIN questions q ON q.id = a.question_id
                GROUP BY q.topic
                ORDER BY accuracy_pct ASC, total DESC
                """
            )
            return cur.fetchall()


def get_latest_progress_snapshot() -> dict[str, Any] | None:
    with get_conn() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute("SELECT * FROM progress ORDER BY created_at DESC LIMIT 1")
            return cur.fetchone()


def build_performance_summary_text() -> str:
    stats = get_dashboard_stats()
    accuracy_rows = get_accuracy_by_topic()
    recent = get_recent_activity(limit=5)

    lines = [
        f"Total submitted tests: {stats.total_tests_taken}",
        f"Average score: {stats.average_score:.2f}%",
        f"Weak topics: {', '.join(stats.weak_topics) if stats.weak_topics else 'none yet'}",
        "Recent activity:",
    ]
    for row in recent:
        lines.append(
            f"- {row['exam_type']} {row['section']} ({row['difficulty']}): "
            f"{row['score_percent'] if row['score_percent'] is not None else 'n/a'}%"
        )
    lines.append("Accuracy by topic:")
    for row in accuracy_rows:
        lines.append(f"- {row['topic']}: {row['accuracy_pct']}% ({row['correct']}/{row['total']})")
    return "\n".join(lines)


def save_recommended_next_practice(recommendation: str) -> None:
    with get_conn() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute("SELECT id FROM progress ORDER BY created_at DESC LIMIT 1")
            latest = cur.fetchone()
            if latest:
                cur.execute(
                    """
                    UPDATE progress
                    SET recommended_next_practice = %s, created_at = NOW()
                    WHERE id = %s
                    """,
                    (recommendation, latest["id"]),
                )
            else:
                cur.execute(
                    """
                    INSERT INTO progress (
                        attempt_id,
                        tests_taken,
                        avg_score,
                        weak_topics,
                        accuracy_by_topic,
                        frequent_mistakes,
                        trend_summary,
                        recommended_next_practice
                    )
                    VALUES (NULL, 0, 0, '[]'::jsonb, '{}'::jsonb, '{}'::jsonb, %s, %s)
                    """,
                    ("Not enough data for a trend yet.", recommendation),
                )
        conn.commit()


def _insert_progress_snapshot(cur: Any, attempt_id: int) -> None:
    cur.execute(
        """
        SELECT
            COUNT(*)::int AS tests_taken,
            COALESCE(AVG(score_percent), 0)::float8 AS avg_score
        FROM attempts
        WHERE status = 'submitted'
        """
    )
    base = cur.fetchone()

    cur.execute(
        """
        SELECT
            q.topic,
            COUNT(*)::int AS total,
            SUM(CASE WHEN a.is_correct THEN 1 ELSE 0 END)::int AS correct
        FROM answers a
        JOIN attempts att ON att.id = a.attempt_id AND att.status = 'submitted'
        JOIN questions q ON q.id = a.question_id
        GROUP BY q.topic
        """
    )
    topic_rows = cur.fetchall()

    accuracy_by_topic: dict[str, float] = {}
    weak_topics: list[str] = []
    if topic_rows:
        topic_scores = []
        for r in topic_rows:
            accuracy = (r["correct"] / r["total"] * 100.0) if r["total"] else 0.0
            accuracy_by_topic[r["topic"]] = round(accuracy, 2)
            topic_scores.append((r["topic"], accuracy))
        weak_topics = [topic for topic, _ in sorted(topic_scores, key=lambda x: x[1])[:3]]

    cur.execute(
        """
        SELECT topic, COUNT(*)::int AS count
        FROM mistake_journal
        WHERE review_status = 'open'
        GROUP BY topic
        ORDER BY count DESC
        LIMIT 5
        """
    )
    mistakes_rows = cur.fetchall()
    frequent_mistakes = {row["topic"]: row["count"] for row in mistakes_rows}

    cur.execute(
        """
        SELECT score_percent
        FROM attempts
        WHERE status = 'submitted'
        ORDER BY submitted_at DESC
        LIMIT 6
        """
    )
    recent_scores = [float(r["score_percent"]) for r in cur.fetchall() if r["score_percent"] is not None]
    trend_summary = _build_trend_summary(recent_scores)
    recommendation = _build_recommendation(weak_topics, frequent_mistakes)

    cur.execute(
        """
        INSERT INTO progress (
            attempt_id,
            tests_taken,
            avg_score,
            weak_topics,
            accuracy_by_topic,
            frequent_mistakes,
            trend_summary,
            recommended_next_practice
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (
            attempt_id,
            base["tests_taken"],
            round(base["avg_score"], 2),
            Json(weak_topics),
            Json(accuracy_by_topic),
            Json(frequent_mistakes),
            trend_summary,
            recommendation,
        ),
    )


def _build_trend_summary(scores_desc: list[float]) -> str:
    if len(scores_desc) < 2:
        return "Not enough data for a trend yet."
    latest_window = scores_desc[:3]
    previous_window = scores_desc[3:6]
    latest_avg = mean(latest_window)
    if not previous_window:
        return f"Recent average is {latest_avg:.1f}%."

    prev_avg = mean(previous_window)
    delta = latest_avg - prev_avg
    if delta > 2:
        return f"Improving trend: recent average is up by {delta:.1f} points."
    if delta < -2:
        return f"Needs attention: recent average is down by {abs(delta):.1f} points."
    return "Stable trend over recent attempts."


def _build_recommendation(weak_topics: list[str], frequent_mistakes: dict[str, int]) -> str:
    if weak_topics:
        topic = weak_topics[0]
        return f"Practice 15 medium {topic} questions, then 10 mixed review questions."

    if frequent_mistakes:
        topic = max(frequent_mistakes, key=frequent_mistakes.get)
        return f"Review core rules for {topic}, then do a short 10-question timed set."

    return "Take one medium mixed test and review every explanation carefully."
