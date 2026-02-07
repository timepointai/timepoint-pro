# SynthasAIzer: A Control Paradigm for Timepoint-Daedalus

**Version**: 1.0
**Status**: Phase 1-3 Implemented, Phase 4 Planned
**Inspired by**: Moog synthesizers, modular synthesis UI/UX patterns

---

## Implementation Status (January 2026)

| Phase | Feature | Status | Tests |
|-------|---------|--------|-------|
| **Phase 1** | ADSR Envelopes | **COMPLETE** | 53 unit tests |
| **Phase 2** | Voice Controls | **COMPLETE** | Integrated |
| **Phase 3** | Patch System | **COMPLETE** | 15 templates with patch metadata |
| **Phase 4** | Event Monitoring | Specification | - |

### What's Implemented

**`synth/` module** (`synth/__init__.py`, `envelope.py`, `voice.py`, `events.py`):
```python
from synth import EnvelopeConfig, VoiceConfig, SynthEventEmitter, SynthEvent

# ADSR envelope for entity presence lifecycle
envelope = EnvelopeConfig(attack=0.2, decay=0.1, sustain=0.8, release=0.3)
intensity = envelope.intensity_at(progress=0.5, total_timepoints=10)

# Voice controls for entity mixing
voice = VoiceConfig(mute=False, solo=False, gain=1.0)

# Event emission (ready for Phase 4)
emitter = SynthEventEmitter(enabled=True)
emitter.emit(SynthEvent.RUN_START, "run_123", {"template": "board_meeting"})
```

**Patch System** (`generation/templates/loader.py`):
- `TemplateLoader` with `get_all_patches()`, `list_patch_categories()`
- `PatchInfo` dataclass with name, category, tags, author, version, description
- 9 patch categories: corporate, historical, crisis, mystical, mystery, directorial, portal, space, scifi, convergence
- 15 JSON templates with patch metadata in `generation/templates/`

**Template Organization**:
- `generation/templates/showcase/` - 12 showcase scenarios (including `castaway_colony_branching` — full 19-mechanism showcase)
- `generation/templates/convergence/` - 3 convergence-optimized templates

---

## Philosophy

Timepoint-Daedalus and analog synthesizers solve the same fundamental problem: **steering complex, concurrent, time-evolving systems through intuitive controls**.

This document specifies the "SynthasAIzer" paradigm—a control layer that borrows synthesizer interface patterns without claiming mathematical equivalence. We use the metaphor where it fits naturally and stop where it would require forcing.

### What Fits (Use These)

| Synth Concept | Timepoint Equivalent | Why It Fits |
|---------------|---------------------|-------------|
| **ADSR Envelope** | Entity presence lifecycle | Entities DO have attack (introduction), decay (settling), sustain (participation), release (exit) |
| **Voice** | Entity instance | Each entity is an independent "voice" in the simulation |
| **Gain** | Entity importance weight | Some entities matter more than others in a scene |
| **Mute/Solo** | Entity exclusion/focus | Standard mixing board controls for attention |
| **Patch** | Template preset | Templates ARE presets—saved configurations |
| **LFO** | Circadian modulation (M14) | Already exists—time-based parameter modulation |
| **Sequencer Grid** | Timepoint array | Discrete time steps, exactly like a step sequencer |

### What Doesn't Fit (Don't Use These)

| Synth Concept | Why It Doesn't Fit |
|---------------|-------------------|
| Filter cutoff | Resolution is discrete (5 levels), not continuous |
| Oscillator waveform | No mathematical basis for entity "wave shape" |
| Frequency/pitch | Entities don't have frequency |
| Modulation matrix | Over-engineering for current needs |
| MIDI | Unnecessary protocol complexity |
| Polyphony limits | Entity count is scenario-driven, not hardware-limited |
| Audio output | We produce data, not sound |

### The Moog Inspiration

Moog synthesizers succeeded because they made complex signal routing **tangible**. Patch cables, knobs with clear labels, visual feedback. We adopt this sensibility:

