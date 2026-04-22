from __future__ import annotations

from dataclasses import dataclass

from utils.config import get_admin_emails


@dataclass(frozen=True)
class UserPolicy:
    """Policy decisions for UI and operational gating."""

    is_admin: bool
    can_view_admin_tools: bool
    can_initialize_db: bool
    can_clear_cache: bool


def evaluate_user_policy(*, email: str) -> UserPolicy:
    normalized_email = (email or "").strip().lower()
    admins = get_admin_emails()
    is_admin = normalized_email in admins
    return UserPolicy(
        is_admin=is_admin,
        can_view_admin_tools=is_admin,
        can_initialize_db=is_admin,
        can_clear_cache=is_admin,
    )
