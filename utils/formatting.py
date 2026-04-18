from __future__ import annotations

import json
from typing import Any


def format_choices_for_display(choices: list[str]) -> str:
    labels = ["A", "B", "C", "D"]
    parts = []
    for i, choice in enumerate(choices):
        label = labels[i] if i < len(labels) else str(i + 1)
        parts.append(f"{label}. {choice}")
    return " | ".join(parts)


def pretty_json(data: Any) -> str:
    return json.dumps(data, indent=2, ensure_ascii=True)
