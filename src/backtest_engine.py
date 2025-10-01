
"""
Backtest helpers: metrics and a simple runner for baseline/enhanced strategies.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Dict

import numpy as np
import pandas as pd

def annualize_return(daily_returns: pd.Series, trading_days: int = 252) -> float:
    daily_returns = daily_returns.fillna(0.0)
    cum = (1 + daily_returns).prod()
    years = len(daily_returns) / trading_days
    return cum**(1/years) - 1 if years > 0 else 0.0

def sharpe_ratio(daily_returns: pd.Series, trading_days: int = 252) -> float:
    daily_returns = daily_returns.fillna(0.0)
    mu = daily_returns.mean()
    sigma = daily_returns.std(ddof=1)
    return 0.0 if sigma == 0 else (mu * trading_days) / (sigma * np.sqrt(trading_days))

def max_drawdown(equity: pd.Series) -> float:
    eq = equity.fillna(method="ffill")
    peak = eq.cummax()
    dd = eq/peak - 1.0
    return float(dd.min())

def summarize(res: Dict) -> Dict:
    dr = res["daily_ret"]
    eq = res["equity"]
    return {
        "ann_return": annualize_return(dr),
        "sharpe": sharpe_ratio(dr),
        "max_dd": max_drawdown(eq)
    }
