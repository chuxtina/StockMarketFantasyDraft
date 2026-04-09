#!/usr/bin/env python3
"""Fetch stock data and save to data/stock_data.json.

Reads tickers from players.json, fetches prices, dividends, technical signals,
earnings, and news via yfinance, then writes a single JSON file consumed by the app.

Usage:
    python fetch_data.py
"""

import datetime
import json
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import pandas as pd
import yfinance as yf

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

DEFAULT_START = datetime.date(2026, 3, 6)
BATCH_SIZE = 20
BATCH_DELAY = 2  # seconds between yf.download batches
MAX_RETRIES = 3
RETRY_DELAY = 5  # seconds
THREAD_WORKERS = 10

ROOT = Path(__file__).resolve().parent
PLAYERS_PATH = ROOT / "players.json"
OUTPUT_DIR = ROOT / "data"
OUTPUT_PATH = OUTPUT_DIR / "stock_data.json"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def load_tickers() -> list[dict]:
    """Load player entries from players.json."""
    with open(PLAYERS_PATH, "r") as f:
        data = json.load(f)
    return data["players"]


def _retry(fn, *args, retries=MAX_RETRIES, delay=RETRY_DELAY, label=""):
    """Call *fn* with retries on exception."""
    for attempt in range(1, retries + 1):
        try:
            return fn(*args)
        except Exception as exc:
            if attempt < retries:
                print(f"  [retry {attempt}/{retries}] {label}: {exc}")
                time.sleep(delay)
            else:
                print(f"  [FAILED] {label}: {exc}")
                raise


# ---------------------------------------------------------------------------
# 1. Daily close prices
# ---------------------------------------------------------------------------


def fetch_prices(tickers: list[str], start: datetime.date, end: datetime.date) -> dict:
    """Download daily close prices in batches and return {ticker: {date_str: price}}."""
    all_close = pd.DataFrame()
    for i in range(0, len(tickers), BATCH_SIZE):
        batch = tickers[i : i + BATCH_SIZE]
        print(f"  Downloading prices batch {i // BATCH_SIZE + 1} ({len(batch)} tickers)...")

        def _download():
            return yf.download(
                batch,
                start=start,
                end=end + datetime.timedelta(days=1),
                auto_adjust=True,
                progress=False,
                threads=True,
            )

        try:
            data = _retry(_download, label=f"price batch {i // BATCH_SIZE + 1}")
        except Exception:
            continue

        if data.empty:
            continue

        close = data["Close"]
        if isinstance(close, pd.Series):
            close = close.to_frame(name=batch[0])

        all_close = pd.concat([all_close, close], axis=1)

        if i + BATCH_SIZE < len(tickers):
            time.sleep(BATCH_DELAY)

    # Fill gaps
    all_close = all_close.ffill().bfill()

    # Build per-ticker dict
    prices: dict[str, dict[str, float]] = {}
    for ticker in tickers:
        if ticker in all_close.columns and not all_close[ticker].isna().all():
            series = all_close[ticker].dropna()
            prices[ticker] = {
                d.strftime("%Y-%m-%d"): round(float(v), 4) for d, v in series.items()
            }

    return prices


# ---------------------------------------------------------------------------
# 2. Dividends
# ---------------------------------------------------------------------------


def fetch_dividends(tickers: list[str], start: datetime.date, end: datetime.date) -> dict:
    """Fetch total dividends per share in the date range (threaded)."""

    def _fetch_one(ticker: str):
        try:
            t = yf.Ticker(ticker)
            d = t.dividends
            if d is not None and not d.empty:
                d.index = d.index.tz_localize(None)
                mask = (d.index >= pd.Timestamp(start)) & (d.index <= pd.Timestamp(end))
                return ticker, round(float(d[mask].sum()), 4)
            return ticker, 0.0
        except Exception:
            return ticker, 0.0

    print(f"  Fetching dividends for {len(tickers)} tickers...")
    with ThreadPoolExecutor(max_workers=THREAD_WORKERS) as pool:
        results = pool.map(_fetch_one, tickers)
    return dict(results)


# ---------------------------------------------------------------------------
# 3. Technical signals
# ---------------------------------------------------------------------------


