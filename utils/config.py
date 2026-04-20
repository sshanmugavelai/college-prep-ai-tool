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
