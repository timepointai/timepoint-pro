"""
Unit Tests for SynthasAIzer Controls

Tests for the Moog-inspired control paradigm:
- ADSR envelopes for entity presence lifecycle
- Voice controls for entity mixing
- Event emission for monitoring
"""

import pytest
import time
from unittest.mock import MagicMock

from synth import (
    EnvelopeConfig,
    DEFAULT_ENVELOPE,
    VoiceConfig,
    VoiceMixer,
    DEFAULT_VOICE,
    SynthEvent,
    SynthEventData,
    SynthEventEmitter,
    logging_listener,
    console_listener,
    get_emitter,
    set_emitter,
)


class TestEnvelopeConfig:
    """Tests for ADSR envelope configuration."""

    def test_default_envelope_values(self):
        """Default envelope should have sensible ADSR values."""
        env = EnvelopeConfig()
        assert env.attack == 0.1
        assert env.decay == 0.2
        assert env.sustain == 0.8
        assert env.release == 0.3

    def test_custom_envelope_values(self):
        """Custom envelope values should be accepted."""
        env = EnvelopeConfig(attack=0.5, decay=0.3, sustain=0.6, release=0.4)
        assert env.attack == 0.5
        assert env.decay == 0.3
        assert env.sustain == 0.6
        assert env.release == 0.4

    def test_envelope_value_bounds(self):
        """Envelope values must be 0.0-1.0."""
        with pytest.raises(ValueError):
            EnvelopeConfig(attack=-0.1)
        with pytest.raises(ValueError):
            EnvelopeConfig(sustain=1.5)

    def test_intensity_at_start(self):
        """Intensity at start should be low (in attack phase)."""
        env = EnvelopeConfig(attack=0.5)
        intensity = env.intensity_at(0.0)
        # At progress 0, we're at the start of attack phase
        assert intensity >= 0.0
        assert intensity <= 0.5

    def test_intensity_at_peak(self):
        """Intensity should reach 1.0 at end of attack phase."""
        env = EnvelopeConfig(attack=0.4, decay=0.1, sustain=0.8, release=0.2)
        # At end of attack phase (0.4 * 0.25 = 0.1)
        intensity = env.intensity_at(0.1)
        assert intensity >= 0.95  # Should be near 1.0

    def test_intensity_at_sustain(self):
        """Intensity during sustain phase should be at sustain level."""
        env = EnvelopeConfig(attack=0.2, decay=0.2, sustain=0.7, release=0.2)
        # Middle of scenario should be in sustain phase
        intensity = env.intensity_at(0.5)
        assert intensity == 0.7

    def test_intensity_at_end(self):
        """Intensity at end should be near 0 (in release phase)."""
        env = EnvelopeConfig(attack=0.2, decay=0.2, sustain=0.7, release=0.5)
        # At progress 1.0, should be at end of release
        intensity = env.intensity_at(1.0)
        assert intensity <= 0.1  # Should be near 0

    def test_flat_envelope(self):
        """Zero attack/decay/release should give flat sustain."""
        env = EnvelopeConfig(attack=0.0, decay=0.0, sustain=0.5, release=0.0)
        # Should be sustain level throughout
        assert env.intensity_at(0.0) == 0.5
        assert env.intensity_at(0.5) == 0.5
        assert env.intensity_at(1.0) == 0.5

    def test_intensity_clamped(self):
        """Progress outside 0-1 should be clamped."""
        env = EnvelopeConfig()
        # Negative progress should be treated as 0
        assert env.intensity_at(-0.5) == env.intensity_at(0.0)
        # Progress > 1 should be treated as 1
        assert env.intensity_at(1.5) == env.intensity_at(1.0)

    def test_repr(self):
        """String representation should be readable."""
        env = EnvelopeConfig(attack=0.1, decay=0.2, sustain=0.8, release=0.3)
        assert "A=0.10" in repr(env)
        assert "D=0.20" in repr(env)
        assert "S=0.80" in repr(env)
        assert "R=0.30" in repr(env)

    def test_default_envelope_constant(self):
        """DEFAULT_ENVELOPE should be a valid envelope."""
        assert isinstance(DEFAULT_ENVELOPE, EnvelopeConfig)
        assert DEFAULT_ENVELOPE.sustain == 0.8


