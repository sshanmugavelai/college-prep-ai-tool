"""Idempotent migrations: users table, user_id columns, OAuth identities, seed learners."""


def _table_exists(cur, name: str) -> bool:
    cur.execute(
        """
        SELECT EXISTS (
            SELECT 1 FROM information_schema.tables
            WHERE table_schema = 'public' AND table_name = %s
        )
        """,
        (name,),
    )
    return bool(cur.fetchone()[0])


def run_family_migrations(conn) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id BIGSERIAL PRIMARY KEY,
                username TEXT NOT NULL UNIQUE,
                password_hash TEXT,
                display_name TEXT NOT NULL,
                learner_level TEXT NOT NULL CHECK (learner_level IN ('sat', 'middle_school')),
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """
        )
        cur.execute("ALTER TABLE users ALTER COLUMN password_hash DROP NOT NULL")
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS user_identities (
                id BIGSERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                provider TEXT NOT NULL,
                subject TEXT NOT NULL,
                email TEXT NOT NULL,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                UNIQUE (provider, subject),
                UNIQUE (provider, email)
            )
            """
        )

        if _table_exists(cur, "tests"):
            cur.execute("ALTER TABLE tests ADD COLUMN IF NOT EXISTS user_id BIGINT")
        if _table_exists(cur, "attempts"):
            cur.execute("ALTER TABLE attempts ADD COLUMN IF NOT EXISTS user_id BIGINT")
        if _table_exists(cur, "progress"):
            cur.execute("ALTER TABLE progress ADD COLUMN IF NOT EXISTS user_id BIGINT")

        cur.execute("SELECT id FROM users WHERE username = 'ashwika' LIMIT 1")
        row = cur.fetchone()
        default_uid = row[0] if row else None

        if default_uid is not None and _table_exists(cur, "tests"):
            cur.execute(
                "UPDATE tests SET user_id = %s WHERE user_id IS NULL",
                (default_uid,),
            )
        if default_uid is not None and _table_exists(cur, "attempts") and _table_exists(cur, "tests"):
            cur.execute(
                """
                UPDATE attempts a
                SET user_id = t.user_id
                FROM tests t
                WHERE t.id = a.test_id AND a.user_id IS NULL
                """
            )
        if default_uid is not None and _table_exists(cur, "progress"):
            cur.execute(
                """
                UPDATE progress p
                SET user_id = COALESCE(
                    (SELECT a.user_id FROM attempts a WHERE a.id = p.attempt_id LIMIT 1),
                    %s
                )
                WHERE p.user_id IS NULL
                """,
                (default_uid,),
            )

        for tbl in ("tests", "attempts", "progress"):
            if not _table_exists(cur, tbl):
                continue
            cur.execute(
                f"""
                SELECT COUNT(*) FROM information_schema.columns
                WHERE table_schema = 'public' AND table_name = '{tbl}' AND column_name = 'user_id'
                """
            )
            if cur.fetchone()[0]:
                try:
                    cur.execute(f"ALTER TABLE {tbl} ALTER COLUMN user_id SET NOT NULL")
                except Exception:
                    pass


def ensure_family_seed_users(conn) -> None:
    """Insert Ashwika + Thrishi when missing.

    Called on **every** connection (see ``db.connection``). This is not part of the
    one-shot ``_SCHEMA_PATCHED`` block: a long-lived Streamlit process would otherwise
    never re-run migrations, so a missing ``thrishi`` row could persist until restart.
    """
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT EXISTS (
                SELECT 1 FROM information_schema.tables
                WHERE table_schema = 'public' AND table_name = 'users'
            )
            """
        )
        if not cur.fetchone()[0]:
            return

        from db.passwords import hash_password, verify_password

        def add_or_repair(username: str, display_name: str, learner_level: str, plain: str = "prep2026") -> None:
            cur.execute(
                """
                SELECT id, password_hash FROM users WHERE LOWER(username) = LOWER(%s)
                """,
                (username,),
            )
            row = cur.fetchone()
            if row is None:
                h = hash_password(plain)
                cur.execute(
                    """
                    INSERT INTO users (username, password_hash, display_name, learner_level)
                    VALUES (%s, %s, %s, %s)
                    """,
                    (username, h, display_name, learner_level),
                )
                return
            uid, stored = row[0], row[1]
            if verify_password(plain, stored):
                return
            h = hash_password(plain)
            cur.execute(
                """
                UPDATE users
                SET password_hash = %s, display_name = %s, learner_level = %s
                WHERE id = %s
                """,
                (h, display_name, learner_level, uid),
            )

        add_or_repair("ashwika", "Ashwika", "sat")
        add_or_repair("thrishi", "Thrishi", "middle_school")
    conn.commit()
