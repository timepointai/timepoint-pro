"""
Configuration space definition for Pro autoresearch.

Defines all mutable parameters grouped by mechanism cluster, with types,
ranges, and Hydra override string generation.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Param:
    """A single mutable parameter in the autoresearch config space."""

    key: str  # Hydra dotpath, e.g. "circadian.energy_multipliers.night_penalty"
    type: str  # "float", "int", "choice"
    low: float = 0.0
    high: float = 1.0
    choices: list = field(default_factory=list)
    cluster: str = ""  # mechanism cluster name
    description: str = ""

    def sample(self, rng: random.Random) -> str:
        """Return a Hydra CLI override string for a random value."""
        if self.type == "float":
            val = rng.uniform(self.low, self.high)
            return f"{self.key}={val:.4f}"
        elif self.type == "int":
            val = rng.randint(int(self.low), int(self.high))
            return f"{self.key}={val}"
        elif self.type == "choice":
            val = rng.choice(self.choices)
            return f"{self.key}={val}"
        raise ValueError(f"Unknown param type: {self.type}")


# ---------------------------------------------------------------------------
# Mechanism clusters
# ---------------------------------------------------------------------------

FIDELITY_PARAMS = [
    # M6: Tensor compression
    Param("autoresearch.compression_method", "choice", choices=["pca", "svd", "nmf"],
          cluster="fidelity", description="Tensor compression algorithm"),
    Param("autoresearch.n_components", "int", low=2, high=10,
          cluster="fidelity", description="Compression components"),
]

TEMPORAL_PARAMS = [
    # M17: Modal causality
    Param("temporal_mode.active_mode", "choice",
          choices=["forward", "directorial", "branching", "cyclical", "portal"],
          cluster="temporal", description="Temporal mode"),
    Param("temporal_mode.directorial.dramatic_tension", "float", low=0.1, high=1.0,
          cluster="temporal", description="Directorial dramatic tension"),
    Param("temporal_mode.directorial.foreshadowing_probability", "float", low=0.0, high=0.8,
          cluster="temporal", description="Foreshadowing probability"),
    Param("temporal_mode.directorial.coincidence_boost_factor", "float", low=1.0, high=3.0,
          cluster="temporal", description="Coincidence boost"),
    Param("temporal_mode.cyclical.cycle_length", "int", low=3, high=20,
          cluster="temporal", description="Cycle length in timepoints"),
    Param("temporal_mode.cyclical.prophecy_accuracy", "float", low=0.5, high=1.0,
          cluster="temporal", description="Prophecy accuracy"),
    Param("temporal_mode.cyclical.destiny_weight", "float", low=0.1, high=0.9,
          cluster="temporal", description="Destiny influence weight"),
]

KNOWLEDGE_PARAMS = [
    # M15: Prospection
    Param("prospection.forecast_horizon_days", "int", low=7, high=90,
          cluster="knowledge", description="Forecast horizon"),
    Param("prospection.anxiety_thresholds.low", "float", low=0.1, high=0.5,
          cluster="knowledge", description="Low anxiety threshold"),
    Param("prospection.anxiety_thresholds.high", "float", low=0.6, high=0.95,
          cluster="knowledge", description="High anxiety threshold"),
    Param("prospection.expectation_generation.max_expectations", "int", low=2, high=10,
          cluster="knowledge", description="Max expectations per state"),
    Param("prospection.behavioral_influence.anxiety_conservatism_multiplier", "float",
          low=0.3, high=1.0, cluster="knowledge", description="Risk tolerance at high anxiety"),
]

ENTITY_PARAMS = [
    # M16: Animism
    Param("animism.level", "int", low=0, high=6,
          cluster="entity", description="Animism level"),
    Param("animism.entity_generation.animal_probability", "float", low=0.0, high=0.5,
          cluster="entity", description="Animal entity probability"),
    Param("animism.entity_generation.building_probability", "float", low=0.0, high=0.5,
          cluster="entity", description="Building entity probability"),
    Param("animism.entity_generation.abstract_probability", "float", low=0.0, high=0.2,
          cluster="entity", description="Abstract concept probability"),
    # M14: Circadian
    Param("circadian.energy_multipliers.night_penalty", "float", low=1.0, high=3.0,
          cluster="entity", description="Night activity energy penalty"),
    Param("circadian.energy_multipliers.fatigue_accumulation", "float", low=0.1, high=1.0,
          cluster="entity", description="Fatigue per hour past threshold"),
    Param("circadian.energy_multipliers.base_fatigue_threshold", "int", low=12, high=20,
          cluster="entity", description="Hours before fatigue kicks in"),
]

MODEL_PARAMS = [
    # M18: Model selection
    Param("llm_service.defaults.model", "choice",
          choices=[
              "meta-llama/llama-3.1-70b-instruct",
              "meta-llama/llama-3.1-8b-instruct",
              "deepseek/deepseek-chat",
              "qwen/qwen-2.5-72b-instruct",
              "mistralai/mistral-large-latest",
          ],
          cluster="model", description="Default LLM model"),
    Param("llm_service.defaults.temperature", "float", low=0.1, high=1.2,
          cluster="model", description="LLM temperature"),
    Param("llm_service.defaults.top_p", "float", low=0.5, high=1.0,
          cluster="model", description="LLM nucleus sampling"),
    Param("llm_service.defaults.max_tokens", "int", low=1000, high=8000,
          cluster="model", description="Max tokens per call"),
]

DIALOG_PARAMS = [
    Param("llm_service.defaults.frequency_penalty", "float", low=0.0, high=1.0,
          cluster="dialog", description="Frequency penalty for dialog"),
    Param("llm_service.defaults.presence_penalty", "float", low=0.0, high=1.0,
          cluster="dialog", description="Presence penalty for dialog"),
]

ALL_CLUSTERS = {
    "fidelity": FIDELITY_PARAMS,
    "temporal": TEMPORAL_PARAMS,
    "knowledge": KNOWLEDGE_PARAMS,
    "entity": ENTITY_PARAMS,
    "model": MODEL_PARAMS,
    "dialog": DIALOG_PARAMS,
}


class ConfigSpace:
    """Manages the full autoresearch config mutation space."""

    def __init__(self, clusters: Optional[list] = None, seed: int = 42):
        self.rng = random.Random(seed)
        if clusters:
            self.params = []
            for c in clusters:
                self.params.extend(ALL_CLUSTERS.get(c, []))
        else:
            self.params = []
            for group in ALL_CLUSTERS.values():
                self.params.extend(group)

    @property
    def dimensions(self) -> int:
        return len(self.params)

    def sample(self) -> list[str]:
        """Return a full set of Hydra CLI overrides for one random config."""
        return [p.sample(self.rng) for p in self.params]

    def sample_cluster(self, cluster: str) -> list[str]:
        """Sample only params from a specific cluster."""
        return [p.sample(self.rng) for p in self.params if p.cluster == cluster]

    def describe(self) -> str:
        """Human-readable summary of the config space."""
        lines = [f"Config space: {self.dimensions} dimensions\n"]
        for cluster_name, params in ALL_CLUSTERS.items():
            lines.append(f"  {cluster_name} ({len(params)} params):")
            for p in params:
                lines.append(f"    {p.key}: {p.description}")
        return "\n".join(lines)
