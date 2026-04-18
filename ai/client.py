import json
import os
from typing import Any

from anthropic import Anthropic
from dotenv import load_dotenv

from ai.prompts import (
    MISTAKE_EXPLANATION_PROMPT,
    QUESTION_GENERATION_PROMPT,
    STUDY_PLAN_PROMPT,
)


load_dotenv()

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-3-5-sonnet-latest")


class ClaudeClient:
    def __init__(self) -> None:
        if not ANTHROPIC_API_KEY:
            raise RuntimeError("ANTHROPIC_API_KEY is not set. Add it to your .env file.")
        self.client = Anthropic(api_key=ANTHROPIC_API_KEY)

    def _call_json(self, prompt: str) -> dict[str, Any]:
        response = self.client.messages.create(
            model=ANTHROPIC_MODEL,
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