def compute_signals(tickers: list[str], start: datetime.date, end: datetime.date) -> dict:
    """Compute RSI / SMA signals matching the app's compute_signals logic."""
    extended_start = start - datetime.timedelta(days=45)

    print(f"  Downloading extended price history for signals...")
    data = _retry(
        lambda: yf.download(
            tickers,
            start=extended_start,
            end=end + datetime.timedelta(days=1),
            auto_adjust=True,
            progress=False,
            threads=True,
        ),
        label="signal price download",
    )
    if data.empty:
        return {}

    close = data["Close"]
    if isinstance(close, pd.Series):
        close = close.to_frame(name=tickers[0])
    close = close.ffill().bfill()

    signals: dict = {}
    for ticker in tickers:
        if ticker not in close.columns or close[ticker].isna().all():
            continue
        prices = close[ticker].dropna()
        if len(prices) < 20:
            signals[ticker] = {
                "rsi": None,
                "signal": "HOLD",
                "score": 0,
                "sma_cross": None,
                "price_vs_sma": None,
                "signal_date": None,
                "prev_signal": None,
            }
            continue

        # RSI (14-day)
        delta = prices.diff()
        gain = delta.where(delta > 0, 0).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        current_rsi = float(rsi.iloc[-1]) if not pd.isna(rsi.iloc[-1]) else 50.0

        # SMA crossover (10 vs 20)
        sma10 = prices.rolling(window=10).mean()
        sma20 = prices.rolling(window=20).mean()
        sma_cross = bool(sma10.iloc[-1] > sma20.iloc[-1])

        # Price vs 20-day SMA
        price_vs_sma = bool(prices.iloc[-1] > sma20.iloc[-1])

        # Composite score
        score = 0
        if current_rsi < 30:
            score += 1
        elif current_rsi > 70:
            score -= 1
        if sma_cross:
            score += 1
        else:
            score -= 1
        if price_vs_sma:
            score += 1
        else:
            score -= 1

        if score >= 2:
            signal = "BUY"
        elif score <= -2:
            signal = "SELL"
        else:
            signal = "HOLD"

        # Compute daily signals to detect most recent change
        prev_signal = None
        change_date = None
        sma10_series = prices.rolling(window=10).mean()
        sma20_series = prices.rolling(window=20).mean()
        daily_signals = []
        for i in range(len(prices)):
            if pd.isna(rsi.iloc[i]) or pd.isna(sma20_series.iloc[i]) or pd.isna(sma10_series.iloc[i]):
                daily_signals.append(None)
                continue
            s = 0
            r = float(rsi.iloc[i])
            if r < 30:
                s += 1
            elif r > 70:
                s -= 1
            if sma10_series.iloc[i] > sma20_series.iloc[i]:
                s += 1
            else:
                s -= 1
            if prices.iloc[i] > sma20_series.iloc[i]:
                s += 1
            else:
                s -= 1
            if s >= 2:
                daily_signals.append("BUY")
            elif s <= -2:
                daily_signals.append("SELL")
            else:
                daily_signals.append("HOLD")

        # Walk backwards to find last change
        for j in range(len(daily_signals) - 1, 0, -1):
            if daily_signals[j] is None or daily_signals[j - 1] is None:
                continue
            if daily_signals[j] != daily_signals[j - 1]:
                prev_signal = daily_signals[j - 1]
                change_date = prices.index[j].strftime("%m/%d")
                break

        signals[ticker] = {
            "rsi": round(current_rsi, 1),
            "signal": signal,
            "score": score,
            "sma_cross": sma_cross,
            "price_vs_sma": price_vs_sma,
            "signal_date": change_date,
            "prev_signal": prev_signal,
        }

    return signals


# ---------------------------------------------------------------------------
# 4. Earnings
# ---------------------------------------------------------------------------


def fetch_earnings(tickers: list[str]) -> dict:
    """Fetch earnings calendar + history per ticker (threaded)."""

    def _fetch_one(ticker: str):
        result = {
            "next_date": "",
            "eps_est": None,
            "eps_actual": None,
            "last_earnings_date": "",
            "last_eps_reported": None,
            "last_eps_estimate": None,
        }
        try:
            t = yf.Ticker(ticker)
            cal = t.calendar
            cal_dict = None
            if cal is not None:
                if isinstance(cal, dict):
                    cal_dict = cal
                elif hasattr(cal, "to_dict"):
                    try:
                        cal_dict = (
                            cal.T.iloc[0].to_dict()
                            if hasattr(cal, "T") and len(cal.columns) > 0
                            else None
                        )
                    except Exception:
                        pass
            if cal_dict:
                ed_list = cal_dict.get("Earnings Date", [])
                if not isinstance(ed_list, list):
                    ed_list = [ed_list] if ed_list else []
                if ed_list:
                    try:
                        result["next_date"] = ed_list[0].strftime("%b %d")
                    except Exception:
                        result["next_date"] = str(ed_list[0])[:6] if ed_list[0] else ""
                eps_avg = cal_dict.get("Earnings Average")
                if eps_avg:
                    result["eps_est"] = round(eps_avg, 2)

            # Earnings history
            try:
                eh = t.earnings_history
                if eh is not None and len(eh) > 0:
                    latest = eh.iloc[-1]
                    result["last_earnings_date"] = eh.index[-1].strftime("%b %y")
                    v = latest.get("epsActual")
                    if v is not None and str(v) != "nan":
                        result["last_eps_reported"] = round(float(v), 2)
                    v = latest.get("epsEstimate")
                    if v is not None and str(v) != "nan":
                        result["last_eps_estimate"] = round(float(v), 2)

                    # If earnings date has passed, populate eps_actual
                    if result["next_date"]:
                        try:
                            ed = datetime.datetime.strptime(
                                f"{result['next_date']} {datetime.date.today().year}",
                                "%b %d %Y",
                            ).date()
                            if ed <= datetime.date.today():
                                act = latest.get("epsActual")
                                if act is not None and str(act) != "nan":
                                    result["eps_actual"] = round(float(act), 2)
                        except Exception:
                            pass
            except Exception:
                pass
        except Exception:
            pass
        return ticker, result

    print(f"  Fetching earnings for {len(tickers)} tickers...")
    with ThreadPoolExecutor(max_workers=THREAD_WORKERS) as pool:
        futures = {pool.submit(_fetch_one, t): t for t in tickers}
        results = {}
        for future in as_completed(futures):
            ticker, data = future.result()
            results[ticker] = data
    return results


