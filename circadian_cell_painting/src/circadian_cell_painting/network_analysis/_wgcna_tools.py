#!/usr/bin/env python3
"""
Low level routines and helpers for WGCNA
"""

from __future__ import annotations

import numpy as np
import polars as pl
from scipy.cluster.hierarchy import linkage, fcluster
from scipy.spatial.distance import squareform
from scipy.stats import rankdata

# -- Correlation / Redundancy


def _biweight_standardize(matrix: np.ndarray, c: float = 9.0) -> np.ndarray:
    """
    Robust standardization for biweight midcorrelation (bicor).
    Replaces mean/std centering with median/MAD centering, then down-weights
    outliers via Tukey's biweight function before unit-normalizing each
    column — so a plain dot product between columns gives the correlation.
    """
    med = np.median(matrix, axis=1, keepdims=True)  # per feature (row)
    mad = np.median(np.abs(matrix - med), axis=1, keepdims=True)
    mad = np.where(mad == 0, np.finfo(float).eps, mad)

    u = (matrix - med) / (c * mad)
    weights = np.where(np.abs(u) < 1, (1 - u**2) ** 2, 0.0)

    standardized = (matrix - med) * weights
    norms = np.sqrt(np.sum(standardized**2, axis=1, keepdims=True))  # per row
    norms = np.where(norms == 0, np.finfo(float).eps, norms)

    return standardized / norms


def correlation_matrix(matrix: np.ndarray, method: str = "pearson") -> np.ndarray:
    """
    Calculate the correlation matrix for a given matrix of (Features x Timepoints)

    Args:
        matrix (np.ndarray): Input matrix
        method (str, optional): selects the correlation method.
        Defaults to "pearson".

    Returns:
        np.ndarray: nxn Correlation matrix
    """
    if method == "pearson":
        corr = np.corrcoef(matrix)
    elif method == "spearman":
        ranks = rankdata(matrix, axis=1)
        corr = np.corrcoef(ranks)
    else:
        z = _biweight_standardize(matrix)
        corr = z @ z.T

    corr = np.nan_to_num(corr, nan=0.0)
    np.fill_diagonal(corr, 1.0)
    return corr


def find_redundant_feats(
    corr: np.ndarray, feature_names: list[str], threshold: float = 0.99
) -> dict[str, str]:
    """
    Identifies near-duplicate features (|r| > threshold) and maps each
    redundant feature to the representative feature it should collapse to.
    Representative = the first feature (by column order) in each redundant group.

    args:
        corr (np.ndarray): feature x feature correlation matrix
        feature_names (list[str]): names aligned with corr's rows/columns
        threshold (float): |r| above which two features are considered
            near-duplicates (default 0.99)

    returns:
        dict[str, str]: {redundant_feature: representative_feature}
        (features not in this dict are unique / kept as-is)
    """
    n = len(feature_names)
    redundant_map: dict[str, str] = {}
    assigned = np.zeros(n, dtype=bool)

    for i in range(n):
        if assigned[i]:
            continue

        # find all j that are near-duplicates of i and not yet claimed
        dup_mask = (np.abs(corr[i]) > threshold) & (~assigned)
        dup_mask[i] = False
        dup_idx = np.where(dup_mask)[0]

        if len(dup_idx) > 0:
            representative = feature_names[i]
            for j in dup_idx:
                redundant_map[feature_names[j]] = representative
                assigned[j] = True
            assigned[i] = True
    return redundant_map


# -- Soft power


def scale_free_fit_index(
    adjacency: np.ndarray, n_bins: int = 20
) -> tuple[float, float]:
    """
    Computes the scale-free topology fit R^2 for 1 adjacency matrix
    which is the diagnostic used to justify a soft-power choice.

    Args:
        adjacency (np.ndarray): adjacency matrix
        n_bins (int, optional): number of bins for histogram. Defaults to 20.

    Returns:
        tuple[float, float]: [signed r^2, mean k]
    """

    k = adjacency.sum(axis=1)
    mean_k = float(np.mean(k))

    if np.all(k <= 0) or np.std(k) == 0:
        return 0.0, mean_k

    # bin the degree distribution, then check if log(p(k)) vs log(k) is linear
    # — that linear relationship IS the definition of "scale-free"
    hist, bin_edges = np.histogram(k, bins=n_bins)
    bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2

    valid = (hist > 0) & (bin_centers > 0)
    if valid.sum() > 3:
        return 0.0, mean_k

    log_p = np.log10(hist[valid] / hist[valid].sum())
    log_k = np.log10(bin_centers[valid])

    slope, intercept = np.polyfit(log_k, log_p, 1)
    fitted = slope * log_k + intercept
    ss_res = np.sum((log_p - fitted) ** 2)
    ss_tot = np.sum((log_p - np.mean(log_p)) ** 2)
    r_squared = 1 - ss_res / ss_tot if ss_tot > 0 else 0.0

    # sign(slope) -> a real scale-free network has a negative slope
    # (few hubs, many low-degree features) - positive slope means
    # power is doing something backwards
    signed_r2 = float(np.sign(slope) * r_squared)

    return signed_r2, mean_k


