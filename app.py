import streamlit as st

from db.init_db import init_db
from db.repository import get_dashboard_stats, get_recent_activity
from utils.session import init_session_state


st.set_page_config(page_title="College Prep AI Tool", page_icon="📘", layout="wide")
init_session_state()


st.title("📘 College Prep AI Tool")
st.caption("Local SAT/ACT prep powered by Claude + Postgres")


if st.button("Initialize / Verify Database"):
    try:
        init_db()
        st.success("Database schema is ready.")
    except Exception as exc:
        st.error(f"Could not initialize DB: {exc}")


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
        st.dataframe(recent, use_container_width=True)
    else:
        st.write("No attempts yet. Generate your first practice test in the next page.")
except Exception as exc:
    st.warning("Dashboard is not ready yet. Click 'Initialize / Verify Database' and confirm env vars.")
    st.code(str(exc))


st.markdown("---")
st.markdown(
    """
### App flow
1. **Generate Practice Test** (Claude creates original questions)
2. **Take Test** (one question at a time)
3. **Review Results** (score + explanations + AI feedback)
4. **Mistake Journal** (retry weak areas)
5. **Progress & Study Plan** (charts + weekly AI plan)
"""
)
