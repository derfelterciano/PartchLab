#!/usr/bin/env python3
"""
A file of utilitis for this project
"""

from pathlib import Path
import shutil
from time import sleep
from dataclasses import dataclass
import polars as pl
import pickle
from typing import Any


def clean_folder(dir: Path) -> None:
    if dir.exists():
        shutil.rmtree(dir)
        sleep(0.5)
    dir.mkdir(parents=True, exist_ok=True)


def cosinor_fitted_long(
    results_lf: pl.LazyFrame,
    timepoints: list[float | int],
    timepoint_col: str,
    feature: str | None = None,
    feature_col: str = "feature",
) -> pl.DataFrame:
    """
    Returns the results of ONLY the cosinor analysis with the fitted
    column in long form

    Args:
        results_lf (pl.LazyFrame): A Lazy fram for the results of the cosinor
            analysis
        feature (str | None, optional): A specific feature to select. Defaults to None.

    Returns:
        _type_: Returns a dataframe with the exploded fitted column
    """
    if "fitted" not in results_lf.collect_schema().names():
        raise KeyError(f"This is not a cosinor dataset as 'fitted' is not a column!")

    if feature is not None:
        results_lf = results_lf.filter(pl.col(feature_col) == feature)

    results = results_lf.collect()

    return results.with_columns(
        pl.Series(timepoint_col, [timepoints] * len(results))
    ).explode(["fitted", timepoint_col])


@dataclass
class OscillationResults:
    """
    Bundles the output of detect() into a central class!
    Great for portability of meta information
    *NOTE:* This class does not contain the actual data itself.
    It contains only the meta information and file paths
    """

    # columns metadata
    well_col: str
    feature_col: str
    timepoint_col: str
    value_col: str
    stat: str

    # model params
    detector_params: dict[str, Any]

    # paths
    results_path: Path
    data_path: Path
    platemap: Path | pl.DataFrame | None = None

    # detction metrics
    detector_name: str = "CosinorFitting"
    adj_alpha: float = 0.05
    adj_method: str = "fdr_bh"
    correction_group: list[str] | None = None

    def scan_data(self):
        return pl.scan_parquet(self.data_path)

    def scan_results(self):
        return pl.scan_parquet(self.results_path)

    def load_result(self):
        return pl.read_parquet(self.results_path)

    def to_pickle(self, path: Path) -> None:
        """
        Saves this object as a pickle file
        """

        with open(path, "wb") as f:
            pickle.dump(self, f)

    @property
    def params(self):
        return self.detector_params

    @classmethod
    def load_pickle(cls, path: Path) -> "OscillationResults":
        with open(path, "rb") as f:
            return pickle.load(f)
