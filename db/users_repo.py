from typing import Any, Optional

from psycopg.rows import dict_row

from db.connection import get_conn
from db.migrate_family_users import ensure_family_seed_users


def get_user_by_username(username: str) -> Optional[dict[str, Any]]:
    user = (username or "").strip()
    if not user:
        return None
    with get_conn() as conn:
        ensure_family_seed_users(conn)
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                SELECT id, username, display_name, learner_level
                FROM public.users
                WHERE LOWER(username) = LOWER(%s)
                """,
                (user,),
            )
            row = cur.fetchone()
    return dict(row) if row else None


def get_user_by_id(user_id: int) -> Optional[dict[str, Any]]:
    with get_conn() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                "SELECT id, username, display_name, learner_level FROM users WHERE id = %s",
                (user_id,),
            )
            row = cur.fetchone()
    return dict(row) if row else None
