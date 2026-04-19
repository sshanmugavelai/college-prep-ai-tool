"""Single-workspace UI: overview, generate, take test, review (one section per rerun)."""

import json
import time

import streamlit as st

from ai.client import ClaudeClient
from db.repository import (
    create_attempt,
    create_test_with_questions,
    get_attempt,
    get_attempt_questions,
    get_dashboard_stats,
    get_recent_activity,
    get_review_attempts,
    list_tests,
    save_answer,
    submit_attempt,
    update_ai_feedback,
)
from utils.session import reset_attempt_state
from utils.validation import validate_questions_payload


def _fmt_activity_time(value: object) -> str:
    if value is None:
        return ""
    if hasattr(value, "strftime"):
        return value.strftime("%Y-%m-%d %H:%M")
    return str(value)


def _resume_attempt(attempt_id: int) -> None:
    attempt = get_attempt(attempt_id)
    if not attempt:
        st.error("Attempt not found.")
        return
    if attempt["status"] != "in_progress":
        st.error("This attempt is not in progress.")
        return
    st.session_state.current_attempt_id = attempt_id
    questions = get_attempt_questions(attempt_id)
    first_unanswered = 0
    for i, q in enumerate(questions):
        if not q.get("selected_answer"):
            first_unanswered = i
            break
    else:
        first_unanswered = max(0, len(questions) - 1)
    st.session_state.question_index = first_unanswered
    started = attempt.get("started_at")
    st.session_state.attempt_started_at = (
        int(started.timestamp()) if started is not None and hasattr(started, "timestamp") else int(time.time())
    )
    st.session_state._pending_workspace_step = "Take test"
    st.rerun()


def _retake_same_test(test_id: int) -> None:
    new_id = create_attempt(test_id, practice_mode=False)
    st.session_state.current_attempt_id = new_id
    st.session_state.question_index = 0
    st.session_state.attempt_started_at = int(time.time())
    st.session_state._pending_workspace_step = "Take test"
    st.rerun()


def render_overview() -> None:
    try:
        stats = get_dashboard_stats()
        recent = get_recent_activity(limit=8)

        c1, c2, c3 = st.columns(3)
        c1.metric("Total tests taken", stats.total_tests_taken)
        c2.metric("Average score", f"{stats.average_score:.2f}%")
        c3.metric("Weak topics", ", ".join(stats.weak_topics) if stats.weak_topics else "N/A")

        st.subheader("Recommended next practice")
        st.info(stats.recommended_next_practice)

        st.subheader("Recent activity")
        if recent:
            st.caption(
                "Continue an in-progress attempt, or retake the same test paper (new attempt). "
                "Mode: **P** = practice (hints on), **R** = real test."
            )
            header = st.columns([1.0, 1.9, 1.0, 0.85, 1.0, 1.35, 1.5])
            header[0].markdown("**Attempt**")
            header[1].markdown("**Test**")
            header[2].markdown("**Score**")
            header[3].markdown("**Mode**")
            header[4].markdown("**Status**")
            header[5].markdown("**When**")
            header[6].markdown("**Action**")
            for row in recent:
                test_label = f"{row['exam_type']} {row['section']} ({row['difficulty']})"
                score = row.get("score_percent")
                score_s = f"{float(score):.1f}%" if score is not None else "—"
                mode_s = "P" if row.get("practice_mode") else "R"
                rcols = st.columns([1.0, 1.9, 1.0, 0.85, 1.0, 1.35, 1.5])
                rcols[0].write(f"#{row['attempt_id']}")
                rcols[1].write(test_label)
                rcols[2].write(score_s)
                rcols[3].write(mode_s)
                rcols[4].write(row.get("status", ""))
                rcols[5].write(_fmt_activity_time(row.get("activity_time")))
                with rcols[6]:
                    if row.get("status") == "in_progress":
                        if st.button("Continue", key=f"ov_cont_{row['attempt_id']}", type="primary"):
                            _resume_attempt(int(row["attempt_id"]))
                    else:
                        tid = int(row["test_id"])
                        if st.button("Retake", key=f"ov_retake_{row['attempt_id']}", help="Start a new attempt with the same questions"):
                            _retake_same_test(tid)
        else:
            st.write("No attempts yet. Generate a practice test and complete an attempt.")
    except Exception as exc:
        st.warning("Dashboard is not ready yet. Use the sidebar to initialize the database and confirm env vars.")
        st.code(str(exc))


def render_generate() -> None:
    st.subheader("Generate practice test")
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


def _start_attempt(test_id: int, practice_mode: bool = False) -> None:
    attempt_id = create_attempt(test_id, practice_mode=practice_mode)
    st.session_state.current_attempt_id = attempt_id
    st.session_state.question_index = 0
    st.session_state.attempt_started_at = int(time.time())


