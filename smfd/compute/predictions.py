"""Research-grounded 'predictions' + accuracy tracking. Not financial advice —
the disclaimer is part of the feature.

How it works: each pick's actual daily returns over the whole game are
bootstrap-resampled to simulate thousands of possible next weeks, starting
from today's standings. A card's confidence is the fraction of simulated
weeks in which its claim came true — so "90% confidence last place" can only
appear for a pick that is genuinely within striking distance of the bottom.
Technical signals (RSI / SMA crossovers) tilt the simulated drift slightly,
and earnings within the forecast window widen that pick's outcome spread.
"""

from __future__ import annotations

import datetime
import json

import numpy as np
import pandas as pd

from smfd.config import GROUP_EMOJI, PREDICTION_HISTORY_PATH

N_SIMS = 4000
HORIZON = 5  # trading days ≈ one week

# Momentum is weakly persistent at best — historical drift is shrunk hard
# toward zero rather than extrapolated, and the technical-signal tilt is
# deliberately small (score is -3..+3, so at most ±0.15%/day). Beyond about
# a trading month even that shrunk drift stops compounding (long-horizon
# sims like the title race would otherwise extrapolate momentum for a year).
DRIFT_FULL_WEIGHT = 0.30
DRIFT_RECENT_WEIGHT = 0.20
SIGNAL_TILT = 0.0005
EARNINGS_VOL_MULT = 1.3
DRIFT_PERSIST_DAYS = 21


def _days_to_earnings(earnings: dict, ticker: str, today: datetime.date):
    """Days until the next earnings date ('Jun 18' style), or None."""
    raw = ((earnings or {}).get(ticker) or {}).get("next_date") or ""
    for year in (today.year, today.year + 1):
        try:
            d = datetime.datetime.strptime(f"{raw} {year}", "%b %d %Y").date()
        except ValueError:
            continue
        if d >= today:
            return (d - today).days, raw
    return None, raw


def simulate_next_week(daily: pd.DataFrame, signals: dict | None = None,
                       earnings_soon: dict | None = None,
                       n_sims: int = N_SIMS, horizon: int = HORIZON,
                       seed: int | None = None) -> tuple[list, np.ndarray]:
    """Bootstrap-simulate each pick's total return % *horizon* trading days out.

    *daily* is the cumulative total-return-% frame (rows=dates, cols=tickers).
    Returns (tickers, finals) where finals is (n_sims, n_tickers) of simulated
    end-of-week total return %. Seeded by the data's last date by default so
    the cards are stable across page reloads and only change with fresh data.
    """
    tickers = list(daily.columns)
    if seed is None:
        seed = int(pd.Timestamp(daily.index[-1]).strftime("%Y%m%d"))
    rng = np.random.default_rng(seed)
    # Work in log-value space so a pick at +200% gets proportionally larger
    # point swings than one at +10% — bootstrapping raw percentage-point
    # changes would not be scale-invariant.
    logv = np.log((1.0 + daily / 100.0).clip(lower=1e-6))
    finals = np.empty((n_sims, len(tickers)))
    for j, t in enumerate(tickers):
        series = logv[t].dropna().values
        cur = series[-1] if len(series) else 0.0
        lr = np.diff(series)
        lr = lr[np.isfinite(lr)]
        if len(lr) < 5:
            finals[:, j] = (np.exp(cur) - 1) * 100
            continue
        mean_all = lr.mean()
        score = ((signals or {}).get(t) or {}).get("score") or 0
        drift = (DRIFT_FULL_WEIGHT * mean_all
                 + DRIFT_RECENT_WEIGHT * lr[-10:].mean()
                 + SIGNAL_TILT * score)
        shocks = rng.choice(lr - mean_all, size=(n_sims, horizon), replace=True)
        if (earnings_soon or {}).get(t):
            shocks = shocks * EARNINGS_VOL_MULT
        drift_days = min(horizon, DRIFT_PERSIST_DAYS)
        finals[:, j] = (np.exp(cur + shocks.sum(axis=1) + drift * drift_days) - 1) * 100
    return tickers, finals


