"""Race to the Finish: distance-to-lead, days remaining, simulated title odds."""

from __future__ import annotations

import datetime

import numpy as np
import pandas as pd

from smfd.compute.predictions import simulate_next_week
from smfd.config import GAME_END

TREND_WINDOW = 30        # trailing trading days for the trend column
RACE_SIMS = 2000         # simulated seasons for title/last-place odds
ALIVE_ODDS = 1 / 200     # "still alive" = at least a 1-in-200 simulated title shot


def days_remaining(today: datetime.date | None = None) -> int:
    today = today or datetime.date.today()
    return max((GAME_END - today).days, 0)


def trading_days_remaining(today: datetime.date | None = None) -> int:
    """Rough trading-day count to the finish (weekdays; holidays are noise here)."""
    today = today or datetime.date.today()
    return max(int(np.busday_count(today, GAME_END)), 0)


def race_table(total_returns: pd.DataFrame, scores: pd.DataFrame,
               today: datetime.date | None = None,
               n_sims: int = RACE_SIMS) -> pd.DataFrame:
    """Per-pick race stats, in leaderboard order.

    Columns: total_return_pct, gap_to_leader (pp), gap_to_safety (pp above last
    place), trend_per_day (trailing-30d slope), title_odds / last_odds
    (probability of finishing #1 / last on the final day, from bootstrap
    Monte Carlo of the remaining trading days — same engine as the weekly
    predictions), can_catch_leader (title_odds >= ALIVE_ODDS).
    """
    if total_returns.empty or scores.empty:
        return pd.DataFrame()
    current = scores["total_return_pct"]
    leader_ret = current.max()
    last_ret = current.min()
    remaining = trading_days_remaining(today)

    window = total_returns.iloc[-min(TREND_WINDOW, len(total_returns)):]
    x = np.arange(len(window))

    tickers, finals = simulate_next_week(
        total_returns, n_sims=n_sims, horizon=max(remaining, 1))
    n = finals.shape[0]
    title_odds = pd.Series(
        np.bincount(finals.argmax(axis=1), minlength=len(tickers)) / n, index=tickers)
    last_odds = pd.Series(
        np.bincount(finals.argmin(axis=1), minlength=len(tickers)) / n, index=tickers)

    rows = {}
    for t in scores.index:
        series = window[t].values
        slope = float(np.polyfit(x, series, 1)[0]) if len(series) >= 2 else 0.0
        rows[t] = {
            "total_return_pct": float(current[t]),
            "gap_to_leader": float(leader_ret - current[t]),
            "gap_to_safety": float(current[t] - last_ret),
            "trend_per_day": slope,
            "title_odds": float(title_odds.get(t, 0.0)),
            "last_odds": float(last_odds.get(t, 0.0)),
            "can_catch_leader": bool(title_odds.get(t, 0.0) >= ALIVE_ODDS),
        }
    df = pd.DataFrame.from_dict(rows, orient="index")
    return df.sort_values("total_return_pct", ascending=False)


def milestones(today: datetime.date | None = None) -> dict:
    today = today or datetime.date.today()
    from smfd.config import GAME_START
    total = (GAME_END - GAME_START).days
    elapsed = (today - GAME_START).days
    return {
        "days_remaining": days_remaining(today),
        "trading_days_remaining": trading_days_remaining(today),
        "days_elapsed": max(elapsed, 0),
        "pct_complete": min(max(elapsed / total * 100, 0), 100) if total else 0,
        "end_date": GAME_END,
    }
