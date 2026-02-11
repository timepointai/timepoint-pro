"""
ADPRS Waveform Parameter Fitting Engine

Fits ADPRS waveform parameters (A, P, S, baseline) to observed cognitive
activation trajectories. Supports cold-start (differential_evolution for
global search) and warm-start (curve_fit for local refinement from priors).

Part of Phase 2: Emergent Envelope Fitting from TTM Trajectories.
"""

import math
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple

import numpy as np
from scipy.optimize import curve_fit, differential_evolution

from synth.fidelity_envelope import ADPRSEnvelope, ADPRSComposite

logger = logging.getLogger(__name__)

# Parameter bounds: A in [0,1], P in [0.5,8], S in [0,1], baseline in [0,1]
PARAM_BOUNDS = [(0.0, 1.0), (0.5, 8.0), (0.0, 1.0), (0.0, 1.0)]
PARAM_NAMES = ["A", "P", "S", "baseline"]
DEFAULT_PARAMS = {"A": 0.7, "P": 2.0, "S": 0.8, "baseline": 0.1}


def adprs_waveform(tau: np.ndarray, A: float, P: float, S: float, baseline: float) -> np.ndarray:
    """
    Vectorized ADPRS waveform for scipy optimizers.

    phi(tau) = |sin(tau * 2pi * P)| * (1 - tau)^((1 - A) * 3) * S + (1 - S) * baseline

    Must exactly match ADPRSEnvelope.evaluate() math. D is implicit (tau already
    normalized to [0, 1]). R is not fitted.
    """
    tau = np.asarray(tau, dtype=np.float64)
    oscillation = np.abs(np.sin(tau * 2.0 * np.pi * P))

    # Decay: (1 - tau)^((1 - A) * 3), with tau < 1 guard
    exponent = (1.0 - A) * 3.0
    base = np.clip(1.0 - tau, 0.0, None)
    decay = np.power(base, exponent)

    phi = oscillation * decay * S + (1.0 - S) * baseline
    return np.clip(phi, 0.0, 1.0)


@dataclass
class FitResult:
    """Result of fitting ADPRS parameters to an entity's trajectory."""

    entity_id: str
    params: Dict[str, float]
    residual: float  # MSE
    n_points: int
    method: str  # "differential_evolution" or "curve_fit"
    converged: bool
    prior_params: Optional[Dict[str, float]] = None
    parameter_drift: Optional[Dict[str, float]] = None

    def to_envelope(self, duration_ms: float, t0_iso: str) -> ADPRSEnvelope:
        """Convert fitted parameters to an ADPRSEnvelope."""
        return ADPRSEnvelope(
            A=self.params["A"],
            D=duration_ms,
            P=self.params["P"],
            R=0,  # Single-shot for MVP
            S=self.params["S"],
            t0=t0_iso,
            baseline=self.params["baseline"],
        )