def _conf(p: float) -> int:
    return int(max(1, min(99, round(p * 100))))


def generate_predictions(total_returns: pd.DataFrame, scores: pd.DataFrame,
                         name_map: dict, group_map: dict,
                         signals: dict | None = None, earnings: dict | None = None,
                         today: datetime.date | None = None) -> list:
    """Cards backed by Monte Carlo simulation of the next trading week."""
    daily = total_returns
    if len(daily) < 6 or daily.empty:
        return []
    today = today or datetime.date.today()
    final_returns = scores["total_return_pct"]

    earnings_soon, earnings_label = {}, {}
    for t in daily.columns:
        days, raw = _days_to_earnings(earnings or {}, t, today)
        if days is not None and days <= 7:
            earnings_soon[t] = True
            earnings_label[t] = raw

    tickers, finals = simulate_next_week(daily, signals, earnings_soon)
    idx = {t: j for j, t in enumerate(tickers)}
    n_sims = finals.shape[0]

    current = daily.iloc[-1]
    changes = finals - current.reindex(tickers).values  # simulated weekly move, in pts
    p_first = pd.Series(np.bincount(finals.argmax(axis=1), minlength=len(tickers)) / n_sims,
                        index=tickers)
    p_last = pd.Series(np.bincount(finals.argmin(axis=1), minlength=len(tickers)) / n_sims,
                       index=tickers)
    p_up_week = pd.Series((changes > 0).mean(axis=0), index=tickers)
    p_biggest_move = pd.Series(
        np.bincount(np.abs(changes).argmax(axis=1), minlength=len(tickers)) / n_sims,
        index=tickers)

    def _emoji(t):
        return GROUP_EMOJI.get(group_map.get(t, ""), "")

    def _rsi_note(t):
        rsi = ((signals or {}).get(t) or {}).get("rsi")
        sig = ((signals or {}).get(t) or {}).get("signal")
        parts = []
        if rsi is not None:
            tag = " oversold" if rsi < 30 else (" overbought" if rsi > 70 else "")
            parts.append(f"RSI {rsi:.0f}{tag}")
        if sig and sig != "HOLD":
            parts.append(f"{sig} signal")
        return " · ".join(parts)

    def _earnings_note(t):
        return f"\U0001f4c5 earnings {earnings_label[t]}" if t in earnings_soon else ""

    def _detail(lead, t):
        bits = [lead] + [b for b in (_rsi_note(t), _earnings_note(t)) if b]
        return " · ".join(bits)

    predictions = []

    mvp = p_first.idxmax()
    rank_now = list(final_returns.index).index(mvp) + 1 if mvp in final_returns.index else 0
    predictions.append({
        "icon": "\U0001f451", "title": "Predicted MVP", "ticker": mvp,
        "name": name_map.get(mvp, mvp),
        "detail": _detail(
            f"Finishes #1 in {p_first[mvp]:.0%} of {n_sims:,} simulated weeks "
            f"(now #{rank_now} at {final_returns.get(mvp, 0):+.1f}%)", mvp),
        "confidence": _conf(p_first[mvp]),
        "emoji": _emoji(mvp),
    })

    bench = p_last.idxmax()
    gap = final_returns.get(bench, 0) - final_returns.min()
    predictions.append({
        "icon": "\U0001f4a9", "title": "Predicted Benchwarmer", "ticker": bench,
        "name": name_map.get(bench, bench),
        "detail": _detail(
            f"Finishes last in {p_last[bench]:.0%} of simulations "
            f"({'currently last' if gap == 0 else f'{gap:.1f} pts above last place'})",
            bench),
        "confidence": _conf(p_last[bench]),
        "emoji": _emoji(bench),
    })

    leader = final_returns.idxmax()
    if leader in idx:
        beat_leader = pd.Series(
            (finals > finals[:, [idx[leader]]]).mean(axis=0), index=tickers).drop(leader)
        if len(beat_leader) and beat_leader.max() > 0:
            c = beat_leader.idxmax()
            predictions.append({
                "icon": "\U0001f93a", "title": "Throne Challenger", "ticker": c,
                "name": name_map.get(c, c), "vs": leader,
                "detail": _detail(
                    f"Overtakes {leader} in {beat_leader[c]:.0%} of simulated weeks "
                    f"({final_returns[leader] - final_returns.get(c, 0):.1f} pts behind)", c),
                "confidence": _conf(beat_leader[c]),
                "emoji": _emoji(c),
            })

    def _signal_of(t):
        return ((signals or {}).get(t) or {}).get("signal")

    def _rsi_of(t):
        return ((signals or {}).get(t) or {}).get("rsi")

    bullish = [t for t in tickers
               if _signal_of(t) == "BUY" or (_rsi_of(t) is not None and _rsi_of(t) < 30)]
    if bullish:
        b = p_up_week[bullish].idxmax()
        predictions.append({
            "icon": "\U0001f4a5", "title": "Breakout Watch", "ticker": b,
            "name": name_map.get(b, b), "baseline": round(float(final_returns.get(b, 0)), 4),
            "detail": _detail(
                f"Bullish technicals; ends the week higher in "
                f"{p_up_week[b]:.0%} of simulations", b),
            "confidence": _conf(p_up_week[b]),
            "emoji": _emoji(b),
        })

    bearish = [t for t in tickers
               if _signal_of(t) == "SELL" or (_rsi_of(t) is not None and _rsi_of(t) > 70)]
    if bearish:
        d = (1 - p_up_week[bearish]).idxmax()
        predictions.append({
            "icon": "⚠️", "title": "Danger Zone", "ticker": d,
            "name": name_map.get(d, d), "baseline": round(float(final_returns.get(d, 0)), 4),
            "detail": _detail(
                f"Bearish technicals; ends the week lower in "
                f"{1 - p_up_week[d]:.0%} of simulations", d),
            "confidence": _conf(1 - p_up_week[d]),
            "emoji": _emoji(d),
        })

    # Sleeper: bottom-half pick most likely to simulate its way into the top half.
    half = len(tickers) // 2
    ranks = (-finals).argsort(axis=1).argsort(axis=1)  # 0 = best, per simulation
    bottom_half = [t for t in final_returns.sort_values().head(half).index if t in idx]
    if bottom_half:
        p_top_half = pd.Series({t: (ranks[:, idx[t]] < half).mean() for t in bottom_half})
        s = p_top_half.idxmax()
        if p_top_half[s] > 0:
            predictions.append({
                "icon": "\U0001f634", "title": "Sleeper Alert", "ticker": s,
                "name": name_map.get(s, s),
                "detail": _detail(
                    f"Climbs into the top half in {p_top_half[s]:.0%} of simulations", s),
                "confidence": _conf(p_top_half[s]),
                "emoji": _emoji(s),
            })

    group_cols = {}
    for t in tickers:
        g = group_map.get(t, "")
        if g:
            group_cols.setdefault(g, []).append(idx[t])
    if len(group_cols) > 1:
        group_names = list(group_cols)
        div_gains = np.stack([changes[:, cols].mean(axis=1) for cols in group_cols.values()],
                             axis=1)
        wins = np.bincount(div_gains.argmax(axis=1), minlength=len(group_names)) / n_sims
        gi = int(wins.argmax())
        hot = group_names[gi]
        predictions.append({
            "icon": "\U0001f4c8", "title": "Head of Household", "ticker": hot,
            "name": f"{GROUP_EMOJI.get(hot, '')} {hot} Division",
            "detail": f"Gains the most ground in {wins[gi]:.0%} of simulated weeks "
                      f"({len(group_cols[hot])} picks)",
            "confidence": _conf(wins[gi]),
            "emoji": GROUP_EMOJI.get(hot, ""),
        })

    vb = p_biggest_move.idxmax()
    lo, hi = np.percentile(changes[:, idx[vb]], [10, 90])
    predictions.append({
        "icon": "\U0001f4a3", "title": "Volatility Bomb", "ticker": vb,
        "name": name_map.get(vb, vb),
        "detail": _detail(
            f"Biggest weekly mover in {p_biggest_move[vb]:.0%} of simulations "
            f"(80% range {lo:+.0f} to {hi:+.0f} pts)", vb),
        "confidence": _conf(p_biggest_move[vb]),
        "emoji": _emoji(vb),
    })

    predictions.sort(key=lambda p: p.get("confidence", 0), reverse=True)
    return predictions


