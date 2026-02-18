# Causal Provenance as Training Signal: What Structured Temporal Simulation Implies for Foundation Model Research

**February 2026**

---

## The Convergence of Three Crises

Foundation model research is approaching a triple bottleneck. First, the data wall: Epoch AI projects exhaustion of public human text between 2026 and 2032, and synthetic data generation without structural guarantees produces model collapse -- the self-consuming loop where quality and diversity degrade across generations. Second, the causal reasoning gap: DeepMind's December 2025 paper "Robust agents learn causal world models" demonstrates that agents must learn causal structure to generalize under distributional shift, yet current training data contains no explicit causal annotation -- models must reverse-engineer causality from surface correlations in prose. Third, the evaluation crisis: Anthropic's alignment research reveals that as tasks grow harder and reasoning chains grow longer, model failures become dominated by incoherence rather than systematic error, and we lack tools to measure whether a model's internal causal reasoning is reliable versus merely consistent-looking.

These three problems are usually treated as separate research programs. They are the same problem viewed from different angles: the absence of causal structure in training data.

## The Missing Data Modality

Consider what a foundation model actually learns from a passage of text describing a historical event. It learns statistical associations between tokens. It may learn that "the doctor discovered contamination" often precedes "the commander ordered rationing." But it has no access to the typed causal graph underlying that sequence: that Okonkwo's empirical observation at timepoint 2 propagated to Tanaka via a critical alert at timepoint 3, which triggered a policy change affecting all crew members, where each step has a typed exposure event recording who learned what, from whom, with what confidence, through what modality.

This distinction matters computationally. The prose version admits multiple causal interpretations. Perhaps rationing was ordered for unrelated reasons and the contamination discovery was coincidental. Perhaps the commander already knew. The structured version is unambiguous: there is exactly one causal graph, every node has provenance, and every edge has a type. A model trained on the structured version doesn't need to infer causality -- it receives it as explicit signal.

The question this raises is not whether structured causal training data would be useful -- that much is obvious. The question is what becomes possible when you can generate millions of causally-consistent simulations at commodity cost, each carrying full typed provenance, with a built-in mechanism for measuring the reliability of the causal structure itself.

## Convergence Testing as Epistemic Primitive

The most underappreciated mechanism in this architecture is convergence testing. Run the same scenario N times with different random seeds. Extract causal graphs. Compute pairwise Jaccard similarity over the edge sets. Edges appearing in 9/10 runs are structural features of the scenario; edges appearing in 3/10 runs are stochastic noise.

This is not merely a quality assurance technique. It is an operational definition of causal robustness that requires no ground truth, no human labels, and no reference dataset. It answers the question: "Given these entities, these constraints, and these initial conditions, which causal relationships are necessary and which are contingent?"

The implications for training data are significant. Every causal edge in a convergence-tested dataset carries an empirical reliability score. A model trained on this data doesn't just learn "A causes B" -- it learns "A causes B with 0.87 convergence, meaning this relationship is structurally robust across simulation conditions." This is information-theoretically richer than any human-annotated causal dataset, because the reliability signal emerges from computational experiment rather than subjective judgment.

For alignment research specifically, convergence testing offers something that current evaluation frameworks lack: a way to measure whether a model's causal reasoning is stable without requiring access to ground truth. If a model produces causal explanations that converge across perturbations, its reasoning is at minimum self-consistent. If they diverge, the model is doing something closer to confabulation. This connects directly to Anthropic's finding that model failures are increasingly dominated by incoherence -- convergence testing is a tool for measuring exactly that incoherence, applied to causal reasoning specifically.

## Lazy Fidelity and the Attention Prior

The fidelity management system -- where resolution is a 2D surface over (entity, timepoint) space, elevated by queries and compressed by disuse -- implements something that current attention mechanisms approximate but never make explicit: the principle that intelligence allocates computational resources proportional to relevance, and that most of the world can be safely ignored most of the time.

In a standard transformer, attention weights perform a soft version of this allocation within a fixed context window. But the allocation is recomputed from scratch at every layer, with no persistent model of which entities deserve attention over time. The fidelity surface in Timepoint Pro is the explicit, persistent version: most entities sit at TENSOR resolution (~200 tokens) indefinitely, and the system only pays for full resolution (~50,000 tokens) when a query demands it. The result is a 95% token reduction without loss of causal structure.

The ADPRS waveform system takes this further. It fits continuous fidelity envelopes per entity -- learning to predict, based on accumulated trajectory data, when a given entity will need LLM-level resolution versus when a compressed tensor suffices. Envelopes persist across runs, improving with experience. The waveform scheduler then gates LLM calls: entities predicted to be in low-activation bands skip dialog synthesis entirely.

This is a learned attention prior over entities and time. It answers the question "who matters when?" before the simulation runs, and it improves its answer with each subsequent run. The architectural parallel to what neuroscience calls predictive processing is not accidental -- the system maintains a generative model of its own computational needs and allocates resources based on prediction error (shadow evaluation tracks divergence between predicted and actual resolution needs).

The research implication is this: what if attention allocation itself is a learnable function that should be trained explicitly, rather than emerging implicitly from softmax over key-query products? The ADPRS system demonstrates that entity-level attention prediction is tractable, that it improves with data, and that it can gate computation with measurable efficiency gains. Foundation models currently have no equivalent mechanism for deciding, before processing begins, which tokens in a context window are worth attending to and which can be safely compressed.

## Backward Inference and the Planning-Memory Isomorphism

PORTAL mode -- backward temporal reasoning from a known endpoint to the present -- exposes a structural relationship between planning and memory that current architectures handle poorly.

