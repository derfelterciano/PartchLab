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
