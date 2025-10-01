
"""
Kalman Filter utilities for IV-spread equilibrium estimation.

We use a simple random-walk state model by default:
    x_t = x_{t-1} + w_t,     w_t ~ N(0, Q)
    y_t = x_t + v_t,         v_t ~ N(0, R)

Optionally, pass AR(1) coefficient F != 1.0 to allow mean reversion in state.
Robust update via Huber clipping is supported.
"""

from __future__ import annotations
import math
from dataclasses import dataclass
from typing import Tuple

import numpy as np
import pandas as pd

@dataclass
class KFConfig:
    Q: float = 0.02      # process noise variance
    R: float = 0.10      # observation noise variance
    F: float = 1.0       # state transition (1.0=random walk, <1.0=AR(1))
    huber_c: float = 3.0 # Huber clipping threshold in std units

def kalman_filter(y: pd.Series, cfg: KFConfig = KFConfig()) -> Tuple[pd.Series, pd.Series]:
    """
    Run Kalman filter on observed series y to estimate latent equilibrium x and innovation variance S.
    Returns:
        x: pd.Series, filtered state mean
        S: pd.Series, innovation variance each step (used to compute z-score)
    """
    if not isinstance(y, pd.Series):
        raise TypeError("y must be a pandas Series")

    n = len(y)
    x = np.zeros(n); P = np.zeros(n); S_arr = np.zeros(n)

    # initialize
    x[0] = y.iloc[0] if not np.isnan(y.iloc[0]) else 0.0
    P[0] = 1.0

    for i in range(1, n):
        # Predict
        x_pred = cfg.F * x[i-1]
        P_pred = cfg.F * P[i-1] * cfg.F + cfg.Q

        # Update
        yi = y.iloc[i]
        if np.isnan(yi):
            x[i] = x_pred
            P[i] = P_pred
            S_arr[i] = P_pred + cfg.R
            continue

        nu = yi - x_pred
        S = P_pred + cfg.R

        # Robust Huber clipping
        c = cfg.huber_c * math.sqrt(S)
        if nu > c: nu = c
        elif nu < -c: nu = -c

        K = P_pred / S
        x[i] = x_pred + K * nu
        P[i] = (1.0 - K) * P_pred
        S_arr[i] = S

    idx = y.index
    return pd.Series(x, index=idx), pd.Series(S_arr, index=idx)

def zscore(y: pd.Series, x: pd.Series, S: pd.Series) -> pd.Series:
    """Model-based z-score using filter-implied uncertainty."""
    return (y - x) / np.sqrt(S)
