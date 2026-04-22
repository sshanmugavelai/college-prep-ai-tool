from __future__ import annotations

from typing import Any, Optional

from db.users_repo import authenticate_local_credentials


class LocalCredentialAuthService:
    """Credential service for explicit local admin fallback login."""

    def authenticate(self, *, username: str, password: str) -> Optional[dict[str, Any]]:
        return authenticate_local_credentials(username=username, password=password)
