"""Predictions: the confidence numbers must be real simulated probabilities.

Regression context: the old momentum formula once claimed 90% confidence that
the #2 pick would finish LAST because it had a bad week. The Monte Carlo
engine must never do that — last-place probability for a front-runner with a
huge cushion is ~0.
"""

import datetime

import numpy as np
import pandas as pd
import pytest

from smfd.compute import predictions
from smfd.compute.returns import compute_scores, total_return_series

from conftest import make_game


def _roster(n_days=30, seed=7):
    """Roster with a runaway leader, a close #2, a mid pack, and a clear loser."""
    rng = np.random.default_rng(seed)
    dates = pd.bdate_range("2026-03-06", periods=n_days)
    base = {
        "LEAD": 1.022,   # ~+2%/day
        "MID1": 1.001, "MID2": 1.000, "MID3": 0.999,
        "LOSER": 0.97,   # bleeding out alone at the bottom
    }
    prices = {}
    for t, drift in base.items():
        noise = rng.normal(0, 0.02, n_days)
        path = 100 * np.cumprod(drift + noise)
        prices[t] = {d.strftime("%Y-%m-%d"): float(p) for d, p in zip(dates, path)}
    # CHASE shadows LEAD a hair below with its own wiggle — a genuine race
    # for the throne rather than two independent random walks drifting apart.
    lead_path = np.array(list(prices["LEAD"].values()))
    chase_path = lead_path * (0.99 + 0.008 * np.cos(np.arange(n_days)))
    prices["CHASE"] = {d.strftime("%Y-%m-%d"): float(p) for d, p in zip(dates, chase_path)}
    groups = {"LEAD": "ANTY", "CHASE": "UNCL", "MID1": "ANTY",
              "MID2": "UNCL", "MID3": "KIDZ", "LOSER": "KIDZ"}
    return make_game(prices, groups=groups)


@pytest.fixture
def sim_setup():
    game = _roster()
    total = total_return_series(game)
    scores = compute_scores(game)
    return game, total, scores


def _preds(game, total, scores, **kw):
    return predictions.generate_predictions(
        total, scores, game.name_map, game.group_map,
        today=datetime.date(2026, 6, 10), **kw)


def _by_title(preds, title):
    return next((p for p in preds if p["title"] == title), None)


class TestSimulation:
    def test_deterministic_for_same_data(self, sim_setup):
        game, total, scores = sim_setup
        assert _preds(game, total, scores) == _preds(game, total, scores)

    def test_finals_start_from_current_standings(self, sim_setup):
        _, total, _ = sim_setup
        tickers, finals = predictions.simulate_next_week(total, n_sims=500)
        current = total.iloc[-1]
        # Simulated medians stay in the neighborhood of today's return —
        # one week of moves, not a re-roll of the whole game.
        for j, t in enumerate(tickers):
            assert abs(np.median(finals[:, j]) - current[t]) < 25

    def test_too_little_history_returns_empty(self, sim_setup):
        game, total, scores = sim_setup
        assert _preds(game, total.iloc[:5], scores) == []


class TestCardSanity:
    def test_frontrunner_is_never_predicted_benchwarmer(self, sim_setup):
        """The ARM bug: a top-2 pick must not be called 'last place'."""
        game, total, scores = sim_setup
        bench = _by_title(_preds(game, total, scores), "Predicted Benchwarmer")
        top2 = list(scores.index[:2])
        assert bench["ticker"] not in top2
        assert bench["ticker"] == "LOSER"

    def test_mvp_is_a_frontrunner(self, sim_setup):
        game, total, scores = sim_setup
        mvp = _by_title(_preds(game, total, scores), "Predicted MVP")
        assert mvp["ticker"] in list(scores.index[:2])

    def test_confidence_is_simulated_probability(self, sim_setup):
        game, total, scores = sim_setup
        for p in _preds(game, total, scores):
            assert 1 <= p["confidence"] <= 99
            # Detail cites the simulation evidence, not vibes.
            assert "simulat" in p["detail"] or "sims" in p["detail"]

    def test_throne_challenger_is_the_close_second(self, sim_setup):
        game, total, scores = sim_setup
        chal = _by_title(_preds(game, total, scores), "Throne Challenger")
        # The actual runner-up is the credible threat, not whoever is most volatile.
        assert chal["ticker"] == scores.index[1]
        assert chal["vs"] == scores.index[0]
        # A near-tie chase: meaningful but not certain.
        assert 5 <= chal["confidence"] <= 95

    def test_signals_gate_breakout_and_danger(self, sim_setup):
        game, total, scores = sim_setup
        no_sig = _preds(game, total, scores)
        assert _by_title(no_sig, "Breakout Watch") is None
        assert _by_title(no_sig, "Danger Zone") is None
        signals = {"MID1": {"rsi": 25.0, "signal": "BUY", "score": 3},
                   "MID2": {"rsi": 78.0, "signal": "SELL", "score": -3}}
        with_sig = _preds(game, total, scores, signals=signals)
        breakout = _by_title(with_sig, "Breakout Watch")
        danger = _by_title(with_sig, "Danger Zone")
        assert breakout["ticker"] == "MID1" and "RSI 25" in breakout["detail"]
        assert danger["ticker"] == "MID2" and "RSI 78" in danger["detail"]
        assert breakout["baseline"] == pytest.approx(
            scores.loc["MID1", "total_return_pct"], abs=1e-3)

    def test_earnings_within_week_flagged(self, sim_setup):
        game, total, scores = sim_setup
        earnings = {"LEAD": {"next_date": "Jun 12"}}
        mvp = _by_title(_preds(game, total, scores, earnings=earnings), "Predicted MVP")
        if mvp["ticker"] == "LEAD":
            assert "earnings Jun 12" in mvp["detail"]


class TestGrading:
    def test_throne_challenger_graded_against_recorded_leader(self):
        history = {"past": [{"recorded_date": "2026-01-01", "title": "Throne Challenger",
                             "ticker": "CHASE", "confidence": 30, "detail": "", "vs": "LEAD"}]}
        returns = pd.Series({"LEAD": 50.0, "CHASE": 60.0, "MID1": 0.0})
        results = predictions.check_past_predictions(history, returns)
        assert results[0]["correct"] is True

    def test_breakout_graded_against_baseline(self):
        history = {"past": [{"recorded_date": "2026-01-01", "title": "Breakout Watch",
                             "ticker": "MID1", "confidence": 60, "detail": "",
                             "baseline": 5.0}]}
        returns = pd.Series({"LEAD": 50.0, "MID1": 4.0, "MID2": 90.0})
        results = predictions.check_past_predictions(history, returns)
        assert results[0]["correct"] is False  # 4.0 < baseline 5.0

    def test_legacy_entries_still_grade_via_median(self):
        history = {"past": [{"recorded_date": "2026-01-01", "title": "Breakout Watch",
                             "ticker": "MID1", "confidence": 60, "detail": ""}]}
        returns = pd.Series({"LEAD": 50.0, "MID1": 4.0, "MID2": -10.0, "MID3": -20.0})
        results = predictions.check_past_predictions(history, returns)
        assert results[0]["correct"] is True  # above median (-3.0) of the four returns
