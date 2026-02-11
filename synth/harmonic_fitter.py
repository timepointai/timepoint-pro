"""
Harmonic Extension of ADPRS Waveform Fitting

Extends single-mode ADPRS to multi-harmonic K=3 waveforms. Each entity gets
a spectral signature — a harmonic series [c1, c2, c3] that captures richer
behavioral dynamics than the single-mode (A, P, S, baseline) fit.

At K=1 (fundamental only), the harmonic waveform reduces exactly to the
original ADPRS waveform where c1=S, A1=A, P1=P.

Part of Phase 2.5: Harmonic Extension from TTM-MMA plan.
"""

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import numpy as np
from scipy.optimize import curve_fit, differential_evolution

logger = logging.getLogger(__name__)

# Parameter bounds for K=3 harmonic fit:
# P1 in [0.5, 8.0], c1 in [0.01, 1.0], A1 in [0.0, 1.0],
# c2 in [0.0, 1.0], A2 in [0.0, 1.0], c3 in [0.0, 1.0],
# A3 in [0.0, 1.0], baseline in [0.0, 1.0]
HARMONIC_PARAM_BOUNDS = [
    (0.5, 8.0),   # P1
    (0.01, 1.0),  # c1
    (0.0, 1.0),   # A1
    (0.0, 1.0),   # c2
    (0.0, 1.0),   # A2
    (0.0, 1.0),   # c3
    (0.0, 1.0),   # A3
    (0.0, 1.0),   # baseline
]

HARMONIC_PARAM_NAMES = ["P1", "c1", "A1", "c2", "A2", "c3", "A3", "baseline"]

HARMONIC_DEFAULT_PARAMS = {
    "P1": 2.0,
    "c1": 0.8,
    "A1": 0.7,
    "c2": 0.0,
    "A2": 0.5,
    "c3": 0.0,
    "A3": 0.5,
    "baseline": 0.1,
}


def harmonic_adprs_waveform(
    tau: np.ndarray,
    P1: float,
    c1: float,
    A1: float,
    c2: float,
    A2: float,
    c3: float,
    A3: float,
    baseline: float,
) -> np.ndarray:
    """
    Vectorized K=3 harmonic ADPRS waveform for scipy optimizers.

    phi(tau) = sum_{k=1}^{3} c_k * |sin(tau * 2pi * k * P1)| * (1-tau)^((1-A_k)*3) + baseline

    At K=1 with c2=c3=0, this reduces to:
        c1 * |sin(tau * 2pi * P1)| * (1-tau)^((1-A1)*3) + baseline
    which is mathematically equivalent to the original ADPRS waveform
    where c1=S, A1=A, P1=P.

    Output clamped to [0, 1].
    """
    tau = np.asarray(tau, dtype=np.float64)
    base = np.clip(1.0 - tau, 0.0, None)

    phi = np.full_like(tau, baseline)

    # Harmonic 1 (fundamental)
    osc1 = np.abs(np.sin(tau * 2.0 * np.pi * 1 * P1))
    decay1 = np.power(base, (1.0 - A1) * 3.0)
    phi = phi + c1 * osc1 * decay1

    # Harmonic 2
    osc2 = np.abs(np.sin(tau * 2.0 * np.pi * 2 * P1))
    decay2 = np.power(base, (1.0 - A2) * 3.0)
    phi = phi + c2 * osc2 * decay2

    # Harmonic 3
    osc3 = np.abs(np.sin(tau * 2.0 * np.pi * 3 * P1))
    decay3 = np.power(base, (1.0 - A3) * 3.0)
    phi = phi + c3 * osc3 * decay3

    return np.clip(phi, 0.0, 1.0)


def _harmonic_waveform_k1(
    tau: np.ndarray, P1: float, c1: float, A1: float, baseline: float
) -> np.ndarray:
    """K=1 fundamental-only waveform for reduced fitting."""
    tau = np.asarray(tau, dtype=np.float64)
    base = np.clip(1.0 - tau, 0.0, None)
    osc = np.abs(np.sin(tau * 2.0 * np.pi * P1))
    decay = np.power(base, (1.0 - A1) * 3.0)
    phi = c1 * osc * decay + baseline
    return np.clip(phi, 0.0, 1.0)


