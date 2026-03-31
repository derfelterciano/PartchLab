#!/usr/bin/env python3
"""
A file of utilitis for this project
"""

from pathlib import Path
import shutil
from time import sleep
from dataclasses import dataclass
import polars as pl


def clean_folder(dir: Path) -> None:
    if dir.exists():
        shutil.rmtree(dir)
        sleep(0.5)
    dir.mkdir(parents=True, exist_ok=True)


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

    # paths
    results_path: Path
    data_path: Path
    platemap: Path | pl.DataFrame | None = None

    # detction metrics
    detector_name: str = "CosinorFitting"
    period: float = 24
    time_interval: float = 1
    adj_alpha: float = 0.05
    adj_method: str = "fdr_bh"
    correction_group: list[str] | None = None

    def scan_data(self):
        return pl.scan_parquet(self.data_path)

    def scan_results(self):
        return pl.scan_parquet(self.results_path)

    def load_result(self):
        return pl.read_parquet(self.results_path)
