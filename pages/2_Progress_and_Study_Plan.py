import json

import pandas as pd
import plotly.express as px
import streamlit as st

from ai.client import ClaudeClient
from db.repository import (
    build_performance_summary_text,
    get_accuracy_by_topic,
    get_latest_progress_snapshot,
    get_progress_over_time,
    save_recommended_next_practice,
)
from utils.auth_ui import learner_badge, logout_button, render_login_page, require_user_id


if not st.session_state.get("user_id"):
    render_login_page()
    st.stop()

user_id = require_user_id()

st.title("📈 Progress & AI Study Plan")
st.caption("Track trends and generate a weekly practice plan from Claude.")

with st.sidebar:
    learner_badge()
    logout_button()

try:
    score_rows = get_progress_over_time(user_id)
    topic_rows = get_accuracy_by_topic(user_id)
    latest = get_latest_progress_snapshot(user_id)
except Exception as exc:
    st.error(f"Database is not ready: {exc}")
    st.stop()

st.subheader("Score over time")
if score_rows:
    df_scores = pd.DataFrame(score_rows)
    df_scores["submitted_at"] = pd.to_datetime(df_scores["submitted_at"])
    fig_scores = px.line(
        df_scores,
        x="submitted_at",
        y="score_percent",
        markers=True,
        title="Submitted attempt scores",
    )
    fig_scores.update_layout(yaxis_title="Score (%)", xaxis_title="Date")
    st.plotly_chart(fig_scores, use_container_width=True)
else:
    st.info("No submitted attempts yet.")

st.subheader("Accuracy by topic")
if topic_rows:
    df_topics = pd.DataFrame(topic_rows)
    fig_topics = px.bar(
        df_topics,
        x="topic",
        y="accuracy_pct",
        title="Topic accuracy",
        text="accuracy_pct",
    )
    fig_topics.update_layout(yaxis_title="Accuracy (%)", xaxis_title="Topic")
    st.plotly_chart(fig_topics, use_container_width=True)
    st.dataframe(df_topics, use_container_width=True)
else:
    st.info("No topic accuracy data yet.")

st.subheader("Current trend summary")
if latest and latest.get("trend_summary"):
    st.info(latest["trend_summary"])
else:
    st.write("Trend data not available yet.")

st.subheader("Recommended next practice")
if latest and latest.get("recommended_next_practice"):
    st.success(latest["recommended_next_practice"])
else:
    st.write("No recommendation yet.")

st.markdown("---")
st.subheader("Generate AI weekly study plan")

summary_text = build_performance_summary_text(user_id)
with st.expander("Performance summary sent to Claude"):
    st.code(summary_text)

if st.button("Generate weekly AI study plan", type="primary"):
    with st.spinner("Generating plan with Claude..."):
        try:
            client = ClaudeClient()
            plan = client.generate_study_plan(summary_text)
            st.success("Weekly plan generated.")
            st.json(plan)

            if isinstance(plan, dict):
                overall = plan.get("overall_advice")
                if overall:
                    save_recommended_next_practice(user_id, str(overall))
        except Exception as exc:
            st.error(f"Could not generate study plan: {exc}")

with st.expander("Expected study plan JSON"):
    st.code(
        json.dumps(
            {
                "weekly_plan": [
                    {
                        "day": "Monday",
                        "focus_topics": ["algebra", "inference"],
                        "questions_target": 20,
                        "schedule_tip": "Do 10 questions before school and 10 after dinner.",
                    }
                ],
                "overall_advice": "Focus 60% effort on weak topics.",
            },
            indent=2,
        ),
        language="json",
    )
