"""Daily roasts — teasing, never mean. These are friends.

Roasts regenerate once per trading day (after the 4 PM close) and persist in
roasts_cache.json. The 30-day dedup history keys on "TICKER|template" (template
= text with tickers and numbers stripped), so the same joke about the same
ticker rests for 30 days even as the percentages drift day to day.

A slice of each day's roasts is drawn from real headlines (fetched nightly via
yfinance into stock_data.json), juxtaposing the financial press against the
ticker's actual scoreboard. Headlines change daily, so these never go stale.

Ticker markup is the caller's job; templates here take pre-colored ticker HTML.
"""

from __future__ import annotations

import datetime
import html
import json
import random
import re

import pandas as pd

from smfd import market_calendar
from smfd.config import ROASTS_CACHE_PATH, TIMEZONE

MAX_ROASTS = 8
MIN_ROASTS = 7
MAX_NEWS_ROASTS = 2
NEWS_MAX_AGE_DAYS = 7
NEWS_TITLE_MAX_LEN = 100


def _strip_html(s: str) -> str:
    return re.sub(r"<[^>]+>", "", s).strip()


def plain_text(roast: str) -> str:
    """Roast HTML → plain text, entities unescaped (for email contexts that re-escape)."""
    return html.unescape(_strip_html(roast))


def _template(text: str, tickers) -> str:
    """The joke with tickers and numbers removed — what makes it 'the same joke'."""
    t = _strip_html(text)
    for ticker in sorted(tickers, key=len, reverse=True):
        t = t.replace(ticker, "")
    return re.sub(r"[+-]?\d+\.?\d*%?", "", t).strip()


def _roast_key(text: str, ticker: str | None, tickers) -> str:
    return f"{ticker or ''}|{_template(text, tickers)}"