- **Explicit over implicit**: Show the user what's happening
- **Defaults that work**: Unset parameters produce good results
- **Composable**: Small controls combine into complex behaviors
- **Reversible**: Easy to undo, experiment, iterate

### Why This Metaphor Works

The synthesizer analogy isn't just aesthetic—it captures something structural about temporal simulation:

1. **Time as a sequencer grid**: Timepoints are discrete steps, exactly like a 16-step sequencer. Each step has state, each transition has rules.

2. **Entities as polyphonic voices**: Multiple entities running simultaneously, each with their own presence envelope, each contributing to the overall "mix" of the scene.

3. **Resolution as gain staging**: Just as audio gain determines how loud a signal is in the mix, entity resolution determines how much computational attention they receive. A muted entity still exists—it just doesn't dominate the output.

4. **Templates as patches**: A patch on a Moog is a saved configuration of knobs and cables. Our JSON templates are exactly this—reproducible configurations that capture a specific "sound" (scenario shape).

5. **Temporal modes as synthesis algorithms**: FM, subtractive, additive, granular—each synthesis method produces characteristically different sounds from the same oscillator. Similarly, PEARL, DIRECTORIAL, CYCLICAL produce characteristically different narratives from the same entities.

The metaphor helps users who already understand sound synthesis apply that intuition to temporal simulation. It also provides a vocabulary for discussing otherwise-abstract concepts: "What's the attack on Jefferson's presence?" is more graspable than "What's the entity introduction latency coefficient?"

---

## Implementation Phases

Each phase is:
1. **Independently deployable** — Can ship without later phases
2. **Backward compatible** — Existing configs unchanged
3. **Fully tested** — Unit tests + E2E verification
4. **MVP scoped** — Minimal code for maximum utility

---

## Phase 1: ADSR Envelope for Entities

### Concept

An ADSR envelope describes how an entity's **presence intensity** evolves through a scenario:

```
Intensity
    ^
1.0 |    /\
    |   /  \____
    |  /        \
0.0 |_/          \____
    +--A--D--S----R--> Time
```

- **Attack (A)**: How quickly the entity reaches full presence (0.0 = instant, 1.0 = gradual across all timepoints)
- **Decay (D)**: Initial intensity drop after peak (0.0 = none, 1.0 = drops to sustain immediately)
- **Sustain (S)**: Baseline presence level during middle timepoints (0.0-1.0)
- **Release (R)**: How the entity fades in final timepoints (0.0 = abrupt, 1.0 = gradual)

### Schema Addition

```python
# generation/config_schema.py

@dataclass
class EnvelopeConfig:
    """ADSR envelope for entity presence intensity."""
    attack: float = 0.1     # 0.0-1.0, how quickly entity reaches full presence
    decay: float = 0.2      # 0.0-1.0, drop after initial peak
    sustain: float = 0.8    # 0.0-1.0, baseline presence level
    release: float = 0.3    # 0.0-1.0, fade out speed

    def __post_init__(self):
        """Clamp values to valid range."""
        self.attack = max(0.0, min(1.0, self.attack))
        self.decay = max(0.0, min(1.0, self.decay))
        self.sustain = max(0.0, min(1.0, self.sustain))
        self.release = max(0.0, min(1.0, self.release))

    def intensity_at(self, progress: float, total_timepoints: int) -> float:
        """
        Calculate presence intensity at a given progress point.

        Args:
            progress: 0.0 (start) to 1.0 (end) of scenario
            total_timepoints: Total number of timepoints

        Returns:
            Intensity multiplier 0.0-1.0
        """
        # Normalize envelope parameters to scenario length
        a_end = self.attack * 0.25  # Attack phase is first 25% max
        d_end = a_end + self.decay * 0.25  # Decay is next 25% max
        r_start = 1.0 - self.release * 0.25  # Release is last 25% max

        if progress < a_end:
            # Attack phase: ramp up
            return progress / a_end if a_end > 0 else 1.0
        elif progress < d_end:
            # Decay phase: drop to sustain
            decay_progress = (progress - a_end) / (d_end - a_end) if (d_end - a_end) > 0 else 1.0
            return 1.0 - (1.0 - self.sustain) * decay_progress
        elif progress < r_start:
            # Sustain phase: hold level
            return self.sustain
        else:
            # Release phase: fade out
            release_progress = (progress - r_start) / (1.0 - r_start) if (1.0 - r_start) > 0 else 1.0
            return self.sustain * (1.0 - release_progress)
```

