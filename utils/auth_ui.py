"""Streamlit login and session helpers for per-learner accounts."""

import streamlit as st

from db.init_db import init_db
from db.users_repo import get_user_by_username


def render_login_page() -> None:
    st.title("College Prep AI")
    st.caption("Enter your learner username to continue.")

    username = st.text_input("Username", autocomplete="username")
    if st.button("Continue", type="primary"):
        row = get_user_by_username(username)
        if not row:
            st.error("Unknown username.")
            return
        st.session_state.user_id = int(row["id"])
        st.session_state.username = row["username"]
        st.session_state.display_name = row["display_name"]
        st.session_state.learner_level = row["learner_level"]
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


def logout_button() -> None:
    if st.sidebar.button("Sign out"):
        for k in ("user_id", "username", "display_name", "learner_level", "current_attempt_id"):
            st.session_state.pop(k, None)
        st.session_state.question_index = 0
        st.session_state.attempt_started_at = None
        st.rerun()


def learner_badge() -> None:
    name = st.session_state.get("display_name", "")
    level = st.session_state.get("learner_level", "")
    label = "SAT / high school prep" if level == "sat" else "Grade-level practice (middle school)"
    st.sidebar.caption(f"**{name}** · {label}")
