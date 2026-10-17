"""Assemble the newsletter snapshot from the compute layer.

The snapshot reads the SAME computed numbers as the dashboard, so the email can
never contradict the site. Standings are always all-time (that's the game);
movers cover the selected period. One snapshot feeds every edition: the
Gmail-safe HTML email, the plain-text twin, and the PDF print edition.
"""

from __future__ import annotations

import datetime
import json
import random

from smfd import trivia
from smfd.compute import groups, race, rankings, superlatives
from smfd.compute import roasts as roasts_mod
from smfd.config import GAME_END, GAME_START, GROUP_NAMES, GROUPS, NEWSLETTER_LOG_PATH
from smfd.data import GameData

AWARD_COUNT = 6  # trophy-shelf badges shown (2x3 grid)

PERIODS = {
    "month": "Last month",
    "since_last": "Since the last newsletter",
    "all": "All-time",
}


# --- Newsletter log (enables "since last newsletter" + month-over-month) ---

def load_log() -> list:
    try:
        with open(NEWSLETTER_LOG_PATH) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def last_newsletter_date() -> datetime.date | None:
    log = load_log()
    if not log:
        return None
    try:
        return datetime.date.fromisoformat(log[-1]["date"])
    except (KeyError, ValueError):
        return None


def record_newsletter(period_label: str, roast_key: str = "") -> None:
    log = load_log()
    entry = {"date": datetime.date.today().isoformat(), "period_label": period_label}
    if roast_key:
        entry["roast_key"] = roast_key  # so future newsletters never repeat the joke
    log.append(entry)
    try:
        NEWSLETTER_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(NEWSLETTER_LOG_PATH, "w") as f:
            json.dump(log, f, indent=2)
    except OSError:
        pass


# --- Snapshot ---

def _months_elapsed(as_of: datetime.date) -> int:
    return max((as_of.year - GAME_START.year) * 12 + as_of.month - GAME_START.month, 1)


def _shift_month_back(d: datetime.date) -> datetime.date:
    year, month = (d.year, d.month - 1) if d.month > 1 else (d.year - 1, 12)
    try:
        return d.replace(year=year, month=month)
    except ValueError:  # e.g. Mar 31 -> Feb 28
        return d.replace(year=year, month=month, day=1)


def _period_window(period: str, as_of: datetime.date) -> tuple:
    if period == "all":
        return GAME_START, f"All-time · {GAME_START.strftime('%b %d')} – {as_of.strftime('%b %d, %Y')}"
    if period == "since_last":
        last = last_newsletter_date()
        if last and last < as_of:
            return last, (f"Since the last newsletter · {last.strftime('%b %d')} – "
                          f"{as_of.strftime('%b %d, %Y')}")
        period = "month"  # no log yet — fall through
    start = max(_shift_month_back(as_of), GAME_START)
    label = (f"Month {_months_elapsed(as_of)} · {start.strftime('%b %d')} – "
             f"{as_of.strftime('%b %d, %Y')}")
    return start, label


def _pick_row(scores, ticker: str) -> dict:
    return {
        "ticker": ticker,
        "name": scores.loc[ticker, "name"],
        "etf": scores.loc[ticker, "group"],
        "total_return_pct": float(scores.loc[ticker, "total_return_pct"]),
    }


def _roast_line(data: GameData, computed: dict, laggard: dict,
                rng: random.Random) -> tuple[str, str]:
    """One roast from the shared Shots Fired engine, plain-text for email.

    Prefers a joke about the laggard, dedups against roasts sent in past
    newsletters (via roast_key entries in the newsletter log). Returns
    (text, dedup_key); the key is logged when the newsletter is marked sent.
    """
    scores = computed["scores"]
    used = {str(i): [e["roast_key"]]
            for i, e in enumerate(load_log()) if e.get("roast_key")}
    pairs = roasts_mod.generate_roasts(
        scores["total_return_pct"], computed["total_returns"], computed.get("throne"),
        {t: t for t in scores.index}, used_history=used, rng=rng, news=data.news)
    if not pairs:  # engine never comes back empty in practice, but stay safe
        t, pct = laggard["ticker"], laggard["total_return_pct"]
        return (f"{t} at {pct:+.1f}%. Somewhere a piggy bank is outperforming "
                f"you. \U0001f437", "")
    text, key = next((p for p in pairs
                      if p[1].split("|", 1)[0] == laggard["ticker"]), pairs[0])
    return roasts_mod.plain_text(text), key