### EntityConfig Update

```python
@dataclass
class EntityConfig:
    count: int = 3
    allow_animistic: bool = True
    # NEW: Optional envelope for presence modulation
    envelope: Optional[EnvelopeConfig] = None

    def get_envelope(self) -> EnvelopeConfig:
        """Get envelope, creating default if not set."""
        return self.envelope or EnvelopeConfig()
```

### Orchestrator Integration

In `orchestrator.py`, apply envelope when calculating entity participation:

```python
def get_entity_intensity(self, entity_id: str, timepoint_index: int, total_timepoints: int) -> float:
    """Get entity's presence intensity at a timepoint."""
    # Get entity's envelope (from config or default)
    envelope = self.config.entities.get_envelope()

    # Calculate progress through scenario
    progress = timepoint_index / max(1, total_timepoints - 1)

    # Get base intensity from envelope
    intensity = envelope.intensity_at(progress, total_timepoints)

    return intensity
```

Use intensity to:
- Weight entity contributions in dialog synthesis
- Adjust detail level in training data generation
- Modulate relationship strength calculations

### Backward Compatibility

- `envelope` field is optional, defaults to `None`
- When `None`, `get_envelope()` returns default `EnvelopeConfig()`
- Default envelope produces flat 0.8 sustain (current implicit behavior)
- Existing configs work unchanged

### Test Plan

```python
# tests/unit/test_synth_adsr.py

def test_envelope_defaults():
    """Default envelope produces expected intensity curve."""
    env = EnvelopeConfig()
    assert env.attack == 0.1
    assert env.sustain == 0.8

def test_envelope_intensity_at_start():
    """Intensity starts low during attack."""
    env = EnvelopeConfig(attack=0.5)
    assert env.intensity_at(0.0, 10) < 0.5

def test_envelope_intensity_at_sustain():
    """Intensity reaches sustain level in middle."""
    env = EnvelopeConfig(sustain=0.7)
    assert abs(env.intensity_at(0.5, 10) - 0.7) < 0.1

def test_envelope_intensity_at_release():
    """Intensity fades during release."""
    env = EnvelopeConfig(release=0.5)
    assert env.intensity_at(0.95, 10) < env.intensity_at(0.5, 10)

def test_envelope_clamping():
    """Values outside 0-1 are clamped."""
    env = EnvelopeConfig(attack=1.5, sustain=-0.5)
    assert env.attack == 1.0
    assert env.sustain == 0.0

def test_entity_config_envelope_optional():
    """EntityConfig works without envelope."""
    config = EntityConfig(count=5)
    assert config.envelope is None
    assert config.get_envelope().sustain == 0.8
```

### E2E Verification

```bash
# Existing tests must pass
./run.sh core

# Verify board_meeting produces same output structure
./run.sh run board_meeting
# Compare entity count, timepoint count, mechanism coverage
```

---

## Phase 2: Voice Controls

### Concept

Each entity is a "voice" that can be:
- **Muted**: Excluded from dialog synthesis (but still exists in world)
- **Solo'd**: Only this entity participates (others backgrounded)
- **Gain-adjusted**: Weighted importance (0.0-1.0)

### Schema Addition

