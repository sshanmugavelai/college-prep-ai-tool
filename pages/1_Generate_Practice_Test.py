import json

import streamlit as st

from ai.client import ClaudeClient
from db.repository import create_test_with_questions, list_tests
from utils.validation import validate_questions_payload


st.title("🧠 Generate Practice Test")
st.caption("Claude generates original SAT/ACT-style questions in structured JSON.")

exam_type = st.selectbox("Exam type", ["SAT", "ACT"])
section = st.selectbox("Section", ["Reading", "Writing", "Math"])
num_questions = st.slider("Number of questions", min_value=5, max_value=40, value=10, step=1)
difficulty = st.selectbox("Difficulty", ["easy", "medium", "hard"], index=1)
timed = st.toggle("Timed mode", value=False)
time_limit_minutes = (
    st.number_input("Time limit (minutes)", min_value=5, max_value=240, value=30, step=5)
    if timed
    else None
)

if st.button("Generate with Claude", type="primary"):
    with st.spinner("Generating questions..."):
        try:
            client = ClaudeClient()
            payload = client.generate_questions(
                exam_type=exam_type,
                section=section,
                num_questions=num_questions,
                difficulty=difficulty,
            )
            questions = validate_questions_payload(payload, expected_count=num_questions)
            test_id = create_test_with_questions(
                exam_type=exam_type,
                section=section,
                num_questions=num_questions,
                difficulty=difficulty,
                timed=timed,
                time_limit_minutes=int(time_limit_minutes) if timed else None,
                questions=questions,
                source="ai",
            )
            st.success(f"Created test #{test_id} with {len(questions)} questions.")
        except Exception as exc:
            st.error(f"Failed to generate/save test: {exc}")


with st.expander("Claude prompt template: question generation"):
    st.code(
        json.dumps(
            {
                "questions": [
                    {
                        "question": "...",
                        "choices": ["A option", "B option", "C option", "D option"],
                        "correct_answer": "B",
                        "explanation": "...",
                        "topic": "algebra",
                        "difficulty": "medium",
                    }
                ]
            },
            indent=2,
        ),
        language="json",
    )


st.subheader("Available tests")
try:
    tests = list_tests(limit=50)
    if tests:
        st.dataframe(tests, use_container_width=True)
    else:
        st.info("No tests generated yet.")
except Exception as exc:
    st.error(f"Could not load tests: {exc}")
