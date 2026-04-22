import streamlit as st

from db.repository import (
    create_retry_test_from_mistakes,
    list_mistakes,
    list_tests,
)
from utils.auth_ui import (
    account_sidebar,
    learner_badge,
    render_donate_sidebar,
    render_login_page,
    require_user_id,
)
from utils.session import ensure_auth_session_version, is_logged_in

ensure_auth_session_version()
if not is_logged_in():
    render_login_page()
    st.stop()

user_id = require_user_id()

st.title("📒 Mistake Journal")
st.caption("Track incorrect answers by topic and create retry tests.")

with st.sidebar:
    learner_badge()
    account_sidebar(key_prefix="mj")
    render_donate_sidebar()

level = st.session_state.get("learner_level", "sat")
if level == "middle_school":
    st.caption("Mistakes from **middle school** practice (not SAT/ACT).")
    exam_type = "Middle school"
else:
    exam_type = st.selectbox("Exam type", ["SAT", "ACT"])
section = st.selectbox("Section", ["Reading", "Writing", "Math"])
topic_filter = st.text_input("Topic filter (optional)", value="").strip() or None
only_open = st.toggle("Show only open mistakes", value=True)

mistakes = list_mistakes(
    user_id,
    exam_type=exam_type,
    section=section,
    topic=topic_filter,
    only_open=only_open,
)

if mistakes:
    st.write(f"Found {len(mistakes)} mistake entries.")
    st.dataframe(
        [
            {
                "mistake_id": m["id"],
                "attempt_id": m["attempt_id"],
                "topic": m["topic"],
                "user_answer": m["user_answer"],
                "correct_answer": m["correct_answer"],
                "concept_to_learn": m["concept_to_learn"],
                "status": m["review_status"],
                "created_at": m["created_at"],
            }
            for m in mistakes
        ],
        use_container_width=True,
    )

    with st.expander("Preview mistake details"):
        for m in mistakes[:10]:
            st.markdown(f"**Topic:** {m['topic']} | **Attempt:** {m['attempt_id']}")
            st.write(m["question_text"])
            labels = ["A", "B", "C", "D"]
            for i, c in enumerate(m["choices"]):
                st.write(f"{labels[i]}. {c}")
            st.write(f"Your answer: {m['user_answer'] or 'No answer'}")
            st.write(f"Correct answer: {m['correct_answer']}")
            st.write(f"Question explanation: {m['explanation']}")
            if m.get("concept_to_learn"):
                st.write(f"Concept to learn: {m['concept_to_learn']}")
            st.markdown("---")
else:
    st.info("No mistakes match your filters yet.")

st.markdown("---")
st.subheader("Retry only incorrect questions")
max_retry = st.slider("Max questions in retry test", min_value=5, max_value=30, value=10, step=1)

if st.button("Create retry test", type="primary"):
    test_id = create_retry_test_from_mistakes(
        user_id,
        exam_type=exam_type,
        section=section,
        topic=topic_filter,
        max_questions=max_retry,
    )
    if not test_id:
        st.warning("No matching mistakes available to create a retry test.")
    else:
        st.success(f"Created retry test #{test_id}. You can take it from the Take Test page.")

st.subheader("Recent tests")
try:
    st.dataframe(list_tests(user_id, limit=20), use_container_width=True)
except Exception as exc:
    st.error(f"Could not load recent tests: {exc}")
