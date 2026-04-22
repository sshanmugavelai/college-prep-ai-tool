"""Remove all generated tests, attempts, and related rows (keeps ``users``)."""


def truncate_all_practice_data(conn) -> None:
    """Empty practice tables and reset sequences. Safe to call on Neon."""
    with conn.cursor() as cur:
        cur.execute(
            """
            TRUNCATE TABLE
                answers,
                mistake_journal,
                progress,
                attempts,
                questions,
                tests
            RESTART IDENTITY CASCADE
            """
        )
    conn.commit()
