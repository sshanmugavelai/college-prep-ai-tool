from utils.config import _read_csv_emails


def test_read_csv_emails_normalizes_and_dedupes(monkeypatch):
    monkeypatch.setenv("ADMIN_EMAILS", " A@EXAMPLE.com, b@example.com ,a@example.com ")
    out = _read_csv_emails("ADMIN_EMAILS")
    assert out == {"a@example.com", "b@example.com"}
