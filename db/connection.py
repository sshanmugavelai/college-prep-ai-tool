import os
from contextlib import contextmanager

from dotenv import load_dotenv
import psycopg


load_dotenv()


DATABASE_URL = os.getenv("DATABASE_URL", "")

if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL is not set. Add it to your .env file.")


@contextmanager
def get_conn():
    with psycopg.connect(DATABASE_URL) as conn:
        yield conn
