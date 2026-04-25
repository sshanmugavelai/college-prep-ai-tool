from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
import time
from dataclasses import dataclass
from typing import Any, Optional
from urllib.parse import urlencode

from auth.contracts import ExternalIdentity
from utils.config import (
    get_google_oauth_authorize_url,
    get_google_oauth_client_id,
    get_google_oauth_client_secret,
    get_google_oauth_redirect_uri,
    get_google_oauth_token_url,
    get_google_oauth_userinfo_url,
)


@dataclass(frozen=True)
class GoogleOAuthConfig:
    client_id: str
    client_secret: str
    redirect_uri: str
    authorize_url: str
    token_url: str
    userinfo_url: str


class GoogleOAuthService:
    """External provider service: Google OAuth protocol and identity mapping."""

    _STATE_TTL_SECONDS = 600

    def __init__(self, *, config: Optional[GoogleOAuthConfig] = None) -> None:
        self.config = config or GoogleOAuthConfig(
            client_id=get_google_oauth_client_id(),
            client_secret=get_google_oauth_client_secret(),
            redirect_uri=get_google_oauth_redirect_uri(),
            authorize_url=get_google_oauth_authorize_url(),
            token_url=get_google_oauth_token_url(),
            userinfo_url=get_google_oauth_userinfo_url(),
        )

    def is_configured(self) -> bool:
        c = self.config
        return bool(
            c.client_id
            and c.client_secret
            and c.redirect_uri
            and c.authorize_url
            and c.token_url
            and c.userinfo_url
        )

    def create_state(self, *, learner_level: str = "sat") -> str:
        normalized_level = "middle_school" if learner_level == "middle_school" else "sat"
        nonce = secrets.token_urlsafe(24)
        issued_at = str(int(time.time()))
        payload = f"{issued_at}.{normalized_level}.{nonce}"
        signature = self._sign_state_payload(payload)
        return f"{payload}.{signature}"

    def build_authorize_url(self, state: str) -> str:
        query = urlencode(
            {
                "client_id": self.config.client_id,
                "redirect_uri": self.config.redirect_uri,
                "response_type": "code",
                "scope": "openid email profile",
                "state": state,
                "access_type": "online",
                "prompt": "select_account",
            }
        )
        return f"{self.config.authorize_url}?{query}"

    def exchange_code_for_identity(
        self,
        *,
        code: str,
        state: str,
        expected_state: str,
    ) -> ExternalIdentity:
        if not code:
            raise ValueError("Missing OAuth authorization code.")
        if not state:
            raise ValueError("Missing OAuth state. Please retry sign-in.")
        if expected_state and state != expected_state:
            raise ValueError("OAuth state mismatch. Please retry sign-in.")
        self._validate_state_token(state)

        token_data = self._fetch_token(code)
        access_token = str(token_data.get("access_token", "")).strip()
        if not access_token:
            raise ValueError("Google OAuth token response missing access_token.")

        profile = self._fetch_profile(access_token=access_token)
        sub = str(profile.get("sub", "")).strip()
        email = str(profile.get("email", "")).strip().lower()
        name = str(profile.get("name", "")).strip() or email.split("@")[0]
        if not sub or not email:
            raise ValueError("Google profile did not include required identity fields.")

        return ExternalIdentity(
            provider="google",
            subject=sub,
            email=email,
            display_name=name,
        )

    def _fetch_token(self, code: str) -> dict[str, Any]:
        try:
            import requests
        except Exception as exc:
            raise RuntimeError("requests package is required for Google OAuth.") from exc

        resp = requests.post(
            self.config.token_url,
            data={
                "code": code,
                "client_id": self.config.client_id,
                "client_secret": self.config.client_secret,
                "redirect_uri": self.config.redirect_uri,
                "grant_type": "authorization_code",
            },
            timeout=15,
        )
        if resp.status_code >= 400:
            raise ValueError(f"Google token exchange failed ({resp.status_code}).")
        payload = resp.json()
        if not isinstance(payload, dict):
            raise ValueError("Unexpected Google token response format.")
        return payload

    def _fetch_profile(self, *, access_token: str) -> dict[str, Any]:
        try:
            import requests
        except Exception as exc:
            raise RuntimeError("requests package is required for Google OAuth.") from exc

        resp = requests.get(
            self.config.userinfo_url,
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=15,
        )
        if resp.status_code >= 400:
            raise ValueError(f"Google profile fetch failed ({resp.status_code}).")
        payload = resp.json()
        if not isinstance(payload, dict):
            raise ValueError("Unexpected Google userinfo response format.")
        return payload

    def _sign_state_payload(self, payload: str) -> str:
        digest = hmac.new(
            self.config.client_secret.encode("utf-8"),
            payload.encode("utf-8"),
            hashlib.sha256,
        ).digest()
        return base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")

    def _validate_state_token(self, state: str) -> None:
        self.get_learner_level_from_state(state)

    def get_learner_level_from_state(self, state: str) -> str:
        try:
            issued_at, learner_level, nonce, signature = state.split(".", 3)
        except ValueError as exc:
            raise ValueError("OAuth state mismatch. Please retry sign-in.") from exc

        if not issued_at or not learner_level or not nonce or not signature:
            raise ValueError("OAuth state mismatch. Please retry sign-in.")
        if learner_level not in {"sat", "middle_school"}:
            raise ValueError("OAuth state mismatch. Please retry sign-in.")

        payload = f"{issued_at}.{learner_level}.{nonce}"
        expected_signature = self._sign_state_payload(payload)
        if not hmac.compare_digest(signature, expected_signature):
            raise ValueError("OAuth state mismatch. Please retry sign-in.")

        try:
            issued_at_ts = int(issued_at)
        except ValueError as exc:
            raise ValueError("OAuth state mismatch. Please retry sign-in.") from exc
        if time.time() - issued_at_ts > self._STATE_TTL_SECONDS:
            raise ValueError("OAuth sign-in expired. Please retry sign-in.")
        return learner_level