def render_take_test() -> None:
    st.subheader("Take test")
    st.caption(
        "Choose **Real test** for exam-style conditions (no hints). "
        "Choose **Practice** to see topic + explanation hints while you answer."
    )

    if not st.session_state.current_attempt_id:
        tests = list_tests(limit=100)
        if not tests:
            st.info("No tests available yet. Generate one in **Generate tests**.")
            return
        test_options = {f"#{t['id']} - {t['exam_type']} {t['section']} ({t['difficulty']})": t for t in tests}
        selected_label = st.selectbox("Select a test", list(test_options.keys()))
        selected_test = test_options[selected_label]
        test_mode = st.radio(
            "How do you want to take it?",
            [
                "Real test — no hints or explanations until review",
                "Practice — show topic + explanation hints with each question",
            ],
            horizontal=True,
            key="take_test_mode_choice",
        )
        practice_mode = "Practice" in test_mode
        if st.button("Start test", type="primary"):
            _start_attempt(selected_test["id"], practice_mode=practice_mode)
            st.rerun()
        return

    attempt_id = st.session_state.current_attempt_id
    attempt = get_attempt(attempt_id)
    if not attempt:
        st.error("Attempt not found. Restarting state.")
        reset_attempt_state()
        return

    questions = get_attempt_questions(attempt_id)
    total = len(questions)
    if total == 0:
        st.warning("This test has no questions.")
        reset_attempt_state()
        return

    if attempt["status"] == "submitted":
        mode_note = " (practice mode)" if attempt.get("practice_mode") else " (real test)"
        st.success(f"Attempt submitted{mode_note}. Score: {attempt['score_percent']}%")
        if st.button("Start another test"):
            reset_attempt_state()
            st.rerun()
        return

    idx = st.session_state.question_index
    idx = max(0, min(idx, total - 1))
    st.session_state.question_index = idx
    q = questions[idx]

    practice_mode = bool(attempt.get("practice_mode"))

    st.write(f"**Test**: {attempt['exam_type']} {attempt['section']} ({attempt['difficulty']})")
    if practice_mode:
        st.success(
            "Practice mode — each question includes topic and explanation hints (not exam conditions)."
        )
    else:
        st.caption("Real test mode — no explanations until you finish and open Review.")

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

    st.markdown(f"**Q{q['question_order']}:** {q['question_text']}")

    if practice_mode:
        st.info(
            f"**Topic:** {q['topic']} · **Skill difficulty:** {q['difficulty']}\n\n"
            f"**Explanation / hint:** {q['explanation']}"
        )
        st.caption("Practice mode shows the written explanation to support learning; it may reflect the keyed answer.")

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
    if st.button("Submit test", type="primary"):
        for qq in questions:
            user_answer = st.session_state.get(f"answer_{qq['question_id']}")
            if user_answer in {"A", "B", "C", "D"}:
                save_answer(attempt_id, qq["question_id"], user_answer)
        submit_attempt(attempt_id)
        st.success("Test submitted! Open **Review** to see results.")
        reset_attempt_state()
        st.rerun()


def _render_review_hints_panel(q: dict, selected_attempt: dict, attempt_id: int) -> None:
    """Built-in + optional AI hints for re-review (different approaches, flashcards)."""
    with st.expander("Hints for review (even if you solved it differently)", expanded=False):
        st.markdown(
            f"- **Skill:** {q['topic']} · {selected_attempt['exam_type']} {selected_attempt['section']}\n"
            "- **First pass:** Say in your own words what the question is asking.\n"
            "- **Second pass:** For each choice, ask what evidence supports or contradicts it.\n"
            "- **Hard route?** Time-box 90s; if stuck, note *where* the reasoning tangled."
        )
        cache_key = f"review_ai_hints_{attempt_id}_{q['question_id']}"
        hints_cached = st.session_state.get(cache_key)
        if st.button(
            "Generate AI study hints (3 steps)",
            key=f"gen_review_hints_{attempt_id}_{q['question_id']}",
        ):
            with st.spinner("Generating hints..."):
                try:
                    client = ClaudeClient()
                    out = client.generate_review_hints(
                        exam_type=selected_attempt["exam_type"],
                        section=selected_attempt["section"],
                        question=q["question_text"],
                        choices=q["choices"],
                        correct_answer=q["correct_answer"],
                        user_answer=q["selected_answer"] or "No answer",
                        topic=q["topic"],
                        difficulty=q["difficulty"],
                    )
                    hints = out.get("hints") if isinstance(out.get("hints"), list) else []
                    st.session_state[cache_key] = hints[:3] if hints else []
                    st.rerun()
                except Exception as exc:
                    st.error(f"Could not generate hints: {exc}")
        if hints_cached:
            st.markdown("**AI hints**")
            for i, h in enumerate(hints_cached, start=1):
                st.markdown(f"{i}. {h}")


