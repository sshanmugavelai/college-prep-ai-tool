import json
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
        if learner_level == "middle_school":
            prompt = QUESTION_GENERATION_MIDDLE_SCHOOL_PROMPT.format(
                section=section,
                num_questions=num_questions,
                difficulty=difficulty,
                focus_note=focus_note,
                curriculum_note=curriculum_note,
            )
        else:
            prompt = QUESTION_GENERATION_PROMPT.format(
                exam_type=exam_type,
                section=section,
                num_questions=num_questions,
                difficulty=difficulty,
                focus_note=focus_note,
                curriculum_note=curriculum_note,
            )
        if section.strip().lower() == "reading" and num_questions > 10:
            prompt = f"{prompt}\n{_READING_LARGE_SET}"
        # Large JSON payloads; 4000 output tokens often truncates mid-object (invalid JSON).
        return self._call_json(prompt, max_tokens=8192)

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
