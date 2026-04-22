"""Resolve secrets from the environment (local .env) or Streamlit Cloud secrets."""

import os
from pathlib import Path

from dotenv import load_dotenv

# Project-root .env (not cwd) so `streamlit run` from another directory still loads it.
# override=True: a stale DATABASE_URL exported in the shell must not shadow the real .env
# (common cause of "password failed" right after editing .env).
_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(_ROOT / ".env", override=True)


def _streamlit_secret(key: str) -> str:
    try:
        import streamlit as st

        if key not in st.secrets:
            return ""
        return str(st.secrets[key]).strip()
    except Exception:
        return ""


def get_database_url() -> str:
    url = (os.getenv("DATABASE_URL") or "").strip()
    if url:
        return url
    return _streamlit_secret("DATABASE_URL")


def get_anthropic_api_key() -> str:
    key = (os.getenv("ANTHROPIC_API_KEY") or "").strip()
    if key:
        return key
    return _streamlit_secret("ANTHROPIC_API_KEY")


def get_anthropic_model() -> str:
    model = (os.getenv("ANTHROPIC_MODEL") or "").strip()
    if model:
        return model
    return _streamlit_secret("ANTHROPIC_MODEL") or "claude-3-5-sonnet-latest"


def _read_csv_emails(key: str) -> set[str]:
    raw = (os.getenv(key) or _streamlit_secret(key) or "").strip()
    if not raw:
        return set()
    return {part.strip().lower() for part in raw.split(",") if part.strip()}


def get_admin_emails() -> set[str]:
    return _read_csv_emails("ADMIN_EMAILS")


def get_middle_school_emails() -> set[str]:
    return _read_csv_emails("MIDDLE_SCHOOL_EMAILS")


def get_google_oauth_client_id() -> str:
    return (os.getenv("GOOGLE_OAUTH_CLIENT_ID") or _streamlit_secret("GOOGLE_OAUTH_CLIENT_ID") or "").strip()


def get_google_oauth_client_secret() -> str:
    return (
        os.getenv("GOOGLE_OAUTH_CLIENT_SECRET") or _streamlit_secret("GOOGLE_OAUTH_CLIENT_SECRET") or ""
    ).strip()


def get_google_oauth_redirect_uri() -> str:
    return (
        os.getenv("GOOGLE_OAUTH_REDIRECT_URI") or _streamlit_secret("GOOGLE_OAUTH_REDIRECT_URI") or ""
    ).strip()


def get_google_oauth_authorize_url() -> str:
    return (
        os.getenv("GOOGLE_OAUTH_AUTHORIZE_URL")
        or _streamlit_secret("GOOGLE_OAUTH_AUTHORIZE_URL")
        or "https://accounts.google.com/o/oauth2/v2/auth"
    ).strip()


def get_google_oauth_token_url() -> str:
    return (
        os.getenv("GOOGLE_OAUTH_TOKEN_URL")
        or _streamlit_secret("GOOGLE_OAUTH_TOKEN_URL")
        or "https://oauth2.googleapis.com/token"
    ).strip()


def get_google_oauth_userinfo_url() -> str:
    return (
        os.getenv("GOOGLE_OAUTH_USERINFO_URL")
        or _streamlit_secret("GOOGLE_OAUTH_USERINFO_URL")
        or "https://openidconnect.googleapis.com/v1/userinfo"
    ).strip()


def get_paypal_donate_url() -> str:
    return (os.getenv("PAYPAL_DONATE_URL") or _streamlit_secret("PAYPAL_DONATE_URL") or "").strip()
