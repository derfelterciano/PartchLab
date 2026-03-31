#!/usr/bin/env python3

import polars as pl
import numpy as np
from numpy.typing import NDArray
from .base import OscillationBase
from scipy.optimize import curve_fit
from scipy.stats import f


class CosinorDetection(OscillationBase):
    """
    Implements a simple cosinor detection method for circadian data
    https://pmc.ncbi.nlm.nih.gov/articles/PMC3663600/#S4

    Params:
        - period (int): period of time to detect (default: 24 hours)
        - intervals (int): the interval of each timepoint in hours (default: 1 hour)

    """

    def __init__(self, period: int = 24, intervals: int = 1) -> None:
        self.period = period
        self.intervals = intervals
        super().__init__()

    @property
    def params(self) -> dict:
        return {"period": self.period, "time_interval": self.intervals}

    def fit(
        self, timepoints: NDArray[np.float64], values: NDArray[np.float64]
    ) -> dict | None:
        try:
            timepoints = timepoints * self.intervals
            popt, _pcov = curve_fit(
                self._cosinor,
                timepoints,
                values,
                p0=[np.mean(values), np.std(values), 0],
            )

            residual_model = values - self._cosinor(timepoints, *popt)
            residual_null = values - np.mean(values)

            ss_model = np.sum(residual_model**2)
            ss_null = np.sum(residual_null**2)

            n = len(values)
            f_stat = ((ss_null - ss_model) / 2) / (ss_model / (n - 3))
            p_value = 1 - f.cdf(f_stat, 2, n - 3)

            return {
                "baseline": popt[0],
                "amplitude": abs(popt[1]),
                "phase": popt[2] % (2 * np.pi),
                "p_value": p_value,
                "f_stat": f_stat,
                "ss_model": ss_model,
                "ss_null": ss_null,
                "fitted": self._cosinor(timepoints, *popt).tolist(),
            }

        except RuntimeError:
            return None

    @property
    def result_schema(self) -> dict[str, pl.DataType]:
        return {
            "baseline": pl.Float64(),
            "amplitude": pl.Float64(),
            "phase": pl.Float64(),
            "p_value": pl.Float64(),
            "f_stat": pl.Float64(),
            "ss_model": pl.Float64(),
            "ss_null": pl.Float64(),
            "fitted": pl.List(pl.Float64()),
        }

    def _cosinor(
        self, time: NDArray[np.float64], baseline: float, amplitude: float, phase: float
    ):
        """Cosinor equation"""
        return baseline + (
            amplitude * np.cos(((2 * np.pi * time) / self.period) - phase)
        )