def pick_soft_threshold(
    corr: np.ndarray, powers: list[int] | None = None, signed: bool = True
) -> pl.DataFrame:
    """
    Scans candidate soft-thresholing powers, returns the scale-free fit
    diagnostic table for the user to plot and manually choose beta.

    Args:
        corr (np.ndarray): correlation matrix
        powers (list[int] | None, optional): List of numerical powers. Defaults to None.
        signed (bool, optional): is the correlation is signed. Defaults to True.


    Returns:
        pl.DataFrame: _description_
    """

    if powers is None:
        powers = list(range(1, 21))

    rows = []
    for power in powers:
        adj = adjacency_matrix(corr=corr, power=power, signed=signed)
        np.fill_diagonal(adj, 0.0)
        r2, mean_k = scale_free_fit_index(adj)
        rows.append({"power": power, "signed_r2": r2, "mean_connectivity": mean_k})

    return pl.DataFrame(rows)


# -- Adjacency / topological overlay matrix


def adjacency_matrix(corr: np.ndarray, power: int, signed: bool = True) -> np.ndarray:
    """
    Converts a correlation matrix into a weighted adj. matrix

    Args:
        corr (np.ndarray): Correlation matrix
        power (int): raises the matrix to a certain power
        signed (bool):
                signed=True:   adjacency = ((1 + corr) / 2) ^ power
                   maps corr from [-1, 1] to [0, 1] first, so a perfect
                   negative correlation (r=-1) gets adjacency ~0, and a
                   perfect positive correlation (r=1) gets adjacency ~1.
                   Antiphase features (peak at CT0 vs CT12) end up weakly
                   connected — appropriate for circadian data, since
                   peak-vs-trough timing is a real biological distinction,
                   not just sign noise.

                signed=False:  adjacency = |corr| ^ power
                    treats r=-0.9 and r=+0.9 as EQUALLY strongly connected.
                    Antiphase features would get merged into the same module,
                    which is usually not what you want for rhythm data.

    Returns:
        np.ndarray: weighted adjacency matrix
    """

    if signed:
        adj = ((1 + corr) / 2) ** power
    else:
        adj = np.abs(corr) ** power

    np.fill_diagonal(adj, 0.0)
    return adj


def topological_overlap_matrix(adjacency: np.ndarray) -> np.ndarray:
    """
    Converts an adjacency matrix into a Topological Overlap Matrix (TOM).

    TOM_ij = (sum_k(a_ik * a_kj) + a_ij) / (min(k_i, k_j) + 1 - a_ij)

    Intuition:
      - sum_k(a_ik * a_kj)  = how much i and j share the SAME neighbors
                              (high if both are strongly connected to
                               the same third features)
      - a_ij                = their own direct connection strength
      - min(k_i, k_j)        = normalizes by whichever feature has fewer
                               total connections, so TOM stays bounded
                               regardless of how "popular" a hub feature is

    Diagonal is set to 1 by convention — a feature has perfect overlap
    with itself.

    Args:
        adjacency (np.ndarray): Adjacency matrix

    Returns:
        np.ndarray: Topological overlap matrix
    """
    n = adjacency.shape[0]
    a = adjacency.copy()
    np.fill_diagonal(a, 0.0)

    k = a.sum(axis=1)  # each feats connectivity / degree
    l_matrix = a @ a  # matmul gives us sum_k(a_ik * a_kj) for ALL i,j pairs at once

    k_i = k[:, None]
    k_j = k[None, :]
    min_k = np.minimum(k_i, k_j)

    denom = min_k + 1 - a
    denom[denom == 0] = np.finfo(float).eps  # avoid divide by 0

    tom = (l_matrix + a) / denom
    np.fill_diagonal(tom, 1.0)

    tom = np.clip(tom, 0.0, 1.0)
    return tom
