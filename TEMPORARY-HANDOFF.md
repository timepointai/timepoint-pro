# Handoff: ADPRS Waveform System (February 2026)

**DELETE THIS FILE AFTER READING.** It is a temporary context transfer document, not permanent documentation.

---

## Where We Are

Branch: `feat/container-sandbox-and-branching-quality`
Latest commit: `1652360` (docs update)
All code is committed and pushed. Working tree is clean.

### What was built

The ADPRS (Asymptotic/Duration/Period/Recurrence/Spread) waveform system — a continuous fidelity envelope that maps entity cognitive activation to resolution bands (TENSOR/SCENE/GRAPH/DIALOG/TRAINED). This is the SynthasAIzer Phase 1-3 implementation.

**6 new synth modules** (~1,528 lines):
- `synth/fidelity_envelope.py` — `ADPRSEnvelope`, `ADPRSComposite`, phi→band mapping
- `synth/trajectory_tracker.py` — `CognitiveSnapshot` accumulation, tau normalization
- `synth/adprs_fitter.py` — Cold/warm scipy fitting, cross-run convergence
- `synth/harmonic_fitter.py` — K=3 multi-harmonic extension, spectral distance
- `synth/shadow_evaluator.py` — Observation-only divergence tracking
- `synth/waveform_scheduler.py` — phi→resolution→skip-LLM compute gate

**8 test files** (142 tests, all passing):
- `tests/unit/test_fidelity_envelope.py` (30)
- `tests/unit/test_trajectory_tracker.py` (20)
- `tests/unit/test_adprs_fitter.py` (19)
- `tests/unit/test_harmonic_fitter.py` (19)
- `tests/unit/test_shadow_evaluator.py` (16)
- `tests/unit/test_waveform_scheduler.py` (20)
- `tests/integration/test_adprs_phase2_integration.py` (6)
- `tests/integration/test_waveform_sufficiency.py` (12)

**Modified files:**
- `synth/__init__.py` — Exports all new classes
- `generation/config_schema.py` — Added `adprs_envelopes` field to `EntityConfig`
- `storage.py` — Null confidence coercion
- `pyproject.toml` — Dependency updates
- `claude-container.sh` — Fixed dep install order (poetry-first)
- `.devcontainer/init-firewall.sh` — Added `github.com` to firewall allowlist
- `e2e_workflows/e2e_runner.py` — Extended for waveform pipeline

---

## What's Been Tested

- All 142 ADPRS unit + integration tests: **PASS**
- Existing test suite (excluding pre-existing failures): **PASS** (132 passed, 8 skipped)
- WSR > 0.7 confirmed on synthetic trajectories
- K=3 harmonics beat K=1 on complex signals

### Pre-existing failures (NOT caused by our changes)

1. **API tests** (`test_api.py`, `test_batch_api.py`, `test_rate_limit.py`, `test_simulation_runner.py`, `test_usage_quota.py`, `test_api_integration.py`) — All fail with `ModuleNotFoundError: No module named 'slowapi'`. Fixed for next container boot (poetry-first install in `claude-container.sh`), but in current session install `slowapi` manually: `pip install slowapi`
2. **CLI test** (`test_api_cli_integration.py::test_run_sh_help_contains_api_options`) — Asserts `--api` flag in help output but `api` is now a subcommand. Pre-existing, unrelated.
3. **LLM integration tests** — Tests marked `@pytest.mark.real_llm` are flaky because they make real API calls. They're deselected by default unless you pass `--run-llm`.
4. **`logs/test_runs/test_*.py`** — Old test run scripts in logs/ that pytest collects. Ignore via `--ignore=logs/`.

---

## What's Left To Do

### Immediate (this branch)

1. **Orchestrator integration** — The ADPRS modules are self-contained and tested but not yet wired into the main `orchestrator.py` pipeline. The waveform scheduler should be called during entity resolution decisions. Key integration point: `WaveformScheduler.schedule()` returns a `ScheduleDecision` with `band` and `skip_llm` — use this to gate LLM calls per entity per timepoint.

2. **Shadow evaluation in production runs** — `ShadowEvaluator` is built for observation-only mode (tracks divergence without changing behavior). Wire it into the run pipeline to collect divergence data across real runs. This validates ADPRS predictions against actual resolution choices.

3. **Cross-run fitting** — `ADPRSFitter.warm_fit()` accepts a prior from a previous run. The `apply_to_entities()` method stores fit results in entity metadata under `adprs_envelopes`. On subsequent runs, read this metadata to warm-start fitting. The plumbing exists but needs to be connected in the run lifecycle.

4. **Fix the CLI test** — `tests/integration/test_api_cli_integration.py::test_run_sh_help_contains_api_options` expects `--api` but should check for `api` subcommand. Trivial fix.

### Near-term

5. **Phase 4: Event Monitoring** — Spec exists in SYNTH.md. `SynthEventEmitter` is already implemented in `synth/events.py`. Shadow evaluator already emits `ENVELOPE_PHASE_CHANGE` events. Extend to full monitoring dashboard.

6. **PR to main** — Once orchestrator integration is tested, open a PR from `feat/container-sandbox-and-branching-quality` → `main`. The branch has 4 commits ahead of main.

---

## Key Documentation

- **[SYNTH.md](SYNTH.md)** — Full ADPRS spec: waveform math, phi→band mapping, architecture, test coverage (updated Feb 2026)
- **[README.md](README.md)** — Project overview with updated architecture diagram showing waveform scheduler
- **[QUICKSTART.md](QUICKSTART.md)** — Setup guide with synth test commands
- **[MECHANICS.md](MECHANICS.md)** — The 19 mechanisms that ADPRS waveforms gate
- **[MILESTONES.md](MILESTONES.md)** — Roadmap

---

## Running Tests

```bash
# ADPRS waveform tests only (fast, no LLM calls)
python -m pytest tests/unit/test_fidelity_envelope.py tests/unit/test_trajectory_tracker.py \
  tests/unit/test_adprs_fitter.py tests/unit/test_harmonic_fitter.py \
  tests/unit/test_shadow_evaluator.py tests/unit/test_waveform_scheduler.py \
  tests/integration/test_adprs_phase2_integration.py \
  tests/integration/test_waveform_sufficiency.py -v

# Full test suite (exclude known broken)
python -m pytest tests/ --ignore=logs/ -q --tb=short

# If slowapi not installed yet
pip install slowapi
```

---

## Container Notes

- **GitHub auth**: Run `gh auth login --hostname github.com --git-protocol https --web` then `gh auth setup-git` to enable git push.
- **Firewall**: `github.com` was added to `.devcontainer/init-firewall.sh` allowlist. If you can't push, check that the firewall resolved github.com's current IPs: `sudo ipset list allowed-domains`.
- **Dependencies**: `claude-container.sh` now runs `poetry install` first (not `pip install -e .` which silently installs zero deps with poetry-backend projects).

---

**Remember: delete this file after reading. It should not be committed to main.**
