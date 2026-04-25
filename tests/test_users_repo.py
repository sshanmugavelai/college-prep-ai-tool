from db.users_repo import _normalize_learner_level


def test_normalize_learner_level_prefers_explicit_middle_school():
    assert _normalize_learner_level("middle_school", email="student@example.com") == "middle_school"


def test_normalize_learner_level_prefers_explicit_sat():
    assert _normalize_learner_level("sat", email="student@example.com") == "sat"