class TestVoiceConfig:
    """Tests for voice control configuration."""

    def test_default_voice_values(self):
        """Default voice should be unmuted, not solo, full gain."""
        voice = VoiceConfig()
        assert voice.mute is False
        assert voice.solo is False
        assert voice.gain == 1.0

    def test_muted_voice(self):
        """Muted voice should not be active."""
        voice = VoiceConfig(mute=True)
        assert voice.is_active() is False
        assert voice.effective_gain() == 0.0

    def test_solo_voice(self):
        """Solo'd voice should still be active."""
        voice = VoiceConfig(solo=True)
        assert voice.is_active() is True
        assert voice.effective_gain() == 1.0

    def test_gain_zero(self):
        """Zero gain voice should not be active."""
        voice = VoiceConfig(gain=0.0)
        assert voice.is_active() is False
        assert voice.effective_gain() == 0.0

    def test_partial_gain(self):
        """Partial gain should be reflected in effective_gain."""
        voice = VoiceConfig(gain=0.5)
        assert voice.is_active() is True
        assert voice.effective_gain() == 0.5

    def test_gain_bounds(self):
        """Gain must be 0.0-1.0."""
        with pytest.raises(ValueError):
            VoiceConfig(gain=-0.1)
        with pytest.raises(ValueError):
            VoiceConfig(gain=1.5)

    def test_repr_basic(self):
        """Basic voice repr should show gain."""
        voice = VoiceConfig(gain=0.5)
        assert "gain=0.50" in repr(voice)

    def test_repr_muted(self):
        """Muted voice should show MUTED in repr."""
        voice = VoiceConfig(mute=True)
        assert "MUTED" in repr(voice)

    def test_repr_solo(self):
        """Solo'd voice should show SOLO in repr."""
        voice = VoiceConfig(solo=True)
        assert "SOLO" in repr(voice)

    def test_default_voice_constant(self):
        """DEFAULT_VOICE should be a valid voice with full participation."""
        assert isinstance(DEFAULT_VOICE, VoiceConfig)
        assert DEFAULT_VOICE.is_active() is True
        assert DEFAULT_VOICE.effective_gain() == 1.0


class TestVoiceMixer:
    """Tests for voice mixer managing multiple entities."""

    def test_empty_mixer(self):
        """Empty mixer should use default voice for all entities."""
        mixer = VoiceMixer()
        voice = mixer.get_voice("any_entity")
        assert voice.gain == 1.0
        assert voice.mute is False

    def test_set_and_get_voice(self):
        """Should be able to set and retrieve voice for entity."""
        mixer = VoiceMixer()
        mixer.set_voice("entity_1", VoiceConfig(gain=0.5))
        assert mixer.get_voice("entity_1").gain == 0.5
        assert mixer.get_voice("entity_2").gain == 1.0  # Default

    def test_get_active_entity_ids_no_mutes(self):
        """All entities should be active if none are muted."""
        mixer = VoiceMixer()
        entities = ["a", "b", "c"]
        active = mixer.get_active_entity_ids(entities)
        assert active == entities

    def test_get_active_entity_ids_with_mute(self):
        """Muted entities should be filtered out."""
        mixer = VoiceMixer()
        mixer.set_voice("b", VoiceConfig(mute=True))
        entities = ["a", "b", "c"]
        active = mixer.get_active_entity_ids(entities)
        assert "b" not in active
        assert "a" in active
        assert "c" in active

    def test_get_active_entity_ids_with_solo(self):
        """When any entity is solo'd, only solo'd entities should be active."""
        mixer = VoiceMixer()
        mixer.set_voice("b", VoiceConfig(solo=True))
        entities = ["a", "b", "c"]
        active = mixer.get_active_entity_ids(entities)
        assert active == ["b"]

    def test_get_active_entity_ids_multiple_solos(self):
        """Multiple solo'd entities should all be active."""
        mixer = VoiceMixer()
        mixer.set_voice("a", VoiceConfig(solo=True))
        mixer.set_voice("c", VoiceConfig(solo=True))
        entities = ["a", "b", "c"]
        active = mixer.get_active_entity_ids(entities)
        assert set(active) == {"a", "c"}

    def test_get_entity_weight(self):
        """Should return effective gain for entity."""
        mixer = VoiceMixer()
        mixer.set_voice("a", VoiceConfig(gain=0.3))
        mixer.set_voice("b", VoiceConfig(mute=True))
        assert mixer.get_entity_weight("a") == 0.3
        assert mixer.get_entity_weight("b") == 0.0  # Muted
        assert mixer.get_entity_weight("c") == 1.0  # Default

    def test_has_solo(self):
        """Should detect when any voice is solo'd."""
        mixer = VoiceMixer()
        assert mixer.has_solo() is False
        mixer.set_voice("a", VoiceConfig(solo=True))
        assert mixer.has_solo() is True

    def test_clear(self):
        """Clear should reset all voices."""
        mixer = VoiceMixer()
        mixer.set_voice("a", VoiceConfig(gain=0.5))
        mixer.clear()
        assert mixer.get_voice("a").gain == 1.0  # Back to default


