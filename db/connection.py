from contextlib import contextmanager

import psycopg

from utils.config import get_database_url

# Existing DBs may predate newer columns; apply once per process on first connection.
_SCHEMA_PATCHED = False


def _apply_schema_patches_once(conn) -> None:
    global _SCHEMA_PATCHED
    if _SCHEMA_PATCHED:
        return
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT EXISTS (
                SELECT 1 FROM information_schema.tables
                WHERE table_schema = 'public' AND table_name = 'attempts'
            )
            """
        )
        if not cur.fetchone()[0]:
            # init_db has not created tables yet; retry on a later connection.
            return
        cur.execute(
            """
            ALTER TABLE attempts
            ADD COLUMN IF NOT EXISTS practice_mode BOOLEAN NOT NULL DEFAULT FALSE
            """
        )
    conn.commit()
    _SCHEMA_PATCHED = True


@contextmanager
def get_conn():
    url = get_database_url()
    if not url:
        raise RuntimeError(
            "DATABASE_URL is not set. For local development add it to a .env file; "
            "on Streamlit Community Cloud add DATABASE_URL under App settings → Secrets."
        )
    with psycopg.connect(url) as conn:
        _apply_schema_patches_once(conn)
        yield conn