```python
@dataclass
class VoiceConfig:
    """Mixer-style controls for an entity."""
    mute: bool = False       # Exclude from active dialog
    solo: bool = False       # Focus on this entity only
    gain: float = 1.0        # Importance weight 0.0-1.0

    def __post_init__(self):
        self.gain = max(0.0, min(1.0, self.gain))
```

### Per-Entity Voice Assignment

Voices can be assigned per-entity in scenario metadata:

```python
@dataclass
class EntityConfig:
    count: int = 3
    allow_animistic: bool = True
    envelope: Optional[EnvelopeConfig] = None
    # NEW: Default voice settings (can be overridden per-entity)
    default_voice: Optional[VoiceConfig] = None
```

In scenario description or metadata, specific entities can override:

```json
{
  "entities": {
    "count": 5,
    "voices": {
      "john_smith": {"gain": 1.0, "solo": false, "mute": false},
      "background_character": {"gain": 0.3, "mute": false}
    }
  }
}
```

### Orchestrator Integration

```python
def get_active_entities(self, entities: List[Entity]) -> List[Entity]:
    """Filter entities based on voice controls."""
    voices = self.config.entities.get_voices()

    # Check for any solo'd entities
    solo_entities = [e for e in entities if voices.get(e.id, VoiceConfig()).solo]
    if solo_entities:
        return solo_entities

    # Filter out muted entities
    active = [e for e in entities if not voices.get(e.id, VoiceConfig()).mute]

    return active

def get_entity_weight(self, entity_id: str) -> float:
    """Get entity's voice gain."""
    voices = self.config.entities.get_voices()
    return voices.get(entity_id, VoiceConfig()).gain
```

### Backward Compatibility

- All voice fields optional with non-disruptive defaults
- `mute=False`, `solo=False`, `gain=1.0` = current behavior
- Existing configs work unchanged

### Test Plan

```python
# tests/unit/test_synth_voice.py

def test_voice_defaults():
    """Default voice is fully active."""
    voice = VoiceConfig()
    assert voice.mute == False
    assert voice.solo == False
    assert voice.gain == 1.0

def test_muted_entity_excluded():
    """Muted entities filtered from active list."""
    # ... test get_active_entities with muted entity

def test_solo_entity_isolates():
    """Solo'd entity becomes only active entity."""
    # ... test get_active_entities with one solo'd

def test_gain_weights_contribution():
    """Gain affects entity weight calculation."""
    # ... test get_entity_weight returns gain value
```

---

## Phase 3: Patch System

### Concept

Templates become "patches"—named presets with additional metadata for the synth paradigm.

### Metadata Additions

```json
{
  "id": "board_meeting",
  "name": "Board Meeting",
  "patch": {
    "name": "Boardroom Brass",
    "category": "corporate",
    "tags": ["conflict", "decision", "multi-entity"],
    "author": "timepoint-daedalus",
    "version": "1.0",
    "description": "High-tension executive dynamics with competing agendas"
  },
  "scenario_description": "...",
  "temporal": {...},
  "entities": {...}
}
```

### Catalog Enhancement

Update `generation/templates/catalog.json`:

```json
{
  "patches": {
    "corporate": ["board_meeting", "vc_pitch_pearl", "vc_pitch_roadshow"],
    "historical": ["jefferson_dinner"],
    "crisis": ["hospital_crisis"],
    "mystical": ["kami_shrine"]
  },
  "templates": [...]
}
```

### CLI Enhancement

```bash
# List patches by category
./run.sh list --patches
./run.sh list --patches corporate

# Run by patch name
./run.sh run --patch "Boardroom Brass"
```

### Backward Compatibility

- `patch` field is optional in template JSON
- Templates without patch metadata work unchanged
- `--template` flag continues to work
- `--patch` is additive option

### Test Plan

```python
def test_template_without_patch_loads():
    """Templates without patch metadata load normally."""

def test_patch_metadata_accessible():
    """Patch metadata can be retrieved from loaded template."""

def test_list_patches_command():
    """CLI lists patches correctly."""
```

---