# --- History (machine-appended, once per day) ---

def load_history() -> dict:
    try:
        with open(PREDICTION_HISTORY_PATH) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"past": []}


def record_predictions(predictions: list, history: dict) -> None:
    today = datetime.date.today().isoformat()
    if any(p.get("recorded_date") == today for p in history.get("past", [])):
        return
    for pred in predictions:
        entry = {
            "recorded_date": today,
            "title": pred["title"],
            "ticker": pred["ticker"],
            "confidence": pred.get("confidence", 50),
            "detail": pred["detail"],
        }
        if pred.get("vs"):
            entry["vs"] = pred["vs"]
        if pred.get("baseline") is not None:
            entry["baseline"] = pred["baseline"]
        history.setdefault("past", []).append(entry)
    try:
        with open(PREDICTION_HISTORY_PATH, "w") as f:
            json.dump(history, f, indent=2, default=str)
    except OSError:
        pass  # read-only deploys: accuracy tracking just pauses


def check_past_predictions(history: dict, current_returns: pd.Series) -> list:
    """Score predictions at least 5 days old against today's standings."""
    today = datetime.date.today()
    results = []
    for pred in history.get("past", []):
        try:
            pred_date = datetime.date.fromisoformat(pred["recorded_date"])
        except (ValueError, KeyError):
            continue
        if (today - pred_date).days < 5:
            continue
        ticker = pred["ticker"]
        if ticker not in current_returns.index:
            continue
        ret = current_returns[ticker]
        title = pred["title"]
        if title == "Predicted MVP":
            correct = ticker == current_returns.idxmax()
            actual = f"Actual MVP: {current_returns.idxmax()} ({current_returns.max():+.2f}%)"
        elif title == "Breakout Watch":
            # New-style entries store the return at prediction time; the claim
            # is "ends the week higher". Old entries fall back to vs-median.
            if pred.get("baseline") is not None:
                correct = ret > pred["baseline"]
                actual = f"Return: {ret:+.2f}% (was {pred['baseline']:+.2f}%)"
            else:
                correct = ret > current_returns.median()
                actual = f"Return: {ret:+.2f}%"
        elif title == "Danger Zone":
            if pred.get("baseline") is not None:
                correct = ret < pred["baseline"]
                actual = f"Return: {ret:+.2f}% (was {pred['baseline']:+.2f}%)"
            else:
                correct = ret < current_returns.median()
                actual = f"Return: {ret:+.2f}%"
        elif title == "Predicted Benchwarmer":
            correct = ticker == current_returns.idxmin()
            actual = f"Actual Bench: {current_returns.idxmin()} ({current_returns.min():+.2f}%)"
        elif title == "Throne Challenger" and pred.get("vs") in current_returns.index:
            vs = pred["vs"]
            correct = ret > current_returns[vs]
            actual = f"{ticker}: {ret:+.2f}% vs {vs}: {current_returns[vs]:+.2f}%"
        elif title == "Sleeper Alert":
            correct = ret > current_returns.median()
            actual = f"Return: {ret:+.2f}% (median {current_returns.median():+.2f}%)"
        else:
            continue
        results.append({"date": pred["recorded_date"], "title": title, "ticker": ticker,
                        "confidence": pred.get("confidence", 50), "correct": bool(correct),
                        "actual": actual})
    return results