def _tier_candidates(sorted_rets: pd.Series, ticker_html: dict) -> list:
    """(html, ticker) pairs bucketed by total return."""
    candidates = []
    for t, ret in sorted_rets.items():
        tc = ticker_html.get(t, f"<b>{t}</b>")
        if ret > 15:
            lines = [
                f"\U0001f451 {tc} is up {ret:+.2f}% and won't shut up about it. We get it, you're winning.",
                f"\U0001f451 {tc} at {ret:+.2f}%? Enjoy it while it lasts. The market humbles everyone.",
                f"\U0001f451 {tc} sitting pretty at {ret:+.2f}%. Main character energy.",
                f"\U0001f451 Someone check on {tc}'s ego. {ret:+.2f}% and counting. Insufferable.",
                f"\U0001f451 {tc} up {ret:+.2f}% and already practicing the acceptance speech. The trophy isn't engraved yet.",
                f"\U0001f451 {tc} at {ret:+.2f}% is the friend who 'forgot' they aced the test. Nobody forgets.",
                f"\U0001f451 Scientists confirm {tc}'s {ret:+.2f}% is visible from space. So is the gloating.",
                f"\U0001f451 {tc}: {ret:+.2f}%. Started from the close, now we're here.",
            ]
        elif ret > 5:
            lines = [
                f"\U0001f7e2 {tc} quietly sitting at {ret:+.2f}%. Not flashy, but getting the job done.",
                f"\U0001f7e2 {tc} at {ret:+.2f}%. Slow and steady. Boring but profitable.",
                f"\U0001f7e2 {tc} up {ret:+.2f}% with zero drama. The designated driver of this portfolio.",
                f"\U0001f7e2 {tc} at {ret:+.2f}%. Shows up, compounds, goes home. We could all learn something.",
                f"\U0001f7e2 {tc} grinding out {ret:+.2f}% like it's a 9-to-5. Direct deposit energy.",
                f"\U0001f7e2 Nobody talks about {tc} at {ret:+.2f}%, which is exactly how winners like it.",
            ]
        elif ret >= 2:
            lines = [
                f"\U0001f422 {tc} inching along at {ret:+.2f}%. Technically winning. Technically.",
                f"\U0001f422 {tc} at {ret:+.2f}%. Beating inflation and absolutely nothing else.",
                f"\U0001f422 {tc} up {ret:+.2f}%. A round of polite golf claps, please.",
                f"\U0001f422 {tc} at {ret:+.2f}% — the participation ribbon of green numbers.",
            ]
        elif ret > -2:
            lines = [
                f"\U0001fae5 {tc} returned {ret:+.2f}%. Absolute NPC energy. Doing nothing and hoping nobody notices.",
                f"\U0001fae5 {tc} at {ret:+.2f}%. The human equivalent of 'I'm just here so I don't get fined.'",
                f"\U0001fae5 {tc} with {ret:+.2f}%. Flatline energy. Even the chart fell asleep.",
                f"\U0001fae5 {tc} at {ret:+.2f}%. Schrödinger's stock: in the game, showing no signs of life.",
                f"\U0001fae5 {tc} moved {ret:+.2f}% in months. Glaciers are filing complaints about the pace.",
                f"\U0001fae5 {tc} at {ret:+.2f}%. Not a stock, a savings account with anxiety.",
            ]
        elif ret > -5:
            lines = [
                f"\U0001f4c9 {tc} at {ret:+.2f}%. A slow leak, not a blowout. Still losing air, though.",
                f"\U0001f4c9 {tc} at {ret:+.2f}%. Death by a thousand papercuts, but make it financial.",
                f"\U0001f4c9 {tc} at {ret:+.2f}%. Not a disaster, just a quiet disappointment. Like a soggy fry.",
                f"\U0001f4c9 {tc} drifting at {ret:+.2f}%. The market's way of saying 'meh,' but rude about it.",
            ]
        elif ret > -15:
            lines = [
                f"\U0001f534 {tc} down {ret:+.2f}%. Not great, not terrible. Actually, it's terrible.",
                f"\U0001f534 {tc} returning {ret:+.2f}%. Underperforming a savings account. Impressive.",
                f"\U0001f534 {tc} at {ret:+.2f}%. The group chat has started using the past tense.",
                f"\U0001f534 {tc} at {ret:+.2f}%. 'It's a long-term play,' said someone coping, probably.",
                f"\U0001f534 {tc} down {ret:+.2f}% and calling it 'consolidation.' Sure, buddy.",
                f"\U0001f534 {tc} at {ret:+.2f}%. The dip kept dipping. There's guac at the bottom, allegedly.",
            ]
        else:
            lines = [
                f"\U0001f4a9 {tc} at {ret:+.2f}%. If this were a group project, you'd be the one who didn't show up.",
                f"\U0001f4a9 Moment of silence for {tc} at {ret:+.2f}%. You didn't have to go this hard… in the wrong direction.",
                f"\U0001f4a9 {tc} at {ret:+.2f}%. Certified bag holder. No, not designer bags.",
                f"\U0001f4a9 {tc} at {ret:+.2f}%. That's not a drawdown, that's a magic trick. Where did the money go?",
                f"\U0001f4a9 {tc} down {ret:+.2f}%. The good news: the loss is notional. The bad news: everything else.",
                f"\U0001f4a9 Thoughts and prayers to {tc} at {ret:+.2f}%. The candle is lit.",
                f"\U0001f4a9 {tc} at {ret:+.2f}% survived splits, dividends, and dignity. Well, two of the three.",
            ]
        candidates += [(line, t) for line in lines]
    return candidates


