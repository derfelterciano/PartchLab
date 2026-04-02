#!/usr/bin/env python3

from circadian_rhythms.live_cell_painting.data_processing.osc_detection import heat_data
from .base import VisualizerBase
from matplotlib import pyplot as plt
from ..utils import OscillationResults
from pathlib import Path
import polars as pl
import numpy as np
from matplotlib.axes import Axes
import seaborn as sns


class CosinorVisualize(VisualizerBase):
    """
    Plots the result of the cosinor calculations
    """

    def plot_fit(self, ax: Axes, row: dict) -> None:
        """
        Plots/overlays the fitted curves from the analysis results
        No recalculation needed
        """
        fitted = np.array(row["fitted"])
        n = len(fitted)
        hours = np.arange(n) * self.results.time_interval

        ax.plot(
            hours,
            fitted,
            "-",
            color="crimson",
            linewidth=2,
            label=(
                f"cosinor fit\t"
                f"amp={row['amplitude']:.4f}\t"
                f"phase={np.degrees(row['phase'])} degrees"
            ),
        )

        return

    def plot_summary(self, ax, significant: pl.DataFrame) -> None:
        """
        Heatmap of amplitude, phase, p_adjusted for all significant feats
        """
        heat_data = (
            significant.select(
                [self.results.feature_col, "amplitude", "phase", "p_adjusted"]
            )
            .to_pandas()
            .set_index(self.results.feature_col)
        )

        sns.heatmap(heat_data, ax=ax, cmap="viridis", annot=True, fmt=".3f")
        ax.set_title(
            f"Significant Features Summary - metric: {self.results.stat} | "
            f"(p-vals <={self.results.adj_alpha} (adjusted)"
        )
        return

    def view(self, out_dir: Path, alpha: float | None = None) -> None:
        return
