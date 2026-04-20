import streamlit as st

from ai.prompts import (
    MISTAKE_EXPLANATION_PROMPT,
    QUESTION_GENERATION_MIDDLE_SCHOOL_PROMPT,
    QUESTION_GENERATION_PROMPT,
    REVIEW_HINTS_PROMPT,
    STUDY_PLAN_PROMPT,
)
from utils.auth_ui import render_login_page
from utils.session import ensure_auth_session_version

ensure_auth_session_version()
if not st.session_state.get("user_id"):
    render_login_page()
    st.stop()

st.title("🤖 Claude Prompt Templates")
st.caption("Reusable prompts for question generation, mistake analysis, review hints, and study planning.")

st.subheader("1) Question generation prompt (SAT / high school track)")
st.code(
    QUESTION_GENERATION_PROMPT.format(
        exam_type="SAT",
        section="Math",
        num_questions=10,
        difficulty="medium",
    ),
    language="text",
)

st.subheader("1b) Middle school (grade-level) generation — Thrishi’s track")
st.code(
    QUESTION_GENERATION_MIDDLE_SCHOOL_PROMPT.format(
        section="Math",
        num_questions=10,
        difficulty="medium",
    ),
    language="text",
)

st.subheader("2) Mistake explanation prompt")
st.code(
    MISTAKE_EXPLANATION_PROMPT.format(
        exam_type="ACT",
        section="Reading",
        question="Which inference is best supported by the passage?",
        choices=["Option A", "Option B", "Option C", "Option D"],
        correct_answer="C",
        user_answer="A",
        topic="inference",
        difficulty="medium",
    ),
    language="text",
)

st.subheader("3) Weekly study plan prompt")
st.code(
    STUDY_PLAN_PROMPT.format(
        performance_summary=(
            "Total submitted tests: 6\n"
            "Average score: 72.5%\n"
            "Weak topics: algebra, punctuation\n"
            "Recent activity:\n"
            "- SAT Math (medium): 68%\n"
            "- ACT Writing (hard): 70%"
        )
    ),
    language="text",
)

st.subheader("4) Post-test review hints (flashcards / spaced review)")
st.code(
    REVIEW_HINTS_PROMPT.format(
        exam_type="SAT",
        section="Reading",
        topic="inference",
        difficulty="medium",
        question="Which choice is best supported by the passage?",
        choices_lines="A. First\nB. Second\nC. Third\nD. Fourth",
        user_answer="B",
        correct_answer="C",
    ),
    language="text",
)
