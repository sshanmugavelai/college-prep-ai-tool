import streamlit as st

from ai.prompts import (
    MISTAKE_EXPLANATION_PROMPT,
    QUESTION_GENERATION_PROMPT,
    STUDY_PLAN_PROMPT,
)


st.title("🤖 Claude Prompt Templates")
st.caption("Reusable prompts for question generation, mistake analysis, and study planning.")

st.subheader("1) Question generation prompt")
st.code(
    QUESTION_GENERATION_PROMPT.format(
        exam_type="SAT",
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
