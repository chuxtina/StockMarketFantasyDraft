"""Growth chart: weekly check-ups, full-field ranks."""

import pandas as pd

from smfd import charts


def _frame():
    # Three trading weeks; B overtakes A in week 2.
    dates = pd.to_datetime([
        "2026-03-02", "2026-03-04", "2026-03-06",   # week 1
        "2026-03-09", "2026-03-13",                 # week 2
        "2026-03-16", "2026-03-18",                 # week 3 (partial)
    ])
    return pd.DataFrame({
        "A": [0.0, 2.0, 4.0, 4.0, 3.0, 2.0, 1.0],
        "B": [0.0, 1.0, 2.0, 3.0, 5.0, 6.0, 7.0],
        "C": [0.0, -1.0, -2.0, -2.0, -3.0, -3.0, -4.0],
    }, index=dates)


class TestWeeklyRankHistory:
    def test_samples_one_checkup_per_week_plus_day_one(self):
        sampled, ranks = charts.weekly_rank_history(_frame())
        assert list(sampled.index) == list(pd.to_datetime(
            ["2026-03-02", "2026-03-06", "2026-03-13", "2026-03-18"]))

    def test_latest_day_always_included(self):
        sampled, _ = charts.weekly_rank_history(_frame())
        assert sampled.index[-1] == pd.Timestamp("2026-03-18")

    def test_ranks_are_full_field(self):
        _, ranks = charts.weekly_rank_history(_frame())
        # Week 1: A leads; final day: B #1, A #2, C #3.
        assert list(ranks.iloc[1][["A", "B", "C"]]) == [1.0, 2.0, 3.0]
        assert list(ranks.iloc[-1][["A", "B", "C"]]) == [2.0, 1.0, 3.0]

    def test_day_zero_tie_starts_at_week_one_order(self):
        _, ranks = charts.weekly_rank_history(_frame())
        # All-zero opening day inherits week 1's ranks instead of a 3-way tie.
        assert list(ranks.iloc[0]) == list(ranks.iloc[1])

    def test_growth_chart_builds_a_figure(self):
        frame = _frame()
        fig = charts.growth_chart(frame, ["A", "B"], {"A": "A co", "B": "B co"},
                                  {"A": "ANTY", "B": "UNCL"}, "Top picks")
        assert len(fig.data) == 4  # one line + one marker trace per ticker
        marker_trace = fig.data[1]
        assert len(marker_trace.x) == 4  # one point per check-up, not per day
        assert len(fig.layout.annotations) == 2  # one end-of-line label each


class TestLabelDodge:
    def test_no_overlap_when_targets_cluster(self):
        # Ten labels all wanting ranks 1..10 on an axis stretched to 65.
        ys = charts._dodge_labels([float(r) for r in range(1, 11)], 0.5, 65.0, 3.0)
        assert all(b - a >= 3.0 - 1e-9 for a, b in zip(ys, ys[1:]))
        assert ys[0] >= 0.5 and ys[-1] <= 65.0

    def test_untouched_when_already_spread(self):
        ys = charts._dodge_labels([1.0, 10.0, 20.0], 0.5, 30.0, 3.0)
        assert ys == [1.0, 10.0, 20.0]

    def test_cluster_at_bottom_pulls_back_up(self):
        # Bottom-10 case: endpoints jammed against the lower bound.
        ys = charts._dodge_labels([26.0, 27.0, 28.0, 29.0, 30.0], 0.5, 30.0, 3.0)
        assert ys[-1] <= 30.0
        assert all(b - a >= 3.0 - 1e-9 for a, b in zip(ys, ys[1:]))