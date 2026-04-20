from pathlib import Path

from db.connection import get_conn


def init_db() -> None:
    """Create tables from schema.sql against the database in ``DATABASE_URL`` (e.g. Neon).

    Column patches (e.g. ``practice_mode``) run automatically inside ``get_conn()`` on first connect.
    """
    schema_path = Path(__file__).resolve().parent / "schema.sql"
    schema_sql = schema_path.read_text()
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(schema_sql)
        conn.commit()

