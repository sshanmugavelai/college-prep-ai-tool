from contextlib import contextmanager

import psycopg

from utils.config import get_database_url

# Existing DBs may predate newer columns; apply once per process on first connection.
_SCHEMA_PATCHED = False


def _apply_schema_patches_once(conn) -> None:
    global _SCHEMA_PATCHED
    if not _SCHEMA_PATCHED:
        from db.migrate_family_users import run_family_migrations

        run_family_migrations(conn)

        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT EXISTS (
                    SELECT 1 FROM information_schema.tables
                    WHERE table_schema = 'public' AND table_name = 'attempts'
                )
                """
            )
            if cur.fetchone()[0]:
                cur.execute(
                    """
                    ALTER TABLE attempts
                    ADD COLUMN IF NOT EXISTS practice_mode BOOLEAN NOT NULL DEFAULT FALSE
                    """
                )

            cur.execute(
                """
                SELECT EXISTS (
                    SELECT 1 FROM information_schema.tables
                    WHERE table_schema = 'public' AND table_name = 'tests'
                )
                """
            )
            if cur.fetchone()[0]:
                cur.execute(
                    """
                    DO $patch$
                    DECLARE
                      cname text;
                    BEGIN
                      SELECT c.conname INTO cname
                      FROM pg_constraint c
                      JOIN pg_class t ON c.conrelid = t.oid
                      WHERE t.relname = 'tests'
                        AND c.contype = 'c'
                        AND pg_get_constraintdef(c.oid) LIKE '%exam_type%'
                      LIMIT 1;
                      IF cname IS NOT NULL THEN
                        EXECUTE format('ALTER TABLE tests DROP CONSTRAINT %I', cname);
                      END IF;
                    END
                    $patch$;
                    """
                )
                cur.execute(
                    """
                    ALTER TABLE tests ADD CONSTRAINT tests_exam_type_check
                    CHECK (exam_type IN ('SAT', 'ACT', 'Middle school'))
                    """
                )
        conn.commit()
        _SCHEMA_PATCHED = True

    # Every connection: long-lived Streamlit skips the block above after the first
    # open, but seed users must still be ensured (otherwise login fails forever).
    from db.migrate_family_users import ensure_family_seed_users

    ensure_family_seed_users(conn)


@contextmanager
def get_conn():
    url = get_database_url()
    if not url:
        raise RuntimeError(
            "DATABASE_URL is not set. For local development add it to a .env file; "
            "on Streamlit Community Cloud add DATABASE_URL under App settings → Secrets."
        )
    # Neon pooler (PgBouncer) + server-side prepared statements can break queries; disable prep.
    connect_kw = {}
    if "neon.tech" in url.lower() or "pooler" in url.lower():
        connect_kw["prepare_threshold"] = None

    with psycopg.connect(url, **connect_kw) as conn:
        _apply_schema_patches_once(conn)
        yield conn