class TestSynthEvent:
    """Tests for event types."""

    def test_event_types_exist(self):
        """All expected event types should exist."""
        assert SynthEvent.RUN_START.value == "run_start"
        assert SynthEvent.RUN_COMPLETE.value == "run_complete"
        assert SynthEvent.ENTITY_CREATED.value == "entity_created"
        assert SynthEvent.TIMEPOINT_START.value == "timepoint_start"
        assert SynthEvent.DIALOG_TURN.value == "dialog_turn"


class TestSynthEventData:
    """Tests for event data structure."""

    def test_event_data_creation(self):
        """Should be able to create event data."""
        event = SynthEventData(
            event_type=SynthEvent.RUN_START,
            timestamp=1234567890.0,
            run_id="run_123",
            data={"template": "board_meeting"}
        )
        assert event.event_type == SynthEvent.RUN_START
        assert event.run_id == "run_123"
        assert event.data["template"] == "board_meeting"

    def test_to_dict(self):
        """Event data should serialize to dict."""
        event = SynthEventData(
            event_type=SynthEvent.RUN_START,
            timestamp=1234567890.0,
            run_id="run_123",
            data={"key": "value"}
        )
        d = event.to_dict()
        assert d["event"] == "run_start"
        assert d["run_id"] == "run_123"
        assert d["data"]["key"] == "value"

    def test_from_dict(self):
        """Should be able to deserialize from dict."""
        d = {
            "event": "run_complete",
            "timestamp": 1234567890.0,
            "run_id": "run_456",
            "data": {"success": True}
        }
        event = SynthEventData.from_dict(d)
        assert event.event_type == SynthEvent.RUN_COMPLETE
        assert event.run_id == "run_456"
        assert event.data["success"] is True


class TestSynthEventEmitter:
    """Tests for event emission system."""

    def test_emitter_disabled_by_default(self):
        """Emitter should be disabled by default (backward compat)."""
        emitter = SynthEventEmitter()
        assert emitter.enabled is False

    def test_disabled_emitter_doesnt_emit(self):
        """Disabled emitter should not call listeners."""
        emitter = SynthEventEmitter(enabled=False)
        listener = MagicMock()
        emitter.add_listener(listener)
        emitter.emit(SynthEvent.RUN_START, "run_123")
        listener.assert_not_called()

    def test_enabled_emitter_emits(self):
        """Enabled emitter should call listeners."""
        emitter = SynthEventEmitter(enabled=True)
        listener = MagicMock()
        emitter.add_listener(listener)
        emitter.emit(SynthEvent.RUN_START, "run_123", {"template": "test"})
        listener.assert_called_once()
        event = listener.call_args[0][0]
        assert event.event_type == SynthEvent.RUN_START
        assert event.run_id == "run_123"
        assert event.data["template"] == "test"

    def test_multiple_listeners(self):
        """All listeners should be called."""
        emitter = SynthEventEmitter(enabled=True)
        listener1 = MagicMock()
        listener2 = MagicMock()
        emitter.add_listener(listener1)
        emitter.add_listener(listener2)
        emitter.emit(SynthEvent.RUN_START, "run_123")
        listener1.assert_called_once()
        listener2.assert_called_once()

    def test_add_listener_deduplicates(self):
        """Same listener shouldn't be added twice."""
        emitter = SynthEventEmitter(enabled=True)
        listener = MagicMock()
        emitter.add_listener(listener)
        emitter.add_listener(listener)  # Duplicate
        emitter.emit(SynthEvent.RUN_START, "run_123")
        assert listener.call_count == 1

    def test_remove_listener(self):
        """Removed listener should not be called."""
        emitter = SynthEventEmitter(enabled=True)
        listener = MagicMock()
        emitter.add_listener(listener)
        emitter.remove_listener(listener)
        emitter.emit(SynthEvent.RUN_START, "run_123")
        listener.assert_not_called()

    def test_listener_error_doesnt_break_workflow(self):
        """Listener errors should be caught, not propagated."""
        emitter = SynthEventEmitter(enabled=True)
        bad_listener = MagicMock(side_effect=Exception("Oops"))
        good_listener = MagicMock()
        emitter.add_listener(bad_listener)
        emitter.add_listener(good_listener)
        # Should not raise
        emitter.emit(SynthEvent.RUN_START, "run_123")
        # Good listener should still be called
        good_listener.assert_called_once()

    def test_event_history(self):
        """Emitter should maintain event history."""
        emitter = SynthEventEmitter(enabled=True)
        emitter.emit(SynthEvent.RUN_START, "run_1")
        emitter.emit(SynthEvent.ENTITY_CREATED, "run_1")
        emitter.emit(SynthEvent.RUN_COMPLETE, "run_1")
        history = emitter.get_history()
        assert len(history) == 3
        assert history[0].event_type == SynthEvent.RUN_START
        assert history[2].event_type == SynthEvent.RUN_COMPLETE

    def test_event_history_filter(self):
        """History should be filterable by event type."""
        emitter = SynthEventEmitter(enabled=True)
        emitter.emit(SynthEvent.RUN_START, "run_1")
        emitter.emit(SynthEvent.ENTITY_CREATED, "run_1")
        emitter.emit(SynthEvent.ENTITY_CREATED, "run_1")
        emitter.emit(SynthEvent.RUN_COMPLETE, "run_1")
        entity_events = emitter.get_history(SynthEvent.ENTITY_CREATED)
        assert len(entity_events) == 2

    def test_clear_history(self):
        """Clear should empty history."""
        emitter = SynthEventEmitter(enabled=True)
        emitter.emit(SynthEvent.RUN_START, "run_1")
        emitter.clear_history()
        assert len(emitter.get_history()) == 0

    def test_history_size_limit(self):
        """History should not grow unbounded."""
        emitter = SynthEventEmitter(enabled=True)
        emitter._max_history = 10  # Lower limit for testing
        for i in range(20):
            emitter.emit(SynthEvent.DIALOG_TURN, "run_1", {"turn": i})
        assert len(emitter.get_history()) == 10

    def test_enable_disable(self):
        """Should be able to enable/disable emitter."""
        emitter = SynthEventEmitter(enabled=False)
        emitter.enable()
        assert emitter.enabled is True
        emitter.disable()
        assert emitter.enabled is False


