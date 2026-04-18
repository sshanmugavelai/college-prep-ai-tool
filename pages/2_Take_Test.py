import time

import streamlit as st

from db.repository import (
    create_attempt,
    get_attempt,
    get_attempt_questions,
    list_tests,
    save_answer,
    submit_attempt,
)
from utils.session import init_session_state, reset_attempt_state


st.title("📝 Take Test")
st.caption("Answer one question at a time, then submit for scoring.")
init_session_state()


def _start_attempt(test_id: int) -> None:
    attempt_id = create_attempt(test_id)
    st.session_state.current_attempt_id = attempt_id
    st.session_state.question_index = 0
    st.session_state.attempt_started_at = int(time.time())


if not st.session_state.current_attempt_id:
    tests = list_tests(limit=100)
    if not tests:
        st.info("No tests available yet. Generate one first.")
    else:
        test_options = {f"#{t['id']} - {t['exam_type']} {t['section']} ({t['difficulty']})": t for t in tests}
        selected_label = st.selectbox("Select a test", list(test_options.keys()))
        selected_test = test_options[selected_label]
        if st.button("Start test", type="primary"):
            _start_attempt(selected_test["id"])
            st.rerun()
else:
    attempt_id = st.session_state.current_attempt_id
    attempt = get_attempt(attempt_id)
    if not attempt:
        st.error("Attempt not found. Restarting state.")
        reset_attempt_state()
        st.stop()

    questions = get_attempt_questions(attempt_id)
    total = len(questions)
    if total == 0:
        st.warning("This test has no questions.")
        reset_attempt_state()
        st.stop()

    if attempt["status"] == "submitted":
        st.success(f"Attempt submitted. Score: {attempt['score_percent']}%")
        if st.button("Start another test"):
            reset_attempt_state()
            st.rerun()
        st.stop()

    idx = st.session_state.question_index
    idx = max(0, min(idx, total - 1))
    st.session_state.question_index = idx
    q = questions[idx]

    st.write(f"**Test**: {attempt['exam_type']} {attempt['section']} ({attempt['difficulty']})")
    st.progress((idx + 1) / total, text=f"Question {idx + 1} of {total}")

    if attempt["timed"] and attempt["time_limit_minutes"]:
        elapsed_sec = int(time.time()) - int(st.session_state.attempt_started_at or int(time.time()))
        remaining_sec = int(attempt["time_limit_minutes"]) * 60 - elapsed_sec
        if remaining_sec <= 0:
            st.error("Time is up. Submitting automatically.")
            submit_attempt(attempt_id)
            reset_attempt_state()
            st.rerun()
        mins = remaining_sec // 60
        secs = remaining_sec % 60
        st.info(f"Time remaining: {mins:02d}:{secs:02d}")

    st.subheader(f"Q{q['question_order']}: {q['question_text']}")
    labels = ["A", "B", "C", "D"]
    options_map = {labels[i]: q["choices"][i] for i in range(4)}
    current_value = q["selected_answer"] if q["selected_answer"] in options_map else None

    selected = st.radio(
        "Choose your answer",
        options=["", *list(options_map.keys())],
        format_func=lambda k: "Select..." if k == "" else f"{k}. {options_map[k]}",
        index=(["", *list(options_map.keys())].index(current_value) if current_value else 0),
        key=f"answer_{q['question_id']}",
    )

    col1, col2, col3 = st.columns([1, 1, 2])
    with col1:
        if st.button("Save answer"):
            if selected in {"A", "B", "C", "D"}:
                save_answer(attempt_id, q["question_id"], selected)
                st.success("Saved.")
                st.rerun()
            else:
                st.warning("Pick an answer before saving.")
    with col2:
        if st.button("Previous", disabled=idx == 0):
            st.session_state.question_index = max(0, idx - 1)
            st.rerun()
    with col3:
        if st.button("Next", disabled=idx >= total - 1):
            st.session_state.question_index = min(total - 1, idx + 1)
            st.rerun()

    st.markdown("---")
    st.warning("Submitting will finalize scoring and generate review data.")
    if st.button("Submit Test", type="primary"):
        for qq in questions:
            user_answer = st.session_state.get(f"answer_{qq['question_id']}")
            if user_answer in {"A", "B", "C", "D"}:
                save_answer(attempt_id, qq["question_id"], user_answer)
        submit_attempt(attempt_id)
        st.success("Test submitted! Go to 'Review Results'.")
        reset_attempt_state()
        st.rerun()
