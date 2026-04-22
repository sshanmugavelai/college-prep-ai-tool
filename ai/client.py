from __future__ import annotations

import json
import math
import re
from typing import Any

from anthropic import Anthropic

from ai.prompts import (
    MISTAKE_EXPLANATION_PROMPT,
    QUESTION_GENERATION_MIDDLE_SCHOOL_PROMPT,
    QUESTION_GENERATION_PROMPT,
    REVIEW_HINTS_PROMPT,
    STUDY_PLAN_PROMPT,
)
from utils.config import get_anthropic_api_key, get_anthropic_model

# Reading items embed a passage per question → much larger JSON than Math; output is capped (~8k tokens).
_READING_LARGE_SET = """
## Important (Reading, many questions)
Each "question" field must stay short: passage at most ~120 words, choices at most ~30 words each,
explanations at most 3 brief sentences. If you write long passages, the JSON response will be
truncated and invalid. Prefer one short paragraph per item.
"""


class ClaudeClient:
    def __init__(self) -> None:
        key = get_anthropic_api_key()
        if not key:
            raise RuntimeError(
                "ANTHROPIC_API_KEY is not set. For local development add it to a .env file; "
                "on Streamlit Community Cloud add ANTHROPIC_API_KEY under App settings → Secrets."
            )
        self.client = Anthropic(api_key=key)

    def _call_json(self, prompt: str, *, max_tokens: int = 4000) -> dict[str, Any]:
        response = self.client.messages.create(
            model=get_anthropic_model(),
            max_tokens=max_tokens,
            temperature=0.3,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = response.content[0].text.strip()
        return _parse_json_response(raw)

    def generate_questions(
        self,
        exam_type: str,
        section: str,
        num_questions: int,
        difficulty: str,
        learner_level: str = "sat",
        focus_keywords: str = "",
        starr_mode: bool = False,
        custom_instructions: str = "",
    ) -> dict[str, Any]:
        focus_note = (
            focus_keywords.strip()
            if focus_keywords.strip()
            else "No specific topics provided. Pick a reasonable mix for the selected section."
        )
        if custom_instructions.strip():
            focus_note = f"{focus_note}. Extra instructions: {custom_instructions.strip()}"
        curriculum_note = (
            "Use the Texas STAAR style and standards as the curriculum anchor for this set."
            if starr_mode
            else "Use a general U.S. school curriculum style."
        )
        section_lower = section.strip().lower()
        batch_size = _question_batch_size(section=section_lower, learner_level=learner_level)
        all_questions: list[dict[str, Any]] = []
        remaining = num_questions
        batch_idx = 1
        stalled_iterations = 0

        while remaining > 0:
            this_batch = min(batch_size, remaining)
            questions = self._generate_questions_batch(
                learner_level=learner_level,
                exam_type=exam_type,
                section=section,
                section_lower=section_lower,
                requested_count=this_batch,
                difficulty=difficulty,
                focus_note=focus_note,
                curriculum_note=curriculum_note,
                batch_idx=batch_idx,
                total_target=num_questions,
            )

            valid_questions = _extract_valid_questions(questions, fallback_difficulty=difficulty)
            if not valid_questions:
                stalled_iterations += 1
                if stalled_iterations >= 3:
                    raise ValueError(
                        "Question generation stalled after repeated retries. "
                        "Try again, or reduce question count for this run."
                    )
                # Make next iteration lighter.
                batch_size = max(1, batch_size // 2)
                continue

            stalled_iterations = 0
            take_n = min(remaining, len(valid_questions))
            all_questions.extend(valid_questions[:take_n])
            remaining -= take_n
            batch_idx += 1

        return {"questions": all_questions}

    def _generate_questions_batch(
        self,
        *,
        learner_level: str,
        exam_type: str,
        section: str,
        section_lower: str,
        requested_count: int,
        difficulty: str,
        focus_note: str,
        curriculum_note: str,
        batch_idx: int,
        total_target: int,
    ) -> list[dict[str, Any]]:
        current_count = requested_count
        while current_count >= 1:
            prompt = _build_question_prompt(
                learner_level=learner_level,
                exam_type=exam_type,
                section=section,
                num_questions=current_count,
                difficulty=difficulty,
                focus_note=focus_note,
                curriculum_note=curriculum_note,
            )
            if section_lower == "reading":
                prompt = f"{prompt}\n{_READING_LARGE_SET}"

            prompt = (
                f"{prompt}\n\n"
                f"Batch instruction: generate batch {batch_idx} for a total target of {total_target}. "
                f"Return exactly {current_count} questions and keep each question concise."
            )

            try:
                payload = self._call_json_with_retry(
                    prompt=prompt,
                    max_tokens=_generation_max_tokens(section_lower),
                    attempts=3,
                )
            except ValueError:
                if current_count == 1:
                    return []
                current_count = max(1, current_count // 2)
                continue

            questions = payload.get("questions")
            if isinstance(questions, list) and questions:
                return questions[:current_count]

            if current_count == 1:
                return []
            current_count = max(1, current_count // 2)

        return []

    def _call_json_with_retry(self, prompt: str, *, max_tokens: int, attempts: int = 2) -> dict[str, Any]:
        last_exc: Exception | None = None
        for i in range(attempts):
            try:
                return self._call_json(prompt, max_tokens=max_tokens)
            except ValueError as exc:
                last_exc = exc
                if i == attempts - 1:
                    break
                prompt = (
                    f"{prompt}\n\n"
                    "Critical retry rule: return ONLY one valid JSON object with no markdown fences, "
                    "no prose, no trailing comments, and no truncation."
                )
        if last_exc:
            raise last_exc
        raise ValueError("Claude JSON call failed unexpectedly.")

    def explain_mistake(
        self,
        exam_type: str,
        section: str,
        question: str,
        choices: list[str],
        correct_answer: str,
        user_answer: str,
        topic: str,
        difficulty: str,
    ) -> dict[str, Any]:
        prompt = MISTAKE_EXPLANATION_PROMPT.format(
            exam_type=exam_type,
            section=section,
            question=question,
            choices=choices,
            correct_answer=correct_answer,
            user_answer=user_answer,
            topic=topic,
            difficulty=difficulty,
        )
        return self._call_json(prompt)

    def generate_study_plan(self, performance_summary: str) -> dict[str, Any]:
        prompt = STUDY_PLAN_PROMPT.format(performance_summary=performance_summary)
        return self._call_json(prompt)

    def generate_review_hints(
        self,
        exam_type: str,
        section: str,
        question: str,
        choices: list[str],
        correct_answer: str,
        user_answer: str,
        topic: str,
        difficulty: str,
    ) -> dict[str, Any]:
        labels = ["A", "B", "C", "D"]
        lines = [f"{labels[i]}. {choices[i]}" for i in range(min(4, len(choices)))]
        choices_lines = "\n".join(lines)
        prompt = REVIEW_HINTS_PROMPT.format(
            exam_type=exam_type,
            section=section,
            topic=topic,
            difficulty=difficulty,
            question=question,
            choices_lines=choices_lines,
            user_answer=user_answer or "No answer",
            correct_answer=correct_answer,
        )
        return self._call_json(prompt)


def _strip_markdown_fence(text: str) -> str:
    text = text.strip()
    if not text.startswith("```"):
        return text
    text = re.sub(r"^```(?:json)?\s*", "", text, count=1, flags=re.IGNORECASE)
    text = re.sub(r"\s*```\s*$", "", text, count=1)
    return text.strip()


def _relax_trailing_commas(json_blob: str) -> str:
    """Allow occasional trailing commas before } or ] (invalid JSON but common in LLM output)."""
    return re.sub(r",(\s*[}\]])", r"\1", json_blob)


def _parse_json_response(raw: str) -> dict[str, Any]:
    text = _strip_markdown_fence(raw)

    def _try_load(s: str) -> dict[str, Any] | None:
        for variant in (s, _relax_trailing_commas(s)):
            try:
                out = json.loads(variant)
                if isinstance(out, dict):
                    return out
            except json.JSONDecodeError:
                continue
        return None

    parsed = _try_load(text)
    if parsed is not None:
        return parsed

    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("Claude response does not contain a JSON object.")

    parsed = _try_load(text[start : end + 1])
    if parsed is not None:
        return parsed

    raise ValueError(
        "Claude returned JSON that failed to parse (often truncated output — try fewer questions "
        "or a shorter section, then retry)."
    )


def _question_batch_size(section: str, learner_level: str) -> int:
    if section == "reading":
        return 5
    if learner_level == "middle_school":
        return 10
    return 12


def _build_question_prompt(
    *,
    learner_level: str,
    exam_type: str,
    section: str,
    num_questions: int,
    difficulty: str,
    focus_note: str,
    curriculum_note: str,
) -> str:
    if learner_level == "middle_school":
        return QUESTION_GENERATION_MIDDLE_SCHOOL_PROMPT.format(
            section=section,
            num_questions=num_questions,
            difficulty=difficulty,
            focus_note=focus_note,
            curriculum_note=curriculum_note,
        )
    return QUESTION_GENERATION_PROMPT.format(
        exam_type=exam_type,
        section=section,
        num_questions=num_questions,
        difficulty=difficulty,
        focus_note=focus_note,
        curriculum_note=curriculum_note,
    )


def _generation_max_tokens(section: str) -> int:
    if section == "reading":
        return 4500
    return 3200


def _extract_valid_questions(
    raw_questions: list[Any],
    *,
    fallback_difficulty: str,
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for item in raw_questions:
        if not isinstance(item, dict):
            continue
        choices = item.get("choices")
        if not isinstance(choices, list) or len(choices) != 4:
            continue
        correct = item.get("correct_answer")
        if correct not in {"A", "B", "C", "D"}:
            continue
        question_text = item.get("question")
        explanation = item.get("explanation")
        topic = item.get("topic")
        if not all(isinstance(v, str) and v.strip() for v in [question_text, explanation, topic]):
            continue
        normalized = {
            "question": question_text.strip(),
            "choices": [str(c).strip() for c in choices],
            "correct_answer": correct,
            "explanation": explanation.strip(),
            "topic": topic.strip(),
            "difficulty": str(item.get("difficulty", fallback_difficulty)).strip() or fallback_difficulty,
        }
        out.append(normalized)
    return out
