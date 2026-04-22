from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

import streamlit as st

from auth.google_oauth import GoogleOAuthService
from auth.policy import evaluate_user_policy
from db.users_repo import upsert_user_from_external_identity


@dataclass(frozen=True)
class AuthResult:
    user_id: int
    username: str
    display_name: str
    learner_level: str
    email: str
    is_admin: bool


class AuthOrchestrator:
    """Orchestrates auth flow between provider, persistence, and session lifecycle."""

    def __init__(self, *, oauth_service: Optional[GoogleOAuthService] = None) -> None:
        self.oauth_service = oauth_service or GoogleOAuthService()

    def provider_configured(self) -> bool:
        return self.oauth_service.is_configured()

    def start_google_sign_in(self) -> str:
        state = self.oauth_service.create_state()
        st.session_state.oauth_state = state
        return self.oauth_service.build_authorize_url(state)

    def maybe_finish_google_sign_in(self, *, query_params: dict[str, Any]) -> Optional[AuthResult]:
        code = str(query_params.get("code", "")).strip()
        if not code:
            return None

        state = str(query_params.get("state", "")).strip()
        expected_state = str(st.session_state.get("oauth_state", "")).strip()
        identity = self.oauth_service.exchange_code_for_identity(
            code=code,
            state=state,
            expected_state=expected_state,
        )
        user_row = upsert_user_from_external_identity(identity)
        policy = evaluate_user_policy(email=identity.email)
        return AuthResult(
            user_id=int(user_row["id"]),
            username=str(user_row["username"]),
            display_name=str(user_row["display_name"]),
            learner_level=str(user_row["learner_level"]),
            email=identity.email,
            is_admin=policy.is_admin,
        )
