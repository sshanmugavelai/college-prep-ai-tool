"""Streamlit auth UI and account panels."""

import streamlit as st

from auth.orchestrator import AuthOrchestrator
from auth.policy import evaluate_user_policy
from db.init_db import init_db
from utils.config import get_paypal_donate_url
from utils.session import reset_user_session, set_authenticated_user_session


def render_login_page() -> None:
    orchestrator = AuthOrchestrator()
    st.title("College Prep AI")
    st.caption("Sign in with Google (recommended). Local admin fallback is available.")

    query_params = st.query_params.to_dict()
    oauth_error = str(query_params.get("error", "")).strip()
    if oauth_error:
        st.error(f"Google sign-in failed: {oauth_error}")

    try:
        result = orchestrator.maybe_finish_google_sign_in(query_params=query_params)
    except Exception as exc:
        st.error(f"Sign-in failed: {exc}")
        result = None

    if result:
        set_authenticated_user_session(
            user_id=result.user_id,
            username=result.username,
            display_name=result.display_name,
            learner_level=result.learner_level,
            email=result.email,
            is_admin=result.is_admin,
        )
        # Remove provider callback params from URL so reruns are clean.
        st.query_params.clear()
        st.rerun()

    if orchestrator.provider_configured():
        auth_url = orchestrator.start_google_sign_in()
        st.link_button(
            "Continue with Google",
            url=auth_url,
            use_container_width=True,
            type="primary",
        )
    else:
        st.warning("Google OAuth is not configured. You can still use local admin login.")

    with st.expander("Admin fallback login"):
        admin_user = st.text_input("Admin username", value="admin", key="admin_login_user")
        admin_pass = st.text_input("Admin password", type="password", key="admin_login_pass")
        if st.button("Sign in as admin", key="admin_login_btn", use_container_width=True):
            admin_result = orchestrator.login_with_local_credentials(
                username=admin_user,
                password=admin_pass,
            )
            if not admin_result:
                st.error("Invalid admin credentials.")
            else:
                set_authenticated_user_session(
                    user_id=admin_result.user_id,
                    username=admin_result.username,
                    display_name=admin_result.display_name,
                    learner_level=admin_result.learner_level,
                    email=admin_result.email,
                    is_admin=admin_result.is_admin,
                )
                st.success("Admin signed in.")
                st.rerun()


def require_user_id() -> int:
    uid = st.session_state.get("user_id")
    if uid is None:
        st.error("Please sign in from the Dashboard.")
        st.stop()
    return int(uid)


def account_sidebar(*, key_prefix: str = "acct") -> None:
    """Call inside ``with st.sidebar:``."""
    st.subheader("Account")
    if st.button(
        "Log out",
        key=f"{key_prefix}_logout",
        type="primary",
        use_container_width=True,
    ):
        reset_user_session()
        st.rerun()


def render_admin_sidebar_tools(*, key_prefix: str = "admin") -> None:
    """Admin-only tools; hidden for non-admin users."""
    email = str(st.session_state.get("email", "")).strip().lower()
    username = str(st.session_state.get("username", "")).strip().lower()
    policy = evaluate_user_policy(email=email, username=username)
    if not policy.can_view_admin_tools:
        return

    st.subheader("Admin tools")
    if policy.can_initialize_db and st.button(
        "Initialize / Verify Database",
        key=f"{key_prefix}_init_db",
        use_container_width=True,
    ):
        try:
            init_db()
            st.success("Database schema is ready.")
        except Exception as exc:
            st.error(f"Could not initialize DB: {exc}")

    if policy.can_clear_cache and st.button(
        "Clear caches only",
        key=f"{key_prefix}_clear_cache",
        help="Clears cached resources while keeping session login.",
        use_container_width=True,
    ):
        try:
            st.cache_data.clear()
        except Exception:
            pass
        try:
            st.cache_resource.clear()
        except Exception:
            pass
        st.success("Caches cleared.")


def render_donate_sidebar() -> None:
    url = get_paypal_donate_url()
    if not url:
        return
    st.subheader("Support")
    st.link_button("Donate with PayPal", url=url, use_container_width=True)


def learner_badge() -> None:
    """Call inside ``with st.sidebar:``."""
    name = st.session_state.get("display_name", "")
    level = st.session_state.get("learner_level", "")
    label = "SAT / high school prep" if level == "sat" else "Grade-level practice (middle school)"
    st.caption(f"**{name}** · {label}")