class ADPRSFitter:
    """Fits ADPRS waveform parameters to observed activation trajectories."""

    def __init__(
        self,
        min_points: int = 5,
        de_maxiter: int = 100,
        de_tol: float = 1e-4,
        de_seed: int = 42,
    ):
        self.min_points = min_points
        self.de_maxiter = de_maxiter
        self.de_tol = de_tol
        self.de_seed = de_seed

    def fit_entity(
        self,
        tau: np.ndarray,
        activation: np.ndarray,
        entity_id: str,
        prior_params: Optional[Dict[str, float]] = None,
        harmonics: int = 1,
    ) -> FitResult:
        """
        Fit ADPRS parameters to a single entity's activation trajectory.

        Args:
            tau: Normalized time values [0, 1].
            activation: Observed activation values.
            entity_id: Entity identifier.
            prior_params: Prior parameters for warm-start.
            harmonics: Number of harmonics (K). K=1 (default) preserves
                original behavior. K>1 delegates to HarmonicFitter.

        Warm start (prior_params present): curve_fit for local refinement.
        Cold start (no prior): differential_evolution for global search.
        Falls back to sensible defaults on failure.
        """
        if harmonics > 1:
            from synth.harmonic_fitter import HarmonicFitter
            harmonic_fitter = HarmonicFitter(
                min_points=self.min_points,
                de_maxiter=self.de_maxiter,
                de_tol=self.de_tol,
                de_seed=self.de_seed,
            )
            return harmonic_fitter.fit_entity(
                tau, activation, entity_id,
                harmonics=harmonics, prior_params=prior_params,
            )

        tau = np.asarray(tau, dtype=np.float64)
        activation = np.asarray(activation, dtype=np.float64)
        n_points = len(tau)

        if prior_params is not None:
            result = self._warm_fit(tau, activation, entity_id, prior_params)
        else:
            result = self._cold_fit(tau, activation, entity_id)

        # Compute parameter drift if we had priors
        if prior_params is not None:
            drift = {}
            for name in PARAM_NAMES:
                drift[name] = abs(result.params[name] - prior_params.get(name, DEFAULT_PARAMS[name]))
            result.parameter_drift = drift
            result.prior_params = prior_params

        return result

    def _cold_fit(
        self, tau: np.ndarray, activation: np.ndarray, entity_id: str
    ) -> FitResult:
        """Global optimization via differential_evolution."""
        try:
            de_result = differential_evolution(
                func=lambda params: np.mean((adprs_waveform(tau, *params) - activation) ** 2),
                bounds=PARAM_BOUNDS,
                maxiter=self.de_maxiter,
                tol=self.de_tol,
                seed=self.de_seed,
            )
            params = dict(zip(PARAM_NAMES, de_result.x))
            residual = float(de_result.fun)
            converged = de_result.success
        except Exception as e:
            logger.warning("Cold fit failed for %s: %s — using defaults", entity_id, e)
            params = dict(DEFAULT_PARAMS)
            residual = float(np.mean((adprs_waveform(tau, **params) - activation) ** 2))
            converged = False

        return FitResult(
            entity_id=entity_id,
            params=params,
            residual=residual,
            n_points=len(tau),
            method="differential_evolution",
            converged=converged,
        )

    def _warm_fit(
        self,
        tau: np.ndarray,
        activation: np.ndarray,
        entity_id: str,
        prior_params: Dict[str, float],
    ) -> FitResult:
        """Local refinement via curve_fit starting from prior parameters."""
        p0 = [prior_params.get(name, DEFAULT_PARAMS[name]) for name in PARAM_NAMES]
        lower = [b[0] for b in PARAM_BOUNDS]
        upper = [b[1] for b in PARAM_BOUNDS]

        try:
            popt, _ = curve_fit(
                adprs_waveform,
                tau,
                activation,
                p0=p0,
                bounds=(lower, upper),
                maxfev=5000,
            )
            params = dict(zip(PARAM_NAMES, popt))
            residual = float(np.mean((adprs_waveform(tau, *popt) - activation) ** 2))
            converged = True
        except Exception as e:
            logger.warning(
                "Warm fit failed for %s: %s — falling back to cold fit", entity_id, e
            )
            return self._cold_fit(tau, activation, entity_id)

        return FitResult(
            entity_id=entity_id,
            params=params,
            residual=residual,
            n_points=len(tau),
            method="curve_fit",
            converged=converged,
            prior_params=prior_params,
        )

    def fit_all(
        self, tracker, entities: list
    ) -> Dict[str, FitResult]:
        """
        Fit all entities with sufficient trajectory data.

        Extracts prior params from entity_metadata["adprs_envelopes"] for warm-start.
        """
        results = {}
        entity_map = {e.entity_id: e for e in entities}

        for entity_id in tracker.get_all_entity_ids():
            if not tracker.has_sufficient_data(entity_id, self.min_points):
                continue

            tau_list, activation_list = tracker.get_activation_series(entity_id)
            if not tau_list:
                continue

            tau = np.array(tau_list)
            activation = np.array(activation_list)

            # Check for prior params (warm start)
            prior_params = None
            entity = entity_map.get(entity_id)
            if entity and hasattr(entity, "entity_metadata") and entity.entity_metadata:
                adprs_data = entity.entity_metadata.get("adprs_envelopes", {})
                envelopes = adprs_data.get("envelopes", [])
                if envelopes:
                    # Use the first envelope's params as prior
                    env = envelopes[0]
                    prior_params = {
                        "A": env.get("A", DEFAULT_PARAMS["A"]),
                        "P": env.get("P", DEFAULT_PARAMS["P"]),
                        "S": env.get("S", DEFAULT_PARAMS["S"]),
                        "baseline": env.get("baseline", DEFAULT_PARAMS["baseline"]),
                    }

            results[entity_id] = self.fit_entity(tau, activation, entity_id, prior_params)

        return results

    @staticmethod
    def apply_to_entities(
        results: Dict[str, "FitResult"],
        entities: list,
        duration_ms: float,
        t0_iso: str,
    ) -> int:
        """
        Write fitted envelopes to entity_metadata and update fit metadata.

        Returns the number of entities updated.
        """
        entity_map = {e.entity_id: e for e in entities}
        updated = 0

        for entity_id, fit_result in results.items():
            entity = entity_map.get(entity_id)
            if entity is None:
                continue

            envelope = fit_result.to_envelope(duration_ms, t0_iso)

            # Write envelope to entity_metadata
            entity.entity_metadata["adprs_envelopes"] = ADPRSComposite(
                envelopes=[envelope]
            ).to_metadata_dict()

            # Update fit metadata for cross-run convergence
            existing_meta = entity.entity_metadata.get("adprs_fit_metadata", {})
            run_count = existing_meta.get("run_count", 0) + 1
            residual_history = existing_meta.get("residual_history", [])
            residual_history.append(round(fit_result.residual, 6))
            # Bound residual history to last 20 entries
            residual_history = residual_history[-20:]

            entity.entity_metadata["adprs_fit_metadata"] = {
                "run_count": run_count,
                "last_method": fit_result.method,
                "last_residual": round(fit_result.residual, 6),
                "last_n_points": fit_result.n_points,
                "converged": fit_result.converged,
                "residual_history": residual_history,
                "parameter_drift": (
                    {k: round(v, 6) for k, v in fit_result.parameter_drift.items()}
                    if fit_result.parameter_drift
                    else None
                ),
            }

            updated += 1

        return updated
