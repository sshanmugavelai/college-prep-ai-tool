from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ExternalIdentity:
    """Normalized identity returned by external auth providers."""

    provider: str
    subject: str
    email: str
    display_name: str