def _news_candidates(news: dict, sorted_rets: pd.Series, ticker_html: dict,
                     now: datetime.datetime) -> list:
    """Real headlines vs the scoreboard. The freshest headline per ticker only."""
    candidates = []
    cutoff = now - datetime.timedelta(days=NEWS_MAX_AGE_DAYS)
    for t, ret in sorted_rets.items():
        items = news.get(t) or []
        fresh = []
        for item in items:
            title = (item.get("title") or "").strip()
            if len(title) < 20:
                continue
            try:
                published = datetime.datetime.fromisoformat(
                    item.get("providerPublishTime", "").replace("Z", "+00:00"))
            except ValueError:
                continue
            if published >= cutoff:
                fresh.append((published, title))
        if not fresh:
            continue
        _, title = max(fresh)
        if len(title) > NEWS_TITLE_MAX_LEN:
            title = title[:NEWS_TITLE_MAX_LEN - 1].rsplit(" ", 1)[0] + "…"
        title = html.escape(title)
        tc = ticker_html.get(t, f"<b>{t}</b>")
        if ret >= 5:
            lines = [
                f"\U0001f4f0 “{title}” — and {tc} is up {ret:+.2f}%. Even the financial press joined the fan club.",
                f"\U0001f4f0 The headlines say “{title}” — {tc} holders read that at {ret:+.2f}% feeling like geniuses.",
            ]
        elif ret <= -5:
            lines = [
                f"\U0001f4f0 “{title}” — meanwhile {tc} sits at {ret:+.2f}%. The article is doing better than the stock.",
                f"\U0001f4f0 “{title}” — great headline. Shame about the {ret:+.2f}%, {tc}.",
            ]
        else:
            lines = [
                f"\U0001f4f0 “{title}” — all that coverage and {tc} still moved a whole {ret:+.2f}%. Gripping stuff.",
                f"\U0001f4f0 “{title}” says the press. {tc} responded with {ret:+.2f}%. Thrilling follow-through.",
            ]
        candidates += [(line, t) for line in lines]
    return candidates


