from __future__ import annotations

from typing import Any


def validate_questions_payload(payload: dict[str, Any], expected_count: int) -> list[dict[str, Any]]:
    if "questions" not in payload or not isinstance(payload["questions"], list):
        raise ValueError("AI response must include a questions list.")

    questions = payload["questions"]
    if len(questions) != expected_count:
        raise ValueError(
            f"AI returned {len(questions)} questions, expected {expected_count}. Try again."
        )

    for i, q in enumerate(questions, start=1):
        missing = [
            key
            for key in ["question", "choices", "correct_answer", "explanation", "topic", "difficulty"]
            if key not in q
        ]
        if missing:
            raise ValueError(f"Question {i} is missing keys: {', '.join(missing)}")
        if not isinstance(q["choices"], list) or len(q["choices"]) != 4:
            raise ValueError(f"Question {i} must include exactly 4 choices.")
        if q["correct_answer"] not in {"A", "B", "C", "D"}:
            raise ValueError(f"Question {i} has invalid correct_answer: {q['correct_answer']}")
    return questions
