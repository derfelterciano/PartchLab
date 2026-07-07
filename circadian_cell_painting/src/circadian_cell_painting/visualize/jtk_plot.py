from matplotlib.backends.backend_pdf import PdfPages
from .base import VisualizerBase
from matplotlib import pyplot as plt
from ..utils import OscillationResults
from pathlib import Path
import polars as pl
import numpy as np
from matplotlib.axes import Axes
import seaborn as sns
from tqdm import tqdm


class JTKVisualize(VisualizerBase):
    """
    Plots the results of the JTK or eJTK results
    """

    def plot_fit(self, ax: Axes, row: dict) -> None:
        """
        Plots/overlays the fitted curves from the analysis results
        No recalculation needed
        """
        jtk_fitted = np.array(row["jtk_fitted"][0])
        lsq_fitted = np.array(row["lsq_fitted"][0])

        return
