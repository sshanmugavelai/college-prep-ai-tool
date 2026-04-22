from types import SimpleNamespace

import utils.session as session


class _FakeSessionState(dict):
    def __getattr__(self, name):
        if name in self:
            return self[name]
        raise AttributeError(name)

    def __setattr__(self, name, value):
        self[name] = value


def test_set_authenticated_user_session_contract():
    fake_st = SimpleNamespace(session_state=_FakeSessionState())
    original_st = session.st
    try:
        session.st = fake_st
        session.set_authenticated_user_session(
            user_id=123,
            username="kid@example.com",
            display_name="Kid",
            learner_level="sat",
            email="kid@example.com",
            is_admin=True,
        )
        assert fake_st.session_state["user_id"] == 123
        assert fake_st.session_state["username"] == "kid@example.com"
        assert fake_st.session_state["display_name"] == "Kid"
        assert fake_st.session_state["learner_level"] == "sat"
        assert fake_st.session_state["email"] == "kid@example.com"
        assert fake_st.session_state["is_admin"] is True
    finally:
        session.st = original_st
