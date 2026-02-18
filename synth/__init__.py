"""
SynthasAIzer: A Control Paradigm for Timepoint-Pro

Moog-inspired control layer for simulation configuration.
See SYNTH.md for full specification.

This module provides:
- ADSR envelopes for entity presence lifecycle
- Voice controls for entity mixing (mute/solo/gain)
- Event emission for monitoring and visualization

All features are:
- Optional (backward compatible)
- MVP-scoped (minimal code)
- Fully tested (unit + E2E)
- Metaphor-appropriate (no DSP, just UI patterns)

Example:
    from synth import EnvelopeConfig, VoiceConfig, SynthEventEmitter

    # Create an envelope for dramatic buildup
    envelope = EnvelopeConfig(
        attack=0.3,   # Slow buildup
        decay=0.1,    # Quick peak
        sustain=0.9,  # High intensity
        release=0.5   # Gradual resolution
    )

    # Get intensity at 50% through scenario
    intensity = envelope.intensity_at(0.5, total_timepoints=10)

    # Voice controls for entity mixing
    voice = VoiceConfig(gain=0.5)  # Background entity at 50%

    # Event monitoring
    emitter = SynthEventEmitter(enabled=True)
    emitter.emit(SynthEvent.RUN_START, "run_123", {"template": "board_meeting"})
"""

from synth.envelope import EnvelopeConfig, DEFAULT_ENVELOPE
from synth.voice import VoiceConfig, VoiceMixer, DEFAULT_VOICE
from synth.fidelity_envelope import ADPRSEnvelope, ADPRSComposite, FidelityBand, phi_to_resolution_band
from synth.shadow_evaluator import ShadowEvaluator, ShadowEvaluationReport
from synth.trajectory_tracker import TrajectoryTracker, CognitiveSnapshot
from synth.adprs_fitter import ADPRSFitter, FitResult, adprs_waveform
from synth.harmonic_fitter import HarmonicFitter, HarmonicFitResult, harmonic_adprs_waveform
from synth.waveform_scheduler import WaveformScheduler
from synth.events import (
    SynthEvent,
    SynthEventData,
    SynthEventEmitter,
    EventListener,
    logging_listener,
    console_listener,
    get_emitter,
    set_emitter,
)

__all__ = [
    # Envelope
    "EnvelopeConfig",
    "DEFAULT_ENVELOPE",
    # Voice
    "VoiceConfig",
    "VoiceMixer",
    "DEFAULT_VOICE",
    # Fidelity Envelopes (ADPRS)
    "ADPRSEnvelope",
    "ADPRSComposite",
    "FidelityBand",
    "phi_to_resolution_band",
    # Shadow Evaluator
    "ShadowEvaluator",
    "ShadowEvaluationReport",
    # Trajectory Tracker (Phase 2)
    "TrajectoryTracker",
    "CognitiveSnapshot",
    # ADPRS Fitter (Phase 2)
    "ADPRSFitter",
    "FitResult",
    "adprs_waveform",
    # Harmonic Fitter (Phase 2.5)
    "HarmonicFitter",
    "HarmonicFitResult",
    "harmonic_adprs_waveform",
    # Waveform Scheduler (Phase 3)
    "WaveformScheduler",
    # Events
    "SynthEvent",
    "SynthEventData",
    "SynthEventEmitter",
    "EventListener",
    "logging_listener",
    "console_listener",
    "get_emitter",
    "set_emitter",
]

__version__ = "1.0.0"
