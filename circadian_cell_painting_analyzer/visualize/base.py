#!/usr/bin/env python3

from matplotlib.axes import Axes
import polars as pl
from abc import ABC, abstractmethod
from pathlib import Path
from ..utils import OscillationResults


class VisualizerBase(ABC):
    """
    This will be the base used for all visualization classes
    """

    def __init__(self, results: OscillationResults):
        self.results = results

    def plot_timeseries(self, ax: Axes, well: str, feature: str) -> None:
        """
        This plots the raw (but detrended) timeseries data.
        args:
            - ax: matplotlib axes
            - well (str): the well name
            - feature (str): the feature name
        """
        clean_data = (
            self.results.scan_data()
            .filter(
                (pl.col(self.results.well_col) == well)
                & (pl.col(self.results.feature_col) == feature)
            )
            .select([self.results.timepoint_col, self.results.value_col])
            .sort(self.results.timepoint_col)
            .collect()
        )

        hours = (
            clean_data[self.results.timepoint_col].to_numpy()
            * self.results.time_interval
        )
        values = clean_data[self.results.value_col].to_numpy()

        ax.plot(
            hours,
            values,
            "-o",
            color="royalblue",
            markersize=4,
            linewidth=5,
            label="detrended data",
        )
        ax.axhline(0, color="gray", linewidth=0.5, linestyle="--")
        ax.set_xlabel("Time (hours)")
        ax.set_ylabel(f"Detrended {self.results.stat}")

    def get_significant(self, alpha: float | None = None) -> pl.DataFrame:
        """
        Returns all results with p_adjusted values <= alpha.
        This filters out all the non-significant data giving you real
        oscilating results.

        args:
            - alpha (float | None): the alpha value to filter out the p-values
            by

        returns:
            pl.DataFrame: all the results with p values <= alpha.
        """
        threshold = alpha if alpha is not None else self.results.adj_alpha
        return (
            self.results.scan_results()
            .filter(pl.col("p_adjusted") <= threshold)
            .collect()
        )

    @abstractmethod
    def plot_fit(self, ax, row: dict) -> None:
        """
        Overlays the model fit on a time series plot.
        Method specific — must be implemented by each visualizer.
        args:
            - ax: matplotlib axes object to plot on
            - row (dict): a single row from the results dataframe
                containing model parameters (amplitude, phase, etc.)
        """
        ...

    @abstractmethod
    def plot_summary(self, ax, significant: pl.DataFrame) -> None:
        """
        Plots a summary of all significant features for a single well.
        Method specific — must be implemented by each visualizer.
        args:
            - ax: matplotlib axes object to plot on
            - significant (pl.DataFrame): filtered results dataframe
        """
        ...

    def view(
        self,
        out_dir: Path,
        alpha: float | None = None,
    ) -> None:
        """
        Generates one PDF per well containing:
            - Page 1: summary of all significant features
            - Page N: one page per significant feature
        args:
            - out_dir (Path): directory to write PDFs to
            - alpha (float | None): significance threshold,
                defaults to results.adj_alpha
        """
        ...
