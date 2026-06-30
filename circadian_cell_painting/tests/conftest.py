#!/usr/bin/env python3
"""
This is a config for all our tests
"""

import pytest
from circadian_cell_painting.osc_detection._ejtk_cycle_tools import (
    compute_best_tau,
    init_ref_cosines,
    _build_dist_params,
    hlm,
    _s_to_pvalue,
)
import numpy as np


@pytest.fixture
def dp_small():
    """small n distribution params"""
    return _build_dist_params(12)


@pytest.fixture
def dp_medium():
    """medium n for dist params"""
    return _build_dist_params(24)


@pytest.fixture
def dp_large():
    """large n for dist params (this may trigger normal approx)"""
    return _build_dist_params(200)


@pytest.fixture
def ref_24tp(periods):
    return init_ref_cosines(periods, 24)


@pytest.fixture
def ref_48tp(periods):
    return init_ref_cosines(periods, 48)


@pytest.fixture
def periods():
    return list(range(10, 15))


@pytest.fixture
def ref_cosines_48(periods):
    return init_ref_cosines(periods, 48)


@pytest.fixture
def dist_params_48():
    return _build_dist_params(48)


@pytest.fixture
def clean_cosine_24h():
    """Clean 24h cosine @ 2h intervals, n=48"""
    t = np.arange(0, 96, 2, dtype=float)
    return np.cos(2 * np.pi * t / 24)


@pytest.fixture
def flat_signal():
    return np.ones(48)
