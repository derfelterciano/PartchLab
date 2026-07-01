#!/usr/bin/env python3

import polars as pl
import numpy as np
from numpy.typing import NDArray
from .base import OscillationBase
from ._ejtk_cycle_tools import (
    _build_dist_params,
    compute_best_tau,
    init_ref_cosines,
)
from concurrent.futures import ThreadPoolExecutor


class eJTK_CYCLE(OscillationBase):
    """
    Implements the *empirical* JTK_CYCLE

    https://pmc.ncbi.nlm.nih.gov/articles/PMC4368642/

    [Original JTk_CYCLE](https://pmc.ncbi.nlm.nih.gov/articles/PMC3119870/)

    """

    def __init__(
        self,
        periods: list[int],
        interval: float = 1.0,
        time_offset: float = 0.0,
        start_index: int = 0,
        n_perms: int = 500,
        n_workers: int = 4,
    ):
        self.periods = periods
        self.interval = interval
        self.time_offset = time_offset
        self.start_index = start_index
        self.n_perms = n_perms
        self.n_workers = n_workers

        self._ref_cosines: dict | None = None
        self._dist_params: dict | None = None
        self._n_timepoints: int | None = None

        super().__init__()

    @property
    def params(self):
        return {
            "periods": self.periods,
            "time_interval": self.interval,
            "time_offset": self.time_offset,
            "start_index": self.start_index,
            "n_perms": self.n_perms,
            "period": float(np.mean(self.periods)) * self.interval,
        }

    @property
    def result_schema(self):
        return {
            "p_value": pl.Float64,  # empirical p-value
            "adj_p_jtk": pl.Float64,  # Bonferroni JTK p (reference)
            "period": pl.Float64,  # hours
            "phase_hours": pl.Float64,  # hours to peak within cycle
            "amplitude": pl.Float64,  # Hodges-Lehmann amplitude
            "tau": pl.Float64,  # Kendall tau effect size (0-1)
        }

    def _ejtk_fit_single(
        self,
        values: np.ndarray,
        periods: list[int],
        ref_cosines: dict,
        dist_params: list[dict],
        interval: float,
        n_perms: int,
        n_workers: int,
        rng_seed: int = 123456789,
    ) -> dict | None:
        """
        running eJTK_CYCLE on a single timeseries data

        1. Compute observed tau from real data
        2. Build empirical null by permuting time labels n_perms times
        3. emp_p = fraction of permutations where |tau_perm| >= |tau_obs|

        Args:
            values (np.ndarray): time series data
            periods (list[int]): list of desired periods to test
            ref_cosines (dict): generated reference cosines
            dist_params (list[dict]): null dist parameters
            interval (float): sampling intervals
            n_perms (int): number of permutations (for empirical)
            n_workers (int): number of threads/workers to use
            rng_seed (int, optional): rng seed. Defaults to 123456789.

        Returns:
            dict | None: _description_
        """

        try:
            rng = np.random.default_rng(seed=rng_seed)

            # observed stats
            obs_tau, adj_p, best_per, best_lag, amplitude = compute_best_tau(
                values=values,
                periods=periods,
                ref_cosines=ref_cosines,
                dist_params=dist_params,
            )

            seeds = rng.integers(0, 2**32, size=n_perms)

            def _single_perm(seed: int) -> float:
                perm_vals = np.random.default_rng(seed).permutation(values)
                tau, _, _, _, _ = compute_best_tau(
                    perm_vals, periods, ref_cosines, dist_params
                )
                return tau

            with ThreadPoolExecutor(max_workers=n_workers) as pool:
                perm_taus = np.array(list(pool.map(_single_perm, seeds)))

            # empirical p-values
            emp_p = float(np.mean(perm_taus >= obs_tau))
            emp_p = max(emp_p, 1.0 / n_perms)

            return {
                "p_value": emp_p,
                "adj_p_jtk": adj_p,
                "period": float(best_per) * interval,
                "phase_hours": float(best_lag) * interval,
                "amplitude": amplitude,
                "tau": obs_tau,
            }

        except Exception:
            return None

    def _jtk_init(self, n_timepoints: int) -> None:
        """Lazily precomputing reference cosines and distributions"""

        if self._n_timepoints == n_timepoints:
            return

        self._n_timepoints = n_timepoints
        self._ref_cosines = init_ref_cosines(self.periods, n_timepoints)
        self._dist_params = _build_dist_params(n_timepoints)

    def fit(self, timepoints, values):
        self._jtk_init(len(timepoints))
        return self._ejtk_fit_single(
            values=values,
            periods=self.periods,
            ref_cosines=self._ref_cosines,
            dist_params=self._dist_params,
            interval=self.interval,
            n_perms=self.n_perms,
            n_workers=self.n_workers,
        )
