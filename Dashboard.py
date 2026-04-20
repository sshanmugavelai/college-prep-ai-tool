import streamlit as st

from db.init_db import init_db
from utils.auth_ui import learner_badge, logout_button, render_login_page
from utils.session import ensure_auth_session_version, init_session_state, is_logged_in
from workspace_sections import render_generate, render_overview, render_review, render_take_test


st.set_page_config(page_title="College Prep AI Tool", page_icon="📘", layout="wide")

ensure_auth_session_version()
if not is_logged_in():
    render_login_page()
    st.stop()

init_session_state()

# Continue/Retake from Overview sets this; must apply before st.radio(key="workspace_step") is created.
if "_pending_workspace_step" in st.session_state:
    st.session_state.workspace_step = st.session_state.pop("_pending_workspace_step")

with st.sidebar:
    st.header("College Prep AI")
    learner_badge()
    logout_button()
    st.caption("SAT/ACT practice with Claude + Postgres")
    if st.button("Initialize / Verify Database"):
        try:
            init_db()
            st.success("Database schema is ready.")
        except Exception as exc:
            st.error(f"Could not initialize DB: {exc}")
    st.divider()
    st.subheader("More")
    st.page_link("pages/1_Mistake_Journal.py", label="Mistake Journal", icon="📓")
    st.page_link("pages/2_Progress_and_Study_Plan.py", label="Progress & study plan", icon="📈")
    st.page_link("pages/3_AI_Prompts.py", label="AI prompts", icon="🧩")

st.title("📘 Practice workspace")
st.caption("Overview, generation, testing, and review in one place — pick a step below.")

workspace = st.radio(
    "Step",
    ["Overview", "Generate tests", "Take test", "Review"],
    horizontal=True,
    label_visibility="collapsed",
    key="workspace_step",
)

if workspace == "Overview":
    render_overview()
elif workspace == "Generate tests":
    render_generate()
elif workspace == "Take test":
    render_take_test()
else:
    render_review()
