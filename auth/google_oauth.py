from __future__ import annotations

import secrets
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

    def create_state(self) -> str:
        return secrets.token_urlsafe(24)

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
        if not state or state != expected_state:
            raise ValueError("OAuth state mismatch. Please retry sign-in.")

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