def _render_flashcard_mode(
    questions: list[dict],
    selected_attempt: dict,
    attempt_id: int,
) -> None:
    n = len(questions)
    idx_key = f"flash_idx_{attempt_id}"
    side_key = f"flash_side_{attempt_id}"
    if idx_key not in st.session_state:
        st.session_state[idx_key] = 0
    if side_key not in st.session_state:
        st.session_state[side_key] = False

    idx = max(0, min(int(st.session_state[idx_key]), n - 1))
    st.session_state[idx_key] = idx
    q = questions[idx]
    show_back = bool(st.session_state[side_key])

    st.progress((idx + 1) / n, text=f"Flashcard {idx + 1} of {n}")

    with st.container(border=True):
        if not show_back:
            st.markdown(f"### Q{q['question_order']} · {q['topic']}")
            st.write(q["question_text"])
            labels = ["A", "B", "C", "D"]
            for i, choice in enumerate(q["choices"]):
                st.write(f"**{labels[i]}.** {choice}")
            st.caption("Work the question mentally, then flip to compare with the key and explanation.")
        else:
            ok = bool(q["is_correct"])
            st.markdown("### Answer key & explanation")
            if ok:
                st.success("You got this one correct.")
            else:
                st.warning("Review the reasoning below — your approach may still have been partly useful.")
            st.write(f"**Correct answer:** {q['correct_answer']}")
            st.write(f"**Your answer:** {q['selected_answer'] or 'No answer'}")
            st.write(f"**Explanation:** {q['explanation']}")
            feedback = q.get("ai_feedback")
            if feedback and not ok:
                st.info(
                    f"**Concept to solidify:** {feedback.get('concept_to_learn', '')}\n\n"
                    f"**Why the right answer works:** {feedback.get('correct_explanation', '')}"
                )

        _render_review_hints_panel(q, selected_attempt, attempt_id)

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        if st.button("← Previous", disabled=idx == 0, key=f"fc_prev_{attempt_id}"):
            st.session_state[idx_key] = idx - 1
            st.session_state[side_key] = False
            st.rerun()
    with c2:
        if st.button("Flip card", type="primary", key=f"fc_flip_{attempt_id}"):
            st.session_state[side_key] = not show_back
            st.rerun()
    with c3:
        if st.button("Next →", disabled=idx >= n - 1, key=f"fc_next_{attempt_id}"):
            st.session_state[idx_key] = idx + 1
            st.session_state[side_key] = False
            st.rerun()
    with c4:
        if st.button("Front side", key=f"fc_reset_{attempt_id}"):
            st.session_state[side_key] = False
            st.rerun()


def _ensure_ai_feedback_for_question(
    client: ClaudeClient,
    attempt_id: int,
    selected_attempt: dict,
    q: dict,
) -> dict:
    if q["is_correct"]:
        return {}
    if q["ai_feedback"]:
        return q["ai_feedback"]

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


def render_review() -> None:
    st.subheader("Review results")
    st.caption(
        "Question list for line-by-line review, or **flashcards** to rehearse without spoiling the answer first. "
        "Hints work either way — useful if your student used a different approach."
    )

    attempts = [a for a in get_review_attempts(limit=100) if a["status"] == "submitted"]
    if not attempts:
        st.info("No submitted attempts yet. Take and submit a test first.")
        return

    options = {
        (
            f"Attempt #{a['id']} - {a['exam_type']} {a['section']} "
            f"({a['difficulty']}) | Score: {a['score_percent']}% | "
            f"{'Practice' if a.get('practice_mode') else 'Real test'}"
        ): a
        for a in attempts
    }
    selected_label = st.selectbox("Select a submitted attempt", list(options.keys()))
    selected_attempt = options[selected_label]
    attempt_id = selected_attempt["id"]

    st.markdown("**Attempt summary**")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Correct", f"{selected_attempt['correct_count']} / {selected_attempt['total_questions']}")
    c2.metric("Score", f"{selected_attempt['score_percent']}%")
    c3.metric("Section", f"{selected_attempt['exam_type']} {selected_attempt['section']}")
    c4.metric(
        "Mode",
        "Practice" if selected_attempt.get("practice_mode") else "Real test",
    )

    questions = get_attempt_questions(attempt_id)
    wrong_questions = [q for q in questions if not q["is_correct"]]

    st.markdown("---")
    st.markdown("**Questions**")

    if wrong_questions and st.button("Generate AI feedback for all mistakes", type="primary"):
        with st.spinner("Generating AI feedback..."):
            try:
                client = ClaudeClient()
                for q in wrong_questions:
                    _ensure_ai_feedback_for_question(client, attempt_id, selected_attempt, q)
                st.success("AI feedback generated for all mistakes.")
                st.rerun()
            except Exception as exc:
                st.error(f"Could not generate AI feedback: {exc}")

    review_mode = st.radio(
        "How do you want to review?",
        ["Question list", "Flashcards"],
        horizontal=True,
        key=f"review_mode_{attempt_id}",
    )

    if review_mode == "Flashcards":
        _render_flashcard_mode(questions, selected_attempt, attempt_id)
        return

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

            _render_review_hints_panel(q, selected_attempt, attempt_id)

            if not is_correct:
                feedback = q["ai_feedback"]
                if not feedback:
                    if st.button("Generate AI explanation", key=f"ai_{q['question_id']}"):
                        with st.spinner("Generating explanation..."):
                            try:
                                client = ClaudeClient()
                                feedback = _ensure_ai_feedback_for_question(
                                    client, attempt_id, selected_attempt, q
                                )
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
                    st.caption(
                        "Expected JSON schema: correct_explanation, why_user_wrong, "
                        "concept_to_learn, difficulty_adjustment"
                    )
