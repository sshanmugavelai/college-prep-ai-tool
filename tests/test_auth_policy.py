from auth.policy import evaluate_user_policy


def test_policy_non_admin_is_fail_closed(monkeypatch):
    monkeypatch.setattr("auth.policy.get_admin_emails", lambda: {"admin@example.com"})
    policy = evaluate_user_policy(email="student@example.com")
    assert policy.is_admin is False
    assert policy.can_view_admin_tools is False
    assert policy.can_initialize_db is False
    assert policy.can_clear_cache is False


def test_policy_admin_gets_admin_controls(monkeypatch):
    monkeypatch.setattr("auth.policy.get_admin_emails", lambda: {"admin@example.com"})
    policy = evaluate_user_policy(email="ADMIN@example.com")
    assert policy.is_admin is True
    assert policy.can_view_admin_tools is True
    assert policy.can_initialize_db is True
    assert policy.can_clear_cache is True