def _headline(leader: dict, group_standings: list, movers: list) -> str:
    top_group = group_standings[0] if group_standings else None
    if top_group and top_group["change_vs_last"].startswith("+"):
        return (f"\U0001f3c6 {GROUP_NAMES.get(top_group['etf'], top_group['etf'])} retook the "
                f"group lead, powered by {leader['name']}'s "
                f"{leader['total_return_pct']:+.1f}%! \U0001f4aa\U0001f525")
    if (movers and movers[0]["period_change_pct"] > 5
            and movers[0]["ticker"] != leader["ticker"]):
        return (f"\U0001f680 {movers[0]['ticker']} went on a "
                f"{movers[0]['period_change_pct']:+.1f}-point tear, while \U0001f451 "
                f"{leader['ticker']} still rules the leaderboard at "
                f"{leader['total_return_pct']:+.1f}%. \U0001f525")
    if top_group:
        return (f"\U0001f451 {GROUP_NAMES.get(top_group['etf'], top_group['etf'])} holds the "
                f"group crown and \U0001f3c6 {leader['ticker']} leads the field at "
                f"{leader['total_return_pct']:+.1f}%. \U0001f525")
    return f"\U0001f451 {leader['ticker']} leads at {leader['total_return_pct']:+.1f}%. \U0001f525"


def _age_months(as_of: datetime.date) -> int:
    """Alessi's age in whole months (born a year before GAME_END)."""
    born = GAME_END.replace(year=GAME_END.year - 1)
    return ((as_of.year - born.year) * 12 + as_of.month - born.month
            - (as_of.day < born.day))


def weekly_group_series(total_returns, group_map) -> list:
    """Group average total return, one point per week (Fridays) plus the latest
    close — smooth enough to read as a chart, small enough to keep in a dict."""
    series = groups.group_return_series(total_returns, group_map)
    if series.empty:
        return []
    last = series.iloc[-1]
    weekly = series.resample("W-FRI").last().dropna(how="all")
    weekly = weekly[weekly.index < series.index[-1]]
    rows = [{"date": d.date().isoformat(), **{g: float(r[g]) for g in series.columns}}
            for d, r in weekly.iterrows()]
    rows.append({"date": series.index[-1].date().isoformat(),
                 **{g: float(last[g]) for g in series.columns}})
    return rows


def _throne_watch(throne: dict, sup: dict, leader: dict) -> dict:
    mvp_longest = throne.get("mvp_longest") or {}
    bench_longest = throne.get("bench_longest") or {}
    rivalry = sup.get("rivalry") or {}

    def _d(v):
        return v.date().isoformat() if hasattr(v, "date") else str(v)

    return {
        "king": leader["ticker"],
        "king_name": leader["name"],
        "king_days": int(throne.get("mvp_streak") or 0),
        "crown_changes": max(len(throne.get("mvp_history") or []) - 1, 0),
        "longest_reign": ({"ticker": mvp_longest["ticker"], "days": int(mvp_longest["streak"]),
                           "start": _d(mvp_longest["start"]), "end": _d(mvp_longest["end"])}
                          if mvp_longest.get("ticker") else None),
        "longest_timeout": ({"ticker": bench_longest["ticker"],
                             "days": int(bench_longest["streak"])}
                            if bench_longest.get("ticker") else None),
        "rivalry": ({"a": rivalry["ticker1"], "b": rivalry["ticker2"],
                     "swaps": int(rivalry["swaps"])} if rivalry.get("swaps") else None),
    }