When PORTAL reasons backward from "Ares III mission failure in 2031" to discover what sequence of events in 2026-2030 could have produced that outcome, it is performing the same computational operation that humans use for both episodic memory retrieval and goal-directed planning. Remembering "how did I get here?" and planning "how do I get there?" are the same graph traversal in opposite directions over a causal structure. The difference is whether the known node is in the past (memory) or the future (planning).

Current language models are autoregressive -- they generate forward, token by token. They can be prompted to "reason backward," but the underlying computation is still forward prediction conditioned on a prompt containing the endpoint. PORTAL, by contrast, generates candidate antecedent states, scores them via hybrid evaluation (LLM plausibility + causal necessity + entity capability), validates forward coherence, and prunes incoherent paths. It explores a combinatorial search space -- approximately 700 candidate antecedents for a 10-step, 10-path simulation -- and selects for backward-coherent chains.

The training data this produces is qualitatively different from anything in existing pretraining corpora. Each backward-reasoned path carries metadata about why it was selected: its coherence score, the alternatives that were pruned, the pivot points where paths diverged. A model trained on this data doesn't just learn "X can follow Y" -- it learns "X is the most coherent antecedent of Z, given that alternatives A and B were considered and rejected for reasons R1 and R2." This is planning-aware training data. It teaches the structure of means-end reasoning, not just the surface form of narratives that happen to describe plans.

## Typed Knowledge Provenance and the Information Flow Problem

Every major lab is now grappling with some version of the knowledge attribution problem: given a model's output, what in its training data contributed to that output, and through what chain of reasoning? This matters for alignment (does the model know something it shouldn't?), for interpretability (why did it produce this answer?), and for legal compliance (was copyrighted material involved?).

The knowledge provenance system in Timepoint Pro implements a miniature version of this problem at the entity level. Each entity maintains a knowledge state that is the strict subset of its accumulated exposure events. An entity cannot reference information without a tracked exposure event explaining how it learned that information. The exposure event records the source entity, the content, the modality (witnessed, told, experienced, inferred), the timepoint, and the confidence level.

When this system generates training data, every token in a training example carries its full causal ancestry. Not just "the commander ordered rationing" but the complete chain: water testing protocol initiated at timepoint 1, contamination detected at timepoint 2 via empirical observation by Okonkwo, critical alert propagated to Tanaka at timepoint 3, policy decision issued at timepoint 3 with full entity roster and confidence levels. The training example is not a flat string but a structured object with typed provenance edges.

Training on data with this structure could address the knowledge attribution problem from the data side rather than the interpretability side. Instead of trying to reverse-engineer what a trained model knows and how it knows it -- the problem that mechanistic interpretability is attacking from the weights side -- you could train models on data where knowledge provenance is an explicit feature of every example. The model learns not just facts but the structure of knowing: that knowledge has sources, that confidence depends on the chain of transmission, that some knowledge is direct observation and some is hearsay, and that these distinctions matter for reasoning.

## Counterfactual Data as Contrastive Signal

BRANCHING mode generates natural contrastive pairs from the same initial conditions. At a decision point, the simulation spawns parallel timelines -- same entities, same constraints, same history up to the branch point, different choices, different outcomes. Each branch is internally consistent: entities in Branch B cannot access discoveries made in Branch A.

This produces training data with a property that no single-pass generator can match: matched counterfactual pairs where the only variable is the intervention. The same six crew members, the same crashed ship, the same alien planet -- but in one timeline they fortify their position, in another they explore, in a third they attempt to repair the emergency beacon. The downstream consequences diverge causally from a single decision.

For causal representation learning -- the program that Scholkopf et al. (2021) articulated as the next frontier for machine learning -- this is close to ideal training data. Counterfactual reasoning requires examples where you can see what changes when one variable changes and everything else is held constant. Natural text almost never provides this. BRANCHING mode generates it by construction, at scale, with full provenance.

## What This Architecture Does Not Do

It does not solve alignment. It does not produce AGI. It does not replace human judgment about what scenarios to simulate or what causal structures matter. The simulations are generated by the same LLMs that have all the well-documented failure modes -- hallucination, sycophancy, inconsistency under pressure.

What it does is provide architectural scaffolding that converts those unreliable generations into structured artifacts with explicit causal graphs, typed provenance, convergence-tested reliability scores, and counterfactual contrastive pairs. The LLMs generate the content. The framework enforces the structure. The convergence testing measures the reliability. The result is synthetic training data that is information-theoretically richer than unstructured text -- not because the individual generations are better, but because the structure preserves information that prose discards.

## The Compounding Bet

The deepest implication is about what happens over time. The ADPRS waveform system improves its entity-level attention predictions across runs. Convergence scores identify which scenario structures produce robust causal reasoning. The knowledge provenance system accumulates typed exposure graphs that grow more detailed with each simulation.

This is a system that gets better at knowing what it doesn't know. Each run produces not just training data but metadata about the reliability of that training data -- which causal edges are structural, which are noise, where the model's reasoning is stable and where it is fragile. This metadata is itself training signal. A foundation model trained on convergence-annotated causal data would learn not just to reason causally but to estimate its own confidence in causal claims -- a capacity that current models lack and that alignment researchers have identified as critical.

The data wall is real. The exhaustion of public human text is coming. But the response need not be "generate more of the same kind of data, synthetically." It can be "generate a fundamentally different kind of data -- data with structure, provenance, reliability scores, and causal ancestry -- that teaches models things that prose alone cannot teach." The question is whether the field will recognize that the bottleneck is not data volume but data structure, and that the tools to produce structurally rich synthetic data at commodity cost already exist.

---

*This document describes architectural implications, not product claims. The system is an open-source research prototype (Apache 2.0). Theoretical implications require empirical validation through controlled training experiments.*
