import json

import streamlit as st

from ai.client import ClaudeClient
from db.repository import get_attempt_questions, get_review_attempts, update_ai_feedback


st.title("🔍 Review Results")
st.caption("See score details, explanations, and AI feedback for mistakes.")

attempts = [a for a in get_review_attempts(limit=100) if a["status"] == "submitted"]
if not attempts:
    st.info("No submitted attempts yet. Take and submit a test first.")
    st.stop()

options = {
    (
        f"Attempt #{a['id']} - {a['exam_type']} {a['section']} "
        f"({a['difficulty']}) | Score: {a['score_percent']}%"
    ): a
    for a in attempts
}
selected_label = st.selectbox("Select a submitted attempt", list(options.keys()))
selected_attempt = options[selected_label]
attempt_id = selected_attempt["id"]

st.subheader("Attempt Summary")
c1, c2, c3 = st.columns(3)
c1.metric("Correct", f"{selected_attempt['correct_count']} / {selected_attempt['total_questions']}")
c2.metric("Score", f"{selected_attempt['score_percent']}%")
c3.metric("Section", f"{selected_attempt['exam_type']} {selected_attempt['section']}")

questions = get_attempt_questions(attempt_id)
wrong_questions = [q for q in questions if not q["is_correct"]]

st.markdown("---")
st.subheader("Questions")


def _ensure_ai_feedback_for_question(q: dict) -> dict:
    if q["is_correct"]:
        return {}
    if q["ai_feedback"]:
        return q["ai_feedback"]

    client = ClaudeClient()
    feedback = client.explain_mistake(
        exam_type=selected_attempt["exam_type"],
        section=selected_attempt["section"],
        question=q["question_text"],
        choices=q["choices"],
        correct_answer=q["correct_answer"],
        user_answer=q["selected_answer"] or "No answer selected",
        topic=q["topic"],
        difficulty=q["difficulty"],
    )
    update_ai_feedback(attempt_id, q["question_id"], feedback)
    return feedback


if wrong_questions and st.button("Generate AI feedback for all mistakes", type="primary"):
    with st.spinner("Generating AI feedback..."):
        try:
            for q in wrong_questions:
                _ensure_ai_feedback_for_question(q)
            st.success("AI feedback generated for all mistakes.")
            st.rerun()
        except Exception as exc:
            st.error(f"Could not generate AI feedback: {exc}")

for q in questions:
    is_correct = bool(q["is_correct"])
    status_emoji = "✅" if is_correct else "❌"
    with st.expander(f"{status_emoji} Q{q['question_order']} | Topic: {q['topic']}", expanded=False):
        st.write(q["question_text"])
        labels = ["A", "B", "C", "D"]
        for i, choice in enumerate(q["choices"]):
            st.write(f"{labels[i]}. {choice}")

        st.write(f"**Your answer:** {q['selected_answer'] or 'No answer'}")
        st.write(f"**Correct answer:** {q['correct_answer']}")
        st.write(f"**Question explanation:** {q['explanation']}")

        if not is_correct:
            feedback = q["ai_feedback"]
            if not feedback:
                if st.button("Generate AI explanation", key=f"ai_{q['question_id']}"):
                    with st.spinner("Generating explanation..."):
                        try:
                            feedback = _ensure_ai_feedback_for_question(q)
                            st.success("AI feedback saved.")
                        except Exception as exc:
                            st.error(f"Error: {exc}")
            if feedback:
                st.markdown("**AI Review**")
                st.write(f"- **Why correct answer is right:** {feedback.get('correct_explanation', '')}")
                st.write(f"- **Why your answer was wrong:** {feedback.get('why_user_wrong', '')}")
                st.write(f"- **Concept to learn:** {feedback.get('concept_to_learn', '')}")
                st.write(f"- **Difficulty adjustment:** {feedback.get('difficulty_adjustment', 'same')}")
                with st.expander("Raw AI JSON"):
                    st.code(json.dumps(feedback, indent=2), language="json")
                st.caption("Expected JSON schema: correct_explanation, why_user_wrong, concept_to_learn, difficulty_adjustment")
