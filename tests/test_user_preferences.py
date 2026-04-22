from db.repository import UserPreferences
from db.repository import _default_user_preferences


def test_default_preferences_middle_school():
    prefs = _default_user_preferences(learner_level="middle_school")
    assert isinstance(prefs, UserPreferences)
    assert prefs.preferred_exam_type == "Middle school"
    assert prefs.preferred_starr_mode is True
    assert prefs.preferred_section == "Math"


def test_default_preferences_sat():
    prefs = _default_user_preferences(learner_level="sat")
    assert isinstance(prefs, UserPreferences)
    assert prefs.preferred_exam_type == "SAT"
    assert prefs.preferred_starr_mode is False
    assert prefs.preferred_difficulty == "medium"
