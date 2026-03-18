# Stock Market Fantasy Draft

A Streamlit app that turns a stock-picking pool into a live standings board. Each stock gets the same entry stake, the app tracks price return plus dividends over a selectable date range, and the table ranks every pick from MVP to Benchwarmer.

## Features

- **Standings-style Dashboard** — Sports-inspired Streamlit layout with league-table styling
- **Top 10 / Bottom 10 Charts** — Side-by-side Plotly charts for stocks in the money and out of the money
- **ETF Standing** — Stocks grouped into ETF buckets (`UNCL`, `ANTY`, `KIDZ`) with medal rankings and average performance
- **Leaderboard** — Full ranking with start/end prices, stake, units, profit/(loss), dividends, total return, price return, and total return percentage
- **Dividend Tracking** — Fetches actual dividend payments and calculates income based on shares purchased
- **Ticker Management** — Add and remove stocks directly from the sidebar UI and persist changes to `players.json`
- **Stock Search** — Search for stocks from the sidebar and highlight them on the leaderboard
- **Flexible Date Range** — Pick any start and end date (MM/DD/YYYY) from the sidebar, defaults to PST
- **Mobile Responsive** — Optimized for phone viewing with responsive CSS, touch-friendly charts, and scrollable tables

## Tech Stack

- **Python** + **Streamlit**
- **Plotly**
- **yfinance**
- **pandas**

## Setup

```bash
python3 -m pip install -r requirements.txt
python3 -m streamlit run app.py
```

## Configuration

Edit `players.json` to set the entry stake and starting roster:

```json
{
  "investment_amount": 10.00,
  "players": [
    { "etf": "KIDZ", "name": "Apple", "ticker": "AAPL" },
    { "etf": "UNCL", "name": "NVIDIA", "ticker": "NVDA" }
  ]
}
```

`investment_amount` is the amount assigned to each stock. You can also add and remove tickers from the sidebar in the running app.

## UI Overview

- **League Office** sidebar for date selection, ticker management, and stock search
- **MVP / Benchwarmer** summary cards with ETF emoji markers
- **ETF Standing** showing ETF division performance with medal rankings
- **Leaderboard** with row colors fading from green (positive) to red (negative), with a divider line between positive and negative returns

## Project Structure

```text
├── app.py              # Streamlit application
├── .streamlit/
│   └── config.toml     # Streamlit theme configuration
├── players.json        # Player/ticker configuration
├── send_emails.py      # Email sending script
├── requirements.txt    # Python dependencies
└── README.md
```