## Phase 4: Monitoring Hooks (State Emission)

### Concept

Emit events at key workflow points to enable visualization tools. No behavioral change—just observability.

### Event Types

```python
from enum import Enum
from dataclasses import dataclass
from typing import Any, Optional
import time

class SynthEvent(Enum):
    # Lifecycle events
    RUN_START = "run_start"
    RUN_COMPLETE = "run_complete"

    # Entity events
    ENTITY_CREATED = "entity_created"
    ENTITY_INTENSITY_CHANGE = "entity_intensity_change"
    ENTITY_RESOLUTION_CHANGE = "entity_resolution_change"

    # Timepoint events
    TIMEPOINT_START = "timepoint_start"
    TIMEPOINT_COMPLETE = "timepoint_complete"

    # Dialog events
    DIALOG_TURN = "dialog_turn"
    EXPOSURE_EVENT = "exposure_event"

@dataclass
class SynthEventData:
    event_type: SynthEvent
    timestamp: float
    run_id: str
    data: dict

    def to_dict(self) -> dict:
        return {
            "event": self.event_type.value,
            "timestamp": self.timestamp,
            "run_id": self.run_id,
            "data": self.data
        }
```

### Event Emitter

```python
class SynthEventEmitter:
    """Emits events for synth-style monitoring."""

    def __init__(self, enabled: bool = True):
        self.enabled = enabled
        self.listeners: List[Callable[[SynthEventData], None]] = []

    def add_listener(self, listener: Callable[[SynthEventData], None]):
        """Register a listener for events."""
        self.listeners.append(listener)

    def emit(self, event_type: SynthEvent, run_id: str, data: dict):
        """Emit an event to all listeners."""
        if not self.enabled:
            return

        event = SynthEventData(
            event_type=event_type,
            timestamp=time.time(),
            run_id=run_id,
            data=data
        )

        for listener in self.listeners:
            try:
                listener(event)
            except Exception:
                pass  # Don't let listener errors break workflow
```

### Integration Points

```python
# In orchestrator.py

class SceneOrchestrator:
    def __init__(self, config, emitter: Optional[SynthEventEmitter] = None):
        self.emitter = emitter or SynthEventEmitter(enabled=False)

    def create_entity(self, entity_spec):
        entity = Entity(...)
        self.emitter.emit(
            SynthEvent.ENTITY_CREATED,
            self.run_id,
            {"entity_id": entity.id, "type": entity.type}
        )
        return entity
```

### Default Listener (Logging)

```python
def logging_listener(event: SynthEventData):
    """Default listener that logs events."""
    logger.debug(f"[SYNTH] {event.event_type.value}: {event.data}")
```

### Backward Compatibility

- Emitter disabled by default
- No behavioral change when disabled
- Existing code unchanged
- Opt-in via config flag

### Test Plan

```python
def test_emitter_disabled_by_default():
    """Emitter doesn't emit when disabled."""

def test_emitter_calls_listeners():
    """Emitter calls registered listeners."""

def test_listener_error_doesnt_break_workflow():
    """Bad listener doesn't crash emission."""
```

---

## Configuration Examples

### Minimal (Current Behavior)

```python
config = SimulationConfig(
    world_id="test",
    scenario_description="A simple test scenario"
)
# Works exactly as before
```

### With ADSR Envelope

```python
config = SimulationConfig(
    world_id="dramatic_scene",
    scenario_description="A confrontation with dramatic buildup",
    entities=EntityConfig(
        count=3,
        envelope=EnvelopeConfig(
            attack=0.3,    # Slow buildup
            decay=0.1,     # Quick peak
            sustain=0.9,   # High intensity throughout
            release=0.5    # Gradual resolution
        )
    )
)
```

### With Voice Controls

```python
config = SimulationConfig(
    world_id="focused_scene",
    scenario_description="CEO vs Board confrontation",
    entities=EntityConfig(
        count=5,
        default_voice=VoiceConfig(gain=0.5),  # Background entities at 50%
        # Per-entity overrides in scenario metadata
    )
)
```