def _harmonic_waveform_k2(
    tau: np.ndarray, P1: float, c1: float, A1: float, c2: float, A2: float, baseline: float
) -> np.ndarray:
    """K=2 waveform for reduced fitting."""
    tau = np.asarray(tau, dtype=np.float64)
    base = np.clip(1.0 - tau, 0.0, None)

    osc1 = np.abs(np.sin(tau * 2.0 * np.pi * 1 * P1))
    decay1 = np.power(base, (1.0 - A1) * 3.0)

    osc2 = np.abs(np.sin(tau * 2.0 * np.pi * 2 * P1))
    decay2 = np.power(base, (1.0 - A2) * 3.0)

    phi = c1 * osc1 * decay1 + c2 * osc2 * decay2 + baseline
    return np.clip(phi, 0.0, 1.0)


@dataclass
class HarmonicFitResult:
    """Result of fitting harmonic ADPRS parameters to an entity's trajectory."""

    entity_id: str
    params: Dict[str, float]
    spectral_signature: List[float]  # [c1, c2, c3] harmonic amplitudes
    residual: float  # MSE
    n_points: int
    method: str  # "differential_evolution" or "curve_fit"
    converged: bool
    harmonics: int  # K value used
    prior_params: Optional[Dict[str, float]] = None
    parameter_drift: Optional[Dict[str, float]] = None