class TestGlobalEmitter:
    """Tests for global emitter functions."""

    def test_get_emitter_creates_one(self):
        """get_emitter should create a default emitter."""
        # Reset global state
        set_emitter(None)
        emitter = get_emitter()
        assert isinstance(emitter, SynthEventEmitter)
        assert emitter.enabled is False  # Default disabled

    def test_set_emitter(self):
        """set_emitter should replace the global emitter."""
        custom_emitter = SynthEventEmitter(enabled=True)
        set_emitter(custom_emitter)
        assert get_emitter() is custom_emitter


class TestConfigSchemaIntegration:
    """Tests for synth integration with config_schema."""

    def test_entity_config_default_envelope(self):
        """EntityConfig should have optional envelope with default."""
        from generation.config_schema import EntityConfig
        config = EntityConfig(count=5)
        assert config.envelope is None
        envelope = config.get_envelope()
        assert isinstance(envelope, EnvelopeConfig)
        assert envelope.sustain == 0.8  # Default

    def test_entity_config_custom_envelope(self):
        """EntityConfig should accept custom envelope."""
        from generation.config_schema import EntityConfig
        config = EntityConfig(
            count=5,
            envelope=EnvelopeConfig(attack=0.5, sustain=0.9)
        )
        assert config.envelope.attack == 0.5
        assert config.envelope.sustain == 0.9

    def test_entity_config_default_voice(self):
        """EntityConfig should have optional default_voice with default."""
        from generation.config_schema import EntityConfig
        config = EntityConfig(count=5)
        assert config.default_voice is None
        voice = config.get_default_voice()
        assert isinstance(voice, VoiceConfig)
        assert voice.gain == 1.0

    def test_entity_config_custom_voice(self):
        """EntityConfig should accept custom default_voice."""
        from generation.config_schema import EntityConfig
        config = EntityConfig(
            count=5,
            default_voice=VoiceConfig(gain=0.5)
        )
        assert config.default_voice.gain == 0.5

    def test_backward_compatibility(self):
        """Existing configs without synth fields should still work."""
        from generation.config_schema import EntityConfig
        # Old-style config without synth fields
        config = EntityConfig(count=3, types=["human"])
        # Should not raise, should have defaults
        assert config.get_envelope() is not None
        assert config.get_default_voice() is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
