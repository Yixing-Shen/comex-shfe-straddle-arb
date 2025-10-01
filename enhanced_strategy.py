
"""
Enhanced strategy:
- Kalman Filter to estimate time-varying equilibrium for IV spread
- Model-based z-score thresholds
- Event-day blocking, stop-loss, position caps (simplified in backtest)
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Dict
import numpy as np
import pandas as pd

from .kalman_filter import KFConfig, kalman_filter, zscore

@dataclass
class EnhancedConfig:
    entry_k: float = 2.0
    exit_k: float = 0.5
    stop_k: float = 1.0
    max_hold: int = 10
    pnl_scale: float = 0.0032
    trade_cost_bp: float = 8.0
    slippage_bp: float = 8.0
    kf: KFConfig = KFConfig(Q=0.02, R=0.12, F=1.0, huber_c=3.0)
    event_skip_ratio: float = 0.03  # percentage of days as macro-event blocks

def backtest_enhanced(y: pd.Series, cfg: EnhancedConfig = EnhancedConfig()) -> Dict:
    x, S = kalman_filter(y, cfg.kf)
    z = zscore(y, x, S)

    # Randomly simulate event blocks for demo; in real usage, supply actual calendar.
    rng = np.random.default_rng(17)
    skip_mask = pd.Series(False, index=y.index)
    skip_idx = rng.choice(np.arange(10, len(y)-10), size=int(len(y) * cfg.event_skip_ratio), replace=False)
    skip_mask.iloc[skip_idx] = True

    position = 0; hold = 0; entry_z = None
    daily_pnl = pd.Series(0.0, index=y.index)
    equity = pd.Series(1.0, index=y.index)

    prev_dev = (y.iloc[0] - x.iloc[0])

    for i in range(1, len(y)):
        dev = (y.iloc[i] - x.iloc[i]); dev_prev = prev_dev
        can_enter = not skip_mask.iloc[i]

        if position == 0 and can_enter:
            if z.iloc[i] > cfg.entry_k:
                position = +1; hold = 0; entry_z = z.iloc[i]
                daily_pnl.iloc[i] -= (cfg.trade_cost_bp + cfg.slippage_bp) / 1e4
            elif z.iloc[i] < -cfg.entry_k:
                position = -1; hold = 0; entry_z = z.iloc[i]
                daily_pnl.iloc[i] -= (cfg.trade_cost_bp + cfg.slippage_bp) / 1e4
        elif position != 0:
            hold += 1
            # Stop-loss on further sigma worsening
            if (position==+1 and z.iloc[i] > entry_z + cfg.stop_k) or (position==-1 and z.iloc[i] < entry_z - cfg.stop_k):
                position = 0; hold = 0; entry_z = None
                daily_pnl.iloc[i] -= (cfg.trade_cost_bp + cfg.slippage_bp) / 1e4
            # Exit on reversion or time stop
            elif abs(z.iloc[i]) <= cfg.exit_k or hold >= cfg.max_hold:
                position = 0; hold = 0; entry_z = None
                daily_pnl.iloc[i] -= (cfg.trade_cost_bp + cfg.slippage_bp) / 1e4

        # PnL proxy: benefit when |deviation| shrinks
        if position != 0:
            daily_pnl.iloc[i] += position * (abs(dev_prev) - abs(dev)) * cfg.pnl_scale

        equity.iloc[i] = equity.iloc[i-1] * (1 + daily_pnl.iloc[i])
        prev_dev = dev

    return {"equity": equity, "daily_ret": daily_pnl, "z": z, "x": x, "S": S}