class HarmonicFitter:
    """Fits multi-harmonic ADPRS waveform parameters to activation trajectories."""

    def __init__(
        self,
        min_points: int = 5,
        de_maxiter: int = 100,
        de_tol: float = 1e-4,
        de_seed: int = 42,
        min_points_per_harmonic: int = 4,
    ):
        self.min_points = min_points
        self.de_maxiter = de_maxiter
        self.de_tol = de_tol
        self.de_seed = de_seed
        self.min_points_per_harmonic = min_points_per_harmonic

    def _determine_harmonics(self, n_points: int, requested_harmonics: int) -> int:
        """
        Calculate effective K based on available data points.

        Reduces K until n_points >= K * min_points_per_harmonic, with min K=1.
        """
        k = requested_harmonics
        while k > 1 and n_points < k * self.min_points_per_harmonic:
            k -= 1
        return k

    def fit_entity(
        self,
        tau: np.ndarray,
        activation: np.ndarray,
        entity_id: str,
        harmonics: int = 3,
        prior_params: Optional[Dict[str, float]] = None,
    ) -> HarmonicFitResult:
        """
        Fit K=harmonics harmonic ADPRS parameters to a single entity's trajectory.

        If n_points < harmonics * min_points_per_harmonic, reduces K until feasible.
        Warm start (prior_params present): curve_fit for local refinement.
        Cold start (no prior): differential_evolution for global search.
        Falls back to sensible defaults on failure.
        """
        tau = np.asarray(tau, dtype=np.float64)
        activation = np.asarray(activation, dtype=np.float64)
        n_points = len(tau)

        effective_k = self._determine_harmonics(n_points, harmonics)
        if effective_k < harmonics:
            logger.info(
                "Reduced harmonics %d -> %d for %s (n_points=%d, min_per_harmonic=%d)",
                harmonics, effective_k, entity_id, n_points, self.min_points_per_harmonic,
            )

        if prior_params is not None:
            result = self._warm_fit(tau, activation, entity_id, effective_k, prior_params)
        else:
            result = self._cold_fit(tau, activation, entity_id, effective_k)

        # Compute parameter drift if we had priors
        if prior_params is not None:
            drift = {}
            for name in HARMONIC_PARAM_NAMES:
                drift[name] = abs(
                    result.params[name] - prior_params.get(name, HARMONIC_DEFAULT_PARAMS[name])
                )
            result.parameter_drift = drift
            result.prior_params = prior_params

        return result

    def _cold_fit(
        self,
        tau: np.ndarray,
        activation: np.ndarray,
        entity_id: str,
        harmonics: int,
    ) -> HarmonicFitResult:
        """Global optimization via differential_evolution."""
        waveform_fn, bounds, param_names = self._get_fit_config(harmonics)

        try:
            de_result = differential_evolution(
                func=lambda params: np.mean((waveform_fn(tau, *params) - activation) ** 2),
                bounds=bounds,
                maxiter=self.de_maxiter,
                tol=self.de_tol,
                seed=self.de_seed,
            )
            fitted_params = dict(zip(param_names, de_result.x))
            residual = float(de_result.fun)
            converged = de_result.success
        except Exception as e:
            logger.warning("Cold fit failed for %s (K=%d): %s — using defaults", entity_id, harmonics, e)
            fitted_params = {name: HARMONIC_DEFAULT_PARAMS[name] for name in param_names}
            residual = float(
                np.mean((waveform_fn(tau, *[fitted_params[n] for n in param_names]) - activation) ** 2)
            )
            converged = False

        # Expand to full K=3 parameter set
        full_params = self._expand_params(fitted_params, harmonics)
        spectral_signature = [full_params["c1"], full_params["c2"], full_params["c3"]]

        return HarmonicFitResult(
            entity_id=entity_id,
            params=full_params,
            spectral_signature=spectral_signature,
            residual=residual,
            n_points=len(tau),
            method="differential_evolution",
            converged=converged,
            harmonics=harmonics,
        )

    def _warm_fit(
        self,
        tau: np.ndarray,
        activation: np.ndarray,
        entity_id: str,
        harmonics: int,
        prior_params: Dict[str, float],
    ) -> HarmonicFitResult:
        """Local refinement via curve_fit starting from prior parameters."""
        waveform_fn, bounds, param_names = self._get_fit_config(harmonics)

        p0 = [prior_params.get(name, HARMONIC_DEFAULT_PARAMS[name]) for name in param_names]
        lower = [b[0] for b in bounds]
        upper = [b[1] for b in bounds]

        try:
            popt, _ = curve_fit(
                waveform_fn,
                tau,
                activation,
                p0=p0,
                bounds=(lower, upper),
                maxfev=5000,
            )
            fitted_params = dict(zip(param_names, popt))
            residual = float(np.mean((waveform_fn(tau, *popt) - activation) ** 2))
            converged = True
        except Exception as e:
            logger.warning(
                "Warm fit failed for %s (K=%d): %s — falling back to cold fit",
                entity_id, harmonics, e,
            )
            return self._cold_fit(tau, activation, entity_id, harmonics)

        # Expand to full K=3 parameter set
        full_params = self._expand_params(fitted_params, harmonics)
        spectral_signature = [full_params["c1"], full_params["c2"], full_params["c3"]]

        return HarmonicFitResult(
            entity_id=entity_id,
            params=full_params,
            spectral_signature=spectral_signature,
            residual=residual,
            n_points=len(tau),
            method="curve_fit",
            converged=converged,
            harmonics=harmonics,
            prior_params=prior_params,
        )

    def _get_fit_config(
        self, harmonics: int
    ) -> Tuple:
        """
        Return (waveform_fn, bounds, param_names) for the given K.

        K=1: fit P1, c1, A1, baseline (4 params)
        K=2: fit P1, c1, A1, c2, A2, baseline (6 params)
        K=3: fit all 8 params
        """
        if harmonics == 1:
            bounds = [
                (0.5, 8.0),   # P1
                (0.01, 1.0),  # c1
                (0.0, 1.0),   # A1
                (0.0, 1.0),   # baseline
            ]
            param_names = ["P1", "c1", "A1", "baseline"]
            return _harmonic_waveform_k1, bounds, param_names
        elif harmonics == 2:
            bounds = [
                (0.5, 8.0),   # P1
                (0.01, 1.0),  # c1
                (0.0, 1.0),   # A1
                (0.0, 1.0),   # c2
                (0.0, 1.0),   # A2
                (0.0, 1.0),   # baseline
            ]
            param_names = ["P1", "c1", "A1", "c2", "A2", "baseline"]
            return _harmonic_waveform_k2, bounds, param_names
        else:
            return harmonic_adprs_waveform, HARMONIC_PARAM_BOUNDS, HARMONIC_PARAM_NAMES

    def _expand_params(self, fitted_params: Dict[str, float], harmonics: int) -> Dict[str, float]:
        """
        Expand fitted params to full K=3 parameter set, padding missing harmonics with zeros.
        """
        full = dict(HARMONIC_DEFAULT_PARAMS)
        # Zero out higher harmonics by default
        full["c2"] = 0.0
        full["A2"] = 0.5
        full["c3"] = 0.0
        full["A3"] = 0.5
        # Overwrite with actually fitted values
        full.update(fitted_params)
        return full

    @staticmethod
    def spectral_distance(sig_a: List[float], sig_b: List[float]) -> float:
        """
        Cosine distance between two spectral signatures.

        Returns 0.0 for identical signatures, 1.0 for orthogonal.
        Handles zero-vectors gracefully (returns 1.0).
        """
        a = np.asarray(sig_a, dtype=np.float64)
        b = np.asarray(sig_b, dtype=np.float64)

        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)

        if norm_a == 0.0 or norm_b == 0.0:
            return 1.0

        cosine_similarity = np.dot(a, b) / (norm_a * norm_b)
        # Clamp to handle floating-point edge cases
        cosine_similarity = float(np.clip(cosine_similarity, -1.0, 1.0))
        return 1.0 - cosine_similarity