# ---------------------------------------------------------------------------
# 5. News
# ---------------------------------------------------------------------------


def fetch_news(tickers: list[str]) -> dict:
    """Fetch latest 3 headlines per ticker (threaded)."""

    def _fetch_one(ticker: str):
        items = []
        try:
            t = yf.Ticker(ticker)
            news = t.news
            if news:
                for raw in news[:3]:
                    content = raw.get("content", raw)
                    title = content.get("title", "") or raw.get("title", "")
                    publisher = (
                        content.get("provider", {}).get("displayName", "")
                        if isinstance(content.get("provider"), dict)
                        else raw.get("publisher", "")
                    )
                    link = (
                        content.get("canonicalUrl", {}).get("url", "")
                        if isinstance(content.get("canonicalUrl"), dict)
                        else raw.get("link", "")
                    )
                    pub_time = raw.get("providerPublishTime", content.get("pubDate", ""))
                    if title:
                        items.append(
                            {
                                "title": title,
                                "publisher": publisher,
                                "link": link,
                                "providerPublishTime": pub_time,
                            }
                        )
        except Exception:
            pass
        return ticker, items

    print(f"  Fetching news for {len(tickers)} tickers...")
    with ThreadPoolExecutor(max_workers=THREAD_WORKERS) as pool:
        futures = {pool.submit(_fetch_one, t): t for t in tickers}
        results = {}
        for future in as_completed(futures):
            ticker, items = future.result()
            results[ticker] = items
    return results


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    today = datetime.date.today()
    start = DEFAULT_START
    end = today

    print(f"Stock data fetch — {start} to {end}")
    print("=" * 50)

    players = load_tickers()
    tickers = [p["ticker"] for p in players]
    print(f"Loaded {len(tickers)} tickers from players.json\n")

    # 1. Prices
    print("[1/5] Fetching daily prices...")
    prices = fetch_prices(tickers, start, end)
    print(f"  Got prices for {len(prices)} tickers\n")

    # Derive start/end prices
    start_prices: dict[str, float] = {}
    end_prices: dict[str, float] = {}
    for ticker, series in prices.items():
        sorted_dates = sorted(series.keys())
        if sorted_dates:
            start_prices[ticker] = series[sorted_dates[0]]
            end_prices[ticker] = series[sorted_dates[-1]]

    # 2. Dividends
    print("[2/5] Fetching dividends...")
    dividends = fetch_dividends(tickers, start, end)
    print(f"  Done\n")

    # 3. Signals
    print("[3/5] Computing technical signals...")
    signals = compute_signals(tickers, start, end)
    print(f"  Computed signals for {len(signals)} tickers\n")

    # 4. Earnings
    print("[4/5] Fetching earnings data...")
    earnings = fetch_earnings(tickers)
    print(f"  Done\n")

    # 5. News
    print("[5/5] Fetching news headlines...")
    news = fetch_news(tickers)
    print(f"  Done\n")

    # Build output
    now_et = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=-4)))
    output = {
        "last_updated": now_et.isoformat(),
        "prices": prices,
        "start_prices": start_prices,
        "end_prices": end_prices,
        "dividends": dividends,
        "signals": signals,
        "earnings": earnings,
        "news": news,
    }

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w") as f:
        json.dump(output, f, indent=2, default=str)

    print("=" * 50)
    print(f"Saved to {OUTPUT_PATH}")
    print(f"Last updated: {now_et.isoformat()}")


if __name__ == "__main__":
    main()