### Full Synth Config

```python
config = SimulationConfig(
    world_id="synth_demo",
    scenario_description="Full synth paradigm demonstration",
    entities=EntityConfig(
        count=4,
        envelope=EnvelopeConfig(
            attack=0.2,
            decay=0.2,
            sustain=0.7,
            release=0.3
        ),
        default_voice=VoiceConfig(gain=0.8)
    ),
    metadata={
        "patch": {
            "name": "Demo Patch",
            "category": "test"
        }
    }
)
```

---

## Migration Guide

### For Existing Configs

**No changes required.** All new fields are optional with backward-compatible defaults.

### For New Configs

1. Consider adding `envelope` for scenarios with clear dramatic arc
2. Use `voice` controls when some entities should be foregrounded
3. Add `patch` metadata for discoverability

### For Template Authors

Add patch metadata to make templates discoverable:

```json
{
  "patch": {
    "name": "Castaway Colony",
    "category": "scifi",
    "tags": ["alien-planet", "survival", "branching", "knowledge-provenance", "full-mechanism-coverage", "showcase"],
    "author": "timepoint-daedalus",
    "version": "1.0",
    "description": "Full-mechanism showcase: crash-landed crew on alien planet with branching survival strategies"
  }
}
```

Categories include: corporate, historical, crisis, mystical, mystery, directorial, portal, space, scifi, convergence.

---

## Anti-Patterns

### Don't Do These

1. **Don't add audio output** — We produce data, not sound
2. **Don't implement filters as resolution** — Resolution is discrete, filters are continuous
3. **Don't add MIDI** — Unnecessary protocol complexity
4. **Don't create modulation matrices** — Over-engineering
5. **Don't require synth parameters** — Keep everything optional
6. **Don't break existing configs** — Backward compatibility is sacred

### Warning Signs

If you find yourself:
- Adding DSP algorithms → Stop
- Computing frequency content → Stop
- Implementing audio formats → Stop
- Making existing configs fail → Stop

---

## Test Matrix

| Phase | Unit Tests | Integration | E2E |
|-------|-----------|-------------|-----|
| 1. ADSR | `test_synth_adsr.py` | Envelope in orchestrator | `./run.sh core` passes |
| 2. Voice | `test_synth_voice.py` | Voice in dialog synthesis | Muted entity excluded |
| 3. Patch | `test_synth_patch.py` | Catalog loading | `./run.sh list --patches` |
| 4. Events | `test_synth_events.py` | Emitter in workflow | Events logged during run |

### Regression Prevention

After each phase:

```bash
# All existing tests must pass
./run.sh core

# Specific template verification
./run.sh run board_meeting
./run.sh run jefferson_dinner

# Verify mechanism coverage unchanged
./run.sh list --mechanisms
```

---

## Future Possibilities (Not In Scope)

These could be built on this foundation but are **not part of this specification**:

- **Web UI with knobs/faders** — React/Vue control surface
- **Real-time parameter adjustment** — WebSocket updates during run
- **Spectrogram visualization** — Entity state over time as heatmap
- **Patch sharing** — Community template marketplace
- **Ableton Link sync** — Sync timepoints to audio DAW (why not?)

---

## Summary

The SynthasAIzer paradigm provides:

1. **ADSR envelopes** for entity lifecycle modeling
2. **Voice controls** for entity mixing (mute/solo/gain)
3. **Patch system** for template organization
4. **Event emission** for monitoring and visualization

All features are:
- Optional (backward compatible)
- MVP-scoped (minimal code)
- Fully tested (unit + E2E)
- Metaphor-appropriate (no stretching)

The synthesizer metaphor gives us a rich vocabulary for control without requiring us to implement audio DSP. We borrow the **interface patterns**, not the **signal processing**.

---

*"The best interface is one you already understand."* — Adapted from every synthesizer manual ever
