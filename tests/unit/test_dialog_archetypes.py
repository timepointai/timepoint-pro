"""
Tests for Phase 4: Dialog Archetypes - Rhetorical profile lookup and structure.
"""
import pytest
from workflows.dialog_archetypes import (
    ARCHETYPE_RHETORICAL_PROFILES,
    get_rhetorical_profile,
)


REQUIRED_PROFILE_KEYS = {
    "argument_style",
    "disagreement_pattern",
    "deflection_style",
    "sentence_style",
    "never_does",
    "signature_moves",
}


class TestArchetypeProfiles:
    """Test the static archetype profile data."""

    def test_all_archetypes_have_required_keys(self):
        for archetype_id, profile in ARCHETYPE_RHETORICAL_PROFILES.items():
            missing = REQUIRED_PROFILE_KEYS - set(profile.keys())
            assert not missing, f"Archetype '{archetype_id}' missing keys: {missing}"

    def test_never_does_is_list_of_strings(self):
        for archetype_id, profile in ARCHETYPE_RHETORICAL_PROFILES.items():
            never_does = profile["never_does"]
            assert isinstance(never_does, list), f"{archetype_id}.never_does should be list"
            for item in never_does:
                assert isinstance(item, str), f"{archetype_id}.never_does items should be str"

    def test_signature_moves_is_list_of_strings(self):
        for archetype_id, profile in ARCHETYPE_RHETORICAL_PROFILES.items():
            sig = profile["signature_moves"]
            assert isinstance(sig, list), f"{archetype_id}.signature_moves should be list"
            for item in sig:
                assert isinstance(item, str)

    def test_string_fields_are_nonempty(self):
        for archetype_id, profile in ARCHETYPE_RHETORICAL_PROFILES.items():
            for key in ("argument_style", "disagreement_pattern", "deflection_style", "sentence_style"):
                assert isinstance(profile[key], str) and len(profile[key]) > 5, (
                    f"{archetype_id}.{key} should be a non-empty descriptive string"
                )

    def test_minimum_archetype_count(self):
        assert len(ARCHETYPE_RHETORICAL_PROFILES) >= 5, "Should have at least 5 archetypes"

    def test_known_archetypes_present(self):
        expected = {"engineer", "executive_director", "military_commander", "scientist"}
        actual = set(ARCHETYPE_RHETORICAL_PROFILES.keys())
        assert expected.issubset(actual), f"Missing expected archetypes: {expected - actual}"


class TestGetRhetoricalProfile:
    """Test the get_rhetorical_profile lookup function."""

    def test_known_archetype_returns_profile(self):
        profile = get_rhetorical_profile("engineer")
        assert profile != {}
        assert "argument_style" in profile

    def test_unknown_archetype_returns_empty_dict(self):
        profile = get_rhetorical_profile("nonexistent_type")
        assert profile == {}

    def test_empty_string_returns_empty_dict(self):
        assert get_rhetorical_profile("") == {}

    def test_returned_profile_has_all_keys(self):
        for archetype_id in ARCHETYPE_RHETORICAL_PROFILES:
            profile = get_rhetorical_profile(archetype_id)
            assert set(profile.keys()) == REQUIRED_PROFILE_KEYS

    def test_engineer_specific_content(self):
        profile = get_rhetorical_profile("engineer")
        assert "data" in profile["argument_style"].lower()
        assert "emotional appeals" in [nd.lower() for nd in profile["never_does"]] or \
               any("emotional" in nd.lower() for nd in profile["never_does"])

    def test_executive_director_specific_content(self):
        profile = get_rhetorical_profile("executive_director")
        assert "budget" in profile["argument_style"].lower() or "schedule" in profile["argument_style"].lower()
