from typing import Any, Optional

from psycopg.rows import dict_row

from db.connection import get_conn
from db.migrate_family_users import ensure_family_seed_users
from db.passwords import verify_password
from utils.config import get_middle_school_emails

from auth.contracts import ExternalIdentity


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


def authenticate_local_credentials(*, username: str, password: str) -> Optional[dict[str, Any]]:
    user = (username or "").strip()
    plain = password or ""
    if not user or not plain:
        return None
    with get_conn() as conn:
        ensure_family_seed_users(conn)
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                SELECT id, username, display_name, learner_level, password_hash
                FROM users
                WHERE LOWER(username) = LOWER(%s)
                LIMIT 1
                """,
                (user,),
            )
            row = cur.fetchone()
            if not row:
                return None
            stored = str(row.get("password_hash") or "").strip()
            if not stored:
                return None
            if not verify_password(plain, stored):
                return None
            return {
                "id": int(row["id"]),
                "username": str(row["username"]),
                "display_name": str(row["display_name"]),
                "learner_level": str(row["learner_level"]),
            }


def upsert_user_from_external_identity(identity: ExternalIdentity) -> dict[str, Any]:
    """Create or update local user for an external identity provider login."""
    provider = identity.provider.strip().lower()
    subject = identity.subject.strip()
    email = identity.email.strip().lower()
    display_name = identity.display_name.strip() or email
    if not provider or not subject or not email:
        raise ValueError("External identity requires provider, subject, and email.")

    with get_conn() as conn:
        ensure_family_seed_users(conn)
        with conn.cursor(row_factory=dict_row) as cur:
            # 1) Stable key: provider + subject.
            cur.execute(
                """
                SELECT u.id, u.username, u.display_name, u.learner_level
                FROM user_identities ui
                JOIN users u ON u.id = ui.user_id
                WHERE ui.provider = %s AND ui.subject = %s
                LIMIT 1
                """,
                (provider, subject),
            )
            existing = cur.fetchone()
            if existing:
                cur.execute("UPDATE user_identities SET email = %s WHERE provider = %s AND subject = %s", (email, provider, subject))
                cur.execute("UPDATE users SET display_name = %s WHERE id = %s", (display_name, existing["id"]))
                conn.commit()
                return _get_user_by_id_cur(cur, int(existing["id"]))

            # 2) Recover if the same provider/email exists with a rotated subject.
            cur.execute(
                """
                SELECT ui.id AS identity_id, u.id AS user_id
                FROM user_identities ui
                JOIN users u ON u.id = ui.user_id
                WHERE ui.provider = %s AND LOWER(ui.email) = LOWER(%s)
                LIMIT 1
                """,
                (provider, email),
            )
            by_email_identity = cur.fetchone()
            if by_email_identity:
                cur.execute(
                    "UPDATE user_identities SET subject = %s, email = %s WHERE id = %s",
                    (subject, email, by_email_identity["identity_id"]),
                )
                cur.execute(
                    "UPDATE users SET display_name = %s WHERE id = %s",
                    (display_name, by_email_identity["user_id"]),
                )
                conn.commit()
                return _get_user_by_id_cur(cur, int(by_email_identity["user_id"]))

            # 3) Reuse existing user record where username already equals email.
            cur.execute("SELECT id FROM users WHERE LOWER(username) = LOWER(%s) LIMIT 1", (email,))
            user_row = cur.fetchone()
            if user_row:
                user_id = int(user_row["id"])
                cur.execute("UPDATE users SET display_name = %s WHERE id = %s", (display_name, user_id))
            else:
                learner_level = _infer_learner_level(email=email)
                cur.execute(
                    """
                    INSERT INTO users (username, password_hash, display_name, learner_level)
                    VALUES (%s, NULL, %s, %s)
                    RETURNING id
                    """,
                    (email, display_name, learner_level),
                )
                user_id = int(cur.fetchone()["id"])

            cur.execute(
                """
                INSERT INTO user_identities (user_id, provider, subject, email)
                VALUES (%s, %s, %s, %s)
                """,
                (user_id, provider, subject, email),
            )
        conn.commit()

    row = get_user_by_id(user_id)
    if not row:
        raise RuntimeError("Unable to read user after identity upsert.")
    return row


def _infer_learner_level(*, email: str) -> str:
    return "middle_school" if email.strip().lower() in get_middle_school_emails() else "sat"


def _get_user_by_id_cur(cur: Any, user_id: int) -> dict[str, Any]:
    cur.execute(
        "SELECT id, username, display_name, learner_level FROM users WHERE id = %s",
        (user_id,),
    )
    row = cur.fetchone()
    if not row:
        raise RuntimeError(f"User {user_id} not found.")
    return dict(row)
