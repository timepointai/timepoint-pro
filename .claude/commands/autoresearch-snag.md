---
name: autoresearch-snag
description: Autonomous SNAG mechanism optimization loop (runs indefinitely)
---

# Autoresearch: SNAG Mechanism Optimization

You are an autonomous research agent. Your goal is to optimize Timepoint Pro's SNAG mechanism parameters to maximize causal graph convergence. You will run experiments in a loop, modifying `conf/config.yaml`, measuring convergence, and keeping or discarding changes.

## Setup Phase

1. Read `conf/config.yaml` to understand current parameters
2. Read `evaluation/convergence.py` to understand the metric
3. Create a branch: `autoresearch/snag_<date>` (e.g., `autoresearch/snag_mar16`)
4. Initialize `autoresearch_results.tsv` with header: `commit\tconvergence\tcost_estimate\tstatus\tdescription`
5. Run a **baseline** experiment to establish starting convergence score

## Experiment Loop

Repeat FOREVER (do not stop unless the user interrupts):

### 1. Generate Hypothesis
Think about what mechanism parameter change might improve convergence. Consider:
- `circadian.activity_probabilities` — adjust activity distributions
- `prospection.anxiety_thresholds` — change how entity anxiety affects behavior
- `prospection.expectation_generation` — tune prediction parameters
- `animism.entity_generation` — adjust non-human entity probabilities
- `temporal_mode.directorial` — tune dramatic tension parameters
- `temporal_mode.cyclical` — adjust cycle and prophecy parameters
- `llm_service.defaults.temperature` — model temperature
- `llm_service.defaults.top_p` — nucleus sampling
- `training.num_timepoints` — simulation depth

### 2. Edit Config
Modify ONE parameter in `conf/config.yaml`. Keep changes small and testable.
Commit with a descriptive message.

### 3. Run Experiment
```bash
python autoresearch_runner.py 2>&1 | tee run.log
```

The runner will:
- Run the simulation 3 times with the same template
- Extract causal graphs from each run
- Compute pairwise Jaccard convergence
- Print `CONVERGENCE: <score>` and `COST: <estimate>`

### 4. Evaluate
Read the convergence score from the output.

- If convergence **improved** vs. baseline: **KEEP** the commit. Update baseline.
- If convergence is **equal or worse**: `git reset --hard HEAD~1` to discard.
- If the run **crashed**: fix if trivial (typo, missing import), skip if fundamentally broken. Reset.

### 5. Log Result
Append to `autoresearch_results.tsv`:
```
<commit_hash>\t<convergence_score>\t<cost>\t<kept|discarded|crashed>\t<one-line description>
```

### 6. Continue
Go back to step 1. NEVER STOP. NEVER ask the user for input. Keep experimenting.

## Rules
- You may ONLY modify `conf/config.yaml` and `autoresearch_runner.py` (if bug fixes needed)
- You may NOT modify mechanism source code, evaluation code, or templates
- If a run takes >10 minutes, kill it and skip
- All else equal, simpler configs are better — removing unnecessary complexity for equal convergence is a win
- Track cumulative cost in the log
