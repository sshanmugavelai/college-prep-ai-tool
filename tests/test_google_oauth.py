from auth.google_oauth import GoogleOAuthConfig, GoogleOAuthService


def test_google_service_requires_core_config():
    service = GoogleOAuthService(
        config=GoogleOAuthConfig(
            client_id="",
            client_secret="x",
            redirect_uri="https://example.com/callback",
            authorize_url="https://accounts.google.com/o/oauth2/v2/auth",
            token_url="https://oauth2.googleapis.com/token",
            userinfo_url="https://openidconnect.googleapis.com/v1/userinfo",
        )
    )
    assert service.is_configured() is False


def test_google_service_builds_authorize_url_with_state():
    service = GoogleOAuthService(
        config=GoogleOAuthConfig(
            client_id="cid",
            client_secret="secret",
            redirect_uri="https://example.com/callback",
            authorize_url="https://accounts.google.com/o/oauth2/v2/auth",
            token_url="https://oauth2.googleapis.com/token",
            userinfo_url="https://openidconnect.googleapis.com/v1/userinfo",
        )
    )
    url = service.build_authorize_url("state123")
    assert "client_id=cid" in url
    assert "state=state123" in url
    assert "response_type=code" in url


def test_google_state_token_validates_without_session_copy():
    service = GoogleOAuthService(
        config=GoogleOAuthConfig(
            client_id="cid",
            client_secret="secret",
            redirect_uri="https://example.com/callback",
            authorize_url="https://accounts.google.com/o/oauth2/v2/auth",
            token_url="https://oauth2.googleapis.com/token",
            userinfo_url="https://openidconnect.googleapis.com/v1/userinfo",
        )
    )
    state = service.create_state()
    service._validate_state_token(state)
    assert service.get_learner_level_from_state(state) == "sat"


def test_google_state_token_carries_middle_school_selection():
    service = GoogleOAuthService(
        config=GoogleOAuthConfig(
            client_id="cid",
            client_secret="secret",
            redirect_uri="https://example.com/callback",
            authorize_url="https://accounts.google.com/o/oauth2/v2/auth",
            token_url="https://oauth2.googleapis.com/token",
            userinfo_url="https://openidconnect.googleapis.com/v1/userinfo",
        )
    )
    state = service.create_state(learner_level="middle_school")
    assert service.get_learner_level_from_state(state) == "middle_school"


def test_google_state_mismatch_fails_closed():
    service = GoogleOAuthService(
        config=GoogleOAuthConfig(
            client_id="cid",
            client_secret="secret",
            redirect_uri="https://example.com/callback",
            authorize_url="https://accounts.google.com/o/oauth2/v2/auth",
            token_url="https://oauth2.googleapis.com/token",
            userinfo_url="https://openidconnect.googleapis.com/v1/userinfo",
        )
    )
    try:
        service.exchange_code_for_identity(code="abc", state="wrong", expected_state="expected")
        assert False, "Expected ValueError for OAuth state mismatch"
    except ValueError as exc:
        assert "state mismatch" in str(exc).lower()


def test_google_state_signature_tamper_fails_closed():
    service = GoogleOAuthService(
        config=GoogleOAuthConfig(
            client_id="cid",
            client_secret="secret",
            redirect_uri="https://example.com/callback",
            authorize_url="https://accounts.google.com/o/oauth2/v2/auth",
            token_url="https://oauth2.googleapis.com/token",
            userinfo_url="https://openidconnect.googleapis.com/v1/userinfo",
        )
    )
    state = service.create_state()
    tampered = f"{state}x"
    try:
        service._validate_state_token(tampered)
        assert False, "Expected ValueError for tampered OAuth state"
    except ValueError as exc:
        assert "state mismatch" in str(exc).lower()


def test_google_create_state_not_empty():
    service = GoogleOAuthService(
        config=GoogleOAuthConfig(
            client_id="cid",
            client_secret="secret",
            redirect_uri="https://example.com/callback",
            authorize_url="https://accounts.google.com/o/oauth2/v2/auth",
            token_url="https://oauth2.googleapis.com/token",
            userinfo_url="https://openidconnect.googleapis.com/v1/userinfo",
        )
    )
    state = service.create_state()
    assert isinstance(state, str)
    assert len(state) >= 16
