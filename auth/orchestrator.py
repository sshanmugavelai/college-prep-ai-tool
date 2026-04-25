from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

import streamlit as st

from auth.google_oauth import GoogleOAuthService
from auth.local_credentials import LocalCredentialAuthService
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

    def __init__(
        self,
        *,
        oauth_service: Optional[GoogleOAuthService] = None,
        local_credential_service: Optional[LocalCredentialAuthService] = None,
    ) -> None:
        self.oauth_service = oauth_service or GoogleOAuthService()
        self.local_credential_service = local_credential_service or LocalCredentialAuthService()

    def provider_configured(self) -> bool:
        return self.oauth_service.is_configured()

    def start_google_sign_in(self, *, learner_level: str) -> str:
        state = self.oauth_service.create_state(learner_level=learner_level)
        st.session_state.oauth_state = state
        return self.oauth_service.build_authorize_url(state)

    def maybe_finish_google_sign_in(self, *, query_params: dict[str, Any]) -> Optional[AuthResult]:
        code = str(query_params.get("code", "")).strip()
        if not code:
            return None

        state = str(query_params.get("state", "")).strip()
        expected_state = str(st.session_state.get("oauth_state", "")).strip()
        learner_level = self.oauth_service.get_learner_level_from_state(state)
        identity = self.oauth_service.exchange_code_for_identity(
            code=code,
            state=state,
            expected_state=expected_state,
        )
        user_row = upsert_user_from_external_identity(identity, learner_level_hint=learner_level)
        policy = evaluate_user_policy(email=identity.email, username=str(user_row["username"]))
        return AuthResult(
            user_id=int(user_row["id"]),
            username=str(user_row["username"]),
            display_name=str(user_row["display_name"]),
            learner_level=str(user_row["learner_level"]),
            email=identity.email,
            is_admin=policy.is_admin,
        )

    def login_with_local_credentials(self, *, username: str, password: str) -> Optional[AuthResult]:
        row = self.local_credential_service.authenticate(username=username, password=password)
        if not row:
            return None
        uname = str(row["username"])
        synthetic_email = f"{uname}@local"
        policy = evaluate_user_policy(email=synthetic_email, username=uname)
        return AuthResult(
            user_id=int(row["id"]),
            username=uname,
            display_name=str(row["display_name"]),
            learner_level=str(row["learner_level"]),
            email=synthetic_email,
            is_admin=policy.is_admin,
        )
