import json
from typing import Any

from anthropic import Anthropic

from ai.prompts import (
    MISTAKE_EXPLANATION_PROMPT,
    QUESTION_GENERATION_PROMPT,
    REVIEW_HINTS_PROMPT,
    STUDY_PLAN_PROMPT,
)
from utils.config import get_anthropic_api_key, get_anthropic_model


class ClaudeClient:
    def __init__(self) -> None:
        key = get_anthropic_api_key()
        if not key:
            raise RuntimeError(
                "ANTHROPIC_API_KEY is not set. For local development add it to a .env file; "
                "on Streamlit Community Cloud add ANTHROPIC_API_KEY under App settings → Secrets."
            )
        self.client = Anthropic(api_key=key)

    def _call_json(self, prompt: str) -> dict[str, Any]:
        response = self.client.messages.create(
            model=get_anthropic_model(),
            max_tokens=4000,
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
    ) -> dict[str, Any]:
        prompt = QUESTION_GENERATION_PROMPT.format(
            exam_type=exam_type,
            section=section,
            num_questions=num_questions,
            difficulty=difficulty,
        )
        return self._call_json(prompt)

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


def _parse_json_response(raw: str) -> dict[str, Any]:
    # Claude usually returns plain JSON, but this keeps the app resilient
    # when markdown fences are included.
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass

    cleaned = raw.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        if cleaned.startswith("json"):
            cleaned = cleaned[4:].strip()

    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("Claude response does not contain valid JSON object.")

    candidate = cleaned[start : end + 1]
    return json.loads(candidate)
