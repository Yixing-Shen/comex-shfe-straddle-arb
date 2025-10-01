
"""
Baseline straddle-arbitrage signal:
- Rolling mean and std of the IV spread (no Kalman).
- Entry when |z| >= entry_z, exit when |z| <= exit_z or max_hold days reached.
- PnL is proxied using reduction in |deviation from mean| (illustrative),
  and is NOT a full options greeks engine.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Dict

import numpy as np
import pandas as pd

@dataclass
class BaselineConfig:
    window: int = 126
    entry_z: float = 2.0
    exit_z: float = 0.5
    max_hold: int = 10
    trade_cost_bp: float = 8.0   # per entry/exit
    slippage_bp: float = 8.0
    pnl_scale: float = 0.003     # maps deviation shrink to PnL

def backtest_baseline(s: pd.Series, cfg: BaselineConfig = BaselineConfig()) -> Dict:
    s = s.copy()
    roll_mu = s.rolling(cfg.window).mean()
    roll_sd = s.rolling(cfg.window).std().replace(0, np.nan)
    z = (s - roll_mu) / roll_sd

    position = 0
    hold = 0
    daily_pnl = pd.Series(0.0, index=s.index)
    equity = pd.Series(1.0, index=s.index)
    prev_dev = s.iloc[0] - (roll_mu.iloc[0] if not np.isnan(roll_mu.iloc[0]) else 0.0)

    for i in range(1, len(s)):
        if np.isnan(roll_sd.iloc[i]) or np.isnan(roll_mu.iloc[i]):
            equity.iloc[i] = equity.iloc[i-1]
            prev_dev = s.iloc[i] - (roll_mu.iloc[i] if not np.isnan(roll_mu.iloc[i]) else 0.0)
            continue

        dev = s.iloc[i] - roll_mu.iloc[i]
        dev_prev = prev_dev

        # Entries / exits
        if position == 0:
            if z.iloc[i] > cfg.entry_z:
                position = +1; hold = 0
                daily_pnl.iloc[i] -= (cfg.trade_cost_bp + cfg.slippage_bp) / 1e4
            elif z.iloc[i] < -cfg.entry_z:
                position = -1; hold = 0
                daily_pnl.iloc[i] -= (cfg.trade_cost_bp + cfg.slippage_bp) / 1e4
        else:
            hold += 1
            if abs(z.iloc[i]) <= cfg.exit_z or hold >= cfg.max_hold:
                position = 0; hold = 0
                daily_pnl.iloc[i] -= (cfg.trade_cost_bp + cfg.slippage_bp) / 1e4

        # PnL proxy
        if position != 0:
            daily_pnl.iloc[i] += position * (abs(dev_prev) - abs(dev)) * cfg.pnl_scale

        equity.iloc[i] = equity.iloc[i-1] * (1 + daily_pnl.iloc[i])
        prev_dev = dev

    return {
        "equity": equity,
        "daily_ret": daily_pnl,
        "z": z
    }
