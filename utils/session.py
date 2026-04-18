import streamlit as st


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