def build_snapshot(data: GameData, computed: dict, period: str = "month",
                   edition: str = "") -> dict:
    scores = computed["scores"]
    total_returns = computed["total_returns"]
    as_of = total_returns.index[-1].date()

    window_start, period_label = _period_window(period, as_of)

    # Period movers: change in total return (pp) across the window
    in_window = total_returns.loc[total_returns.index >= str(window_start)]
    if len(in_window) >= 2:
        period_change = (in_window.iloc[-1] - in_window.iloc[0]).sort_values(ascending=False)
    else:
        period_change = total_returns.iloc[-1].sort_values(ascending=False)
    top_movers = [{"ticker": t, "period_change_pct": float(v)}
                  for t, v in period_change.head(3).items()]
    bottom_movers = [{"ticker": t, "period_change_pct": float(v)}
                     for t, v in period_change.tail(3).sort_values().items()]

    # Group standings with rank change measured across the period window
    compare_days = max(len(in_window) - 1, 1)
    standings = groups.group_standings(total_returns, scores, data.group_map,
                                       compare_days=compare_days)
    group_rows = [{"etf": s["etf"], "avg_return_pct": s["avg_return_pct"],
                   "rank": s["rank"], "change_vs_last": s["change_vs_last"]}
                  for s in standings]

    leader = _pick_row(scores, scores.index[0])
    laggard = _pick_row(scores, scores.index[-1])

    # Fun extras — reuse the dashboard's numbers when the app already has them
    throne = computed.get("throne") or rankings.compute_throne_history(
        total_returns, data.name_map)
    sup = computed.get("superlatives") or superlatives.compute_superlatives(
        total_returns, throne, data.name_map, data.group_map)
    achievements = computed.get("achievements") or superlatives.compute_achievements(
        total_returns, throne, scores)
    awards = [{"icon": a["icon"], "name": a["name"], "desc": a["desc"],
               "holder": a["holder"]}
              for a in achievements if a.get("unlocked") not in (False, "False")][:AWARD_COUNT]
    etf_war = sup.get("etf_war") or {}

    rng = random.Random(as_of.isoformat())  # deterministic per day: preview == download
    total_days = max((GAME_END - GAME_START).days, 1)
    snapshot = {
        "edition": edition.strip(),
        "period_label": period_label,
        "period": period,
        "as_of": as_of.isoformat(),
        "days_remaining": race.days_remaining(as_of),
        "progress_pct": min(max((as_of - GAME_START).days / total_days * 100, 0), 100),
        "age_months": _age_months(as_of),
        "leader": leader,
        "laggard": laggard,
        "group_standings": group_rows,
        "group_series": weekly_group_series(total_returns, data.group_map),
        "group_lead_changes": len(groups.lead_changes(total_returns, data.group_map)),
        "group_longest_lead": ({"etf": etf_war["etf"], "days": int(etf_war["streak"])}
                               if etf_war.get("etf") in GROUPS else None),
        "all_picks": [_pick_row(scores, t) for t in scores.index],
        "standings_top": [_pick_row(scores, t) for t in scores.head(10).index],
        "standings_bottom": [_pick_row(scores, t) for t in scores.tail(5).index],
        "top_movers": top_movers,
        "bottom_movers": bottom_movers,
        "total_value": float(scores["total_value"].sum()),
        "total_invested": float(data.stake * len(scores)),
        "total_dividends": float(scores["dividend_income"].sum()),
        "n_picks": len(scores),
        "n_up": int((scores["total_return_pct"] > 0).sum()),
        "throne": _throne_watch(throne, sup, leader),
        "awards": awards,
        "trivia": (trivia.ticker_trivia(leader["ticker"], rng)
                   or trivia.generic_trivia(rng)[0]),
    }
    snapshot["headline_stat"] = _headline(leader, group_rows, top_movers)
    snapshot["roast"], snapshot["roast_key"] = _roast_line(data, computed, laggard, rng)
    return snapshot