def _special_candidates(sorted_rets: pd.Series, total_returns: pd.DataFrame,
                        throne: dict, ticker_html: dict, rng: random.Random) -> list:
    candidates = []
    total = len(sorted_rets)

    if len(total_returns) > 2:
        worst_days = total_returns.diff().dropna().min()
        volatile = worst_days[worst_days < -3].index.tolist()
        rng.shuffle(volatile)
        for t in volatile[:3]:
            tc = ticker_html.get(t, f"<b>{t}</b>")
            drop = worst_days[t]
            candidates += [(line, t) for line in [
                f"\U0001f3a2 {tc} nosedived {drop:+.2f}% in one day. That's bungee jumping without the cord.",
                f"\U0001f3a2 {tc} dropped {drop:+.2f}% in a single day. Somewhere a stop-loss is crying.",
                f"\U0001f3a2 {tc} fell {drop:+.2f}% in a day. Even the elevator said 'slow down.'",
                f"\U0001f3a2 {tc}'s {drop:+.2f}% day registered on the seismograph. Geologists are involved now.",
                f"\U0001f3a2 {tc} dropped {drop:+.2f}% in one session. Not volatility — a cliff with extra steps.",
            ]]

    bottom_half = sorted_rets.tail(total // 2)
    if len(bottom_half) >= 3:
        sampled = bottom_half.sample(3, random_state=rng.randint(0, 99999))
        names = ", ".join(ticker_html.get(t, f"<b>{t}</b>") for t in sampled.index)
        combined = sampled.sum()
        candidates += [(line, None) for line in [
            f"\U0001f6bd {names} combining for {combined:+.2f}%. The Avengers of underperformance.",
            f"\U0001f6bd {names} returning {combined:+.2f}% together. Three picks, one shared L.",
            f"\U0001f6bd {names}: {combined:+.2f}% combined. Group costume idea — the three red arrows.",
            f"\U0001f6bd {names} pooled their talents for {combined:+.2f}%. Teamwork makes the dream… worse.",
        ]]

    mvp_changes = len([e for e in (throne or {}).get("mvp_history", [])
                       if e.get("prev_ticker")])
    if mvp_changes >= 4:
        candidates += [(line, None) for line in [
            f"\U0001f3b0 The MVP throne changed hands {mvp_changes} times. More drama than a reality TV show.",
            f"\U0001f3b0 {mvp_changes} different reigns on the MVP throne. That's not a crown, it's a hot potato.",
        ]]
    elif mvp_changes <= 1 and len(sorted_rets):
        mvp = sorted_rets.index[0]
        candidates += [(line, mvp) for line in [
            f"\U0001f3b0 <b>{mvp}</b> has owned the throne the whole time. Everyone else? Participation trophies.",
            f"\U0001f3b0 <b>{mvp}</b> still on the throne. At this point the crown is load-bearing.",
        ]]

    red = int((sorted_rets <= 0).sum())
    if red > total * 0.6:
        candidates += [(line, None) for line in [
            f"\U0001f534 {red} out of {total} in the red. This isn't a portfolio, it's a crime scene.",
            f"\U0001f534 {red} of {total} underwater. The portfolio is doing synchronized sinking.",
        ]]
    elif red < total * 0.3:
        candidates += [(line, None) for line in [
            f"\U0001f7e2 Only {red} out of {total} in the red. Don't get comfortable — the market is just loading the next prank.",
            f"\U0001f7e2 Just {red} of {total} red. Suspicious. The market never lets this slide for long.",
        ]]
    return candidates


def generate_roasts(final_returns: pd.Series, total_returns: pd.DataFrame,
                    throne: dict | None, ticker_html: dict, used_history: dict | None = None,
                    rng: random.Random | None = None, news: dict | None = None,
                    now: datetime.datetime | None = None) -> list:
    """Returns [(html, dedup_key)] — up to MAX_ROASTS, news-flavored ones first."""
    rng = rng or random.Random()
    now = now or datetime.datetime.now(TIMEZONE)
    sorted_rets = final_returns.sort_values(ascending=False)
    tickers = list(sorted_rets.index)

    regular = _tier_candidates(sorted_rets, ticker_html)
    regular += _special_candidates(sorted_rets, total_returns, throne, ticker_html, rng)
    newsy = _news_candidates(news or {}, sorted_rets, ticker_html, now)

    recently_used = set()
    for keys in (used_history or {}).values():
        recently_used.update(keys)

    def _fresh(pool):
        kept = [(text, t) for text, t in pool
                if _roast_key(text, t, tickers) not in recently_used]
        return kept if kept else pool

    regular, newsy = _fresh(regular), _fresh(newsy) if newsy else newsy
    rng.shuffle(regular)
    rng.shuffle(newsy)

    roasts, used_tickers, used_templates = [], set(), set()

    def _take(pool, limit):
        for text, t in pool:
            if len(roasts) >= limit:
                return
            tmpl = _template(text, tickers)
            if tmpl in used_templates or (t and t in used_tickers):
                continue
            roasts.append((text, _roast_key(text, t, tickers)))
            used_templates.add(tmpl)
            if t:
                used_tickers.add(t)

    _take(newsy, MAX_NEWS_ROASTS)
    _take(regular, MAX_ROASTS)

    chosen = {text for text, _ in roasts}
    for text, t in regular + newsy:  # backfill to at least MIN_ROASTS
        if len(roasts) >= MIN_ROASTS:
            break
        if text not in chosen:
            roasts.append((text, _roast_key(text, t, tickers)))
            chosen.add(text)
    return roasts


def current_roast_day(now: datetime.datetime | None = None) -> str:
    """The trading day today's roasts are about (rolls over at 4 PM ET)."""
    now = (now or datetime.datetime.now(TIMEZONE)).astimezone(TIMEZONE)
    day = now.date()
    if not (market_calendar.is_trading_day(day) and now.hour >= 16):
        day = market_calendar.previous_trading_day(day)
    return day.isoformat()


def load_cache() -> dict:
    try:
        with open(ROASTS_CACHE_PATH) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"date": "", "roasts": [], "used": {}}


def daily_roasts(final_returns: pd.Series, total_returns: pd.DataFrame,
                 throne: dict, ticker_html: dict, news: dict | None = None) -> tuple[str, list]:
    """Cached-per-trading-day roasts. Returns (roast_day_iso, roasts)."""
    day = current_roast_day()
    cache = load_cache()
    if cache.get("date") == day and cache.get("roasts"):
        return day, cache["roasts"]

    used = cache.get("used", {})
    pairs = generate_roasts(final_returns, total_returns, throne, ticker_html,
                            used, news=news)
    roasts = [text for text, _ in pairs]
    used[day] = [key for _, key in pairs]
    for old in sorted(used)[:-30]:
        del used[old]
    try:
        with open(ROASTS_CACHE_PATH, "w") as f:
            json.dump({"date": day, "roasts": roasts, "used": used}, f, indent=2)
    except OSError:
        pass  # read-only deploys: roasts regenerate per session instead
    return day, roasts
