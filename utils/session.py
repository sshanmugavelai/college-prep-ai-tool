import streamlit as st

# Bump this when auth or session keys change so Streamlit Cloud visitors are not stuck
# with a stale ``user_id`` from an old session (session_state survives reruns and deploys).
AUTH_SESSION_VERSION = 5


def is_logged_in() -> bool:
    """Require a positive integer user id (avoids truthy junk in session_state on Streamlit Cloud)."""
    uid = st.session_state.get("user_id")
    if uid is None:
        return False
    try:
        return int(uid) > 0
    except (TypeError, ValueError):
        return False


def ensure_auth_session_version() -> None:
    """Clear cached login if this deploy expects a different session shape."""
    key = "_auth_session_version"
    if st.session_state.get(key) == AUTH_SESSION_VERSION:
        return
    for k in (
        "user_id",
        "username",
        "display_name",
        "learner_level",
        "email",
        "is_admin",
        "oauth_state",
        "current_attempt_id",
    ):
        st.session_state.pop(k, None)
    st.session_state[key] = AUTH_SESSION_VERSION


def init_session_state() -> None:
    defaults = {
        "current_attempt_id": None,
        "question_index": 0,
        "attempt_started_at": None,
        "test_filters": {},
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def reset_attempt_state() -> None:
    st.session_state.current_attempt_id = None
    st.session_state.question_index = 0
    st.session_state.attempt_started_at = None


def clear_streamlit_caches() -> None:
    """Clear @st.cache_data / @st.cache_resource (safe no-op if unused)."""
    try:
        st.cache_data.clear()
    except Exception:
        pass
    try:
        st.cache_resource.clear()
    except Exception:
        pass


# Keys removed on log out / “reset session” (not Streamlit internals like widget state).
_SESSION_RESET_KEYS = (
    "user_id",
    "username",
    "display_name",
    "learner_level",
    "email",
    "is_admin",
    "oauth_state",
    "current_attempt_id",
    "question_index",
    "attempt_started_at",
    "workspace_step",
    "_pending_workspace_step",
    "test_filters",
)


def reset_user_session() -> None:
    """Drop login + workspace state so the username screen shows again."""
    clear_streamlit_caches()
    for k in _SESSION_RESET_KEYS:
        st.session_state.pop(k, None)


def set_authenticated_user_session(
    *,
    user_id: int,
    username: str,
    display_name: str,
    learner_level: str,
    email: str,
    is_admin: bool,
) -> None:
    st.session_state.user_id = int(user_id)
    st.session_state.username = username
    st.session_state.display_name = display_name
    st.session_state.learner_level = learner_level
    st.session_state.email = email
    st.session_state.is_admin = bool(is_admin)


def current_user_is_admin() -> bool:
    return bool(st.session_state.get("is_admin", False))
