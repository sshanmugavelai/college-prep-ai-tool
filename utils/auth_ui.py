"""Streamlit login and session helpers for per-learner accounts."""

import streamlit as st

from db.init_db import init_db
from db.users_repo import get_user_by_username
from utils.session import clear_streamlit_caches, reset_user_session


def render_login_page() -> None:
    st.title("College Prep AI")
    st.caption("Enter your learner username to continue.")

    username = st.text_input("Username", autocomplete="username")
    c1, c2 = st.columns(2)
    with c1:
        go = st.button("Continue", type="primary", use_container_width=True, key="login_continue")
    with c2:
        reset = st.button("Reset session & caches", use_container_width=True, key="login_reset")

    if go:
        row = get_user_by_username(username)
        if not row:
            st.error("Unknown username.")
            return
        st.session_state.user_id = int(row["id"])
        st.session_state.username = row["username"]
        st.session_state.display_name = row["display_name"]
        st.session_state.learner_level = row["learner_level"]
        st.rerun()

    if reset:
        reset_user_session()
        st.rerun()

    with st.expander("First-time setup"):
        if st.button("Initialize database & seed accounts"):
            try:
                init_db()
                st.success("Done — try your username again.")
            except Exception as exc:
                st.error(f"Setup failed: {exc}")


def require_user_id() -> int:
    uid = st.session_state.get("user_id")
    if uid is None:
        st.error("Please sign in from the Dashboard.")
        st.stop()
    return int(uid)


def account_sidebar(*, key_prefix: str = "acct") -> None:
    """Call inside ``with st.sidebar:``. Log out clears session + Streamlit caches."""
    st.subheader("Account")
    if st.button(
        "Log out",
        key=f"{key_prefix}_logout",
        type="primary",
        use_container_width=True,
    ):
        reset_user_session()
        st.rerun()
    if st.button(
        "Clear caches only",
        key=f"{key_prefix}_cache",
        help="Clears @st.cache_data / @st.cache_resource; stays signed in",
        use_container_width=True,
    ):
        clear_streamlit_caches()
        st.rerun()


def learner_badge() -> None:
    """Call inside ``with st.sidebar:``."""
    name = st.session_state.get("display_name", "")
    level = st.session_state.get("learner_level", "")
    label = "SAT / high school prep" if level == "sat" else "Grade-level practice (middle school)"
    st.caption(f"**{name}** · {label}")
