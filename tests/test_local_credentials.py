from db.passwords import hash_password
from db.users_repo import authenticate_local_credentials


def test_authenticate_local_credentials_valid(monkeypatch):
    class _FakeCursor:
        def __init__(self):
            self._row = {
                "id": 1,
                "username": "admin",
                "display_name": "Administrator",
                "learner_level": "sat",
                "password_hash": hash_password("admin@1234"),
            }

        def execute(self, *_args, **_kwargs):
            return None

        def fetchone(self):
            return self._row

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

    class _FakeConn:
        def cursor(self, **_kwargs):
            return _FakeCursor()

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

    class _FakeConnCtx:
        def __enter__(self):
            return _FakeConn()

        def __exit__(self, *_args):
            return False

    monkeypatch.setattr("db.users_repo.get_conn", lambda: _FakeConnCtx())
    monkeypatch.setattr("db.users_repo.ensure_family_seed_users", lambda _conn: None)

    row = authenticate_local_credentials(username="admin", password="admin@1234")
    assert row is not None
    assert row["username"] == "admin"


def test_authenticate_local_credentials_invalid_password(monkeypatch):
    class _FakeCursor:
        def __init__(self):
            self._row = {
                "id": 1,
                "username": "admin",
                "display_name": "Administrator",
                "learner_level": "sat",
                "password_hash": hash_password("different"),
            }

        def execute(self, *_args, **_kwargs):
            return None

        def fetchone(self):
            return self._row

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

    class _FakeConn:
        def cursor(self, **_kwargs):
            return _FakeCursor()

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

    class _FakeConnCtx:
        def __enter__(self):
            return _FakeConn()

        def __exit__(self, *_args):
            return False

    monkeypatch.setattr("db.users_repo.get_conn", lambda: _FakeConnCtx())
    monkeypatch.setattr("db.users_repo.ensure_family_seed_users", lambda _conn: None)

    row = authenticate_local_credentials(username="admin", password="wrong")
    assert row is None
