"""Trivia: per-visit variety from a large pool, never the same fact twice on screen."""

import random

from smfd import trivia


class TestPools:
    def test_generic_pool_is_large_and_unique(self):
        assert len(trivia.GENERIC_TRIVIA) >= 50
        assert len(set(trivia.GENERIC_TRIVIA)) == len(trivia.GENERIC_TRIVIA)
        assert all(isinstance(f, str) and f.strip() for f in trivia.GENERIC_TRIVIA)

    def test_ticker_pools_unique_and_nonempty(self):
        for ticker, facts in trivia.STOCK_TRIVIA.items():
            assert facts, ticker
            assert len(set(facts)) == len(facts), ticker

    def test_standings_leaders_have_ticker_facts(self):
        # The MVP card only fires for the current leader — cover the whole
        # top of the standings so it rarely falls back to generic facts.
        for t in ["SNDK", "ARM", "INTC", "MU", "AMD", "STX", "WDC", "LRCX"]:
            assert t in trivia.STOCK_TRIVIA, t


class TestSelection:
    def test_two_cards_never_show_the_same_fact(self):
        for seed in range(200):
            f1, f2 = trivia.generic_trivia(random.Random(seed), count=2)
            assert f1 != f2

    def test_same_session_seed_is_stable(self):
        assert (trivia.generic_trivia(random.Random(42), count=2)
                == trivia.generic_trivia(random.Random(42), count=2))

    def test_different_sessions_usually_differ(self):
        draws = {tuple(trivia.generic_trivia(random.Random(s), count=2))
                 for s in range(20)}
        assert len(draws) >= 15  # fresh visits see fresh facts

    def test_ticker_trivia_comes_from_pool_or_none(self):
        rng = random.Random(7)
        assert trivia.ticker_trivia("ARM", rng) in trivia.STOCK_TRIVIA["ARM"]
        assert trivia.ticker_trivia("NOT-A-TICKER", rng) is None
