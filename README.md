# Stock Market Fantasy Draft Tracker

A Streamlit app where players each invest $10 on a stock. The app tracks percentage return (including dividends) over a flexible date range, visualizes performance on a line graph, and ranks players from winner to loser.

## Features

- **Top 10 Line Chart** — Plotly chart showing cumulative % return over time for the top 10 performing stocks
- **Leaderboard** — Full ranking of all stocks with total return, price return, dividends, final value, and profit/loss
- **Dividend Tracking** — Fetches actual dividend payments and calculates income based on shares purchased
- **Add / Remove Tickers** — Manage tickers directly from the sidebar UI (persists to `players.json`)
- **Flexible Date Range** — Pick any start and end date from the sidebar

## Tech Stack

- **Python** + **Streamlit** (UI)
- **Plotly** (interactive charts)
- **yfinance** (free stock data, no API key needed)
- **pandas** (data processing)

## Setup

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Configuration

Edit `players.json` to set the investment amount and starting roster:

```json
{
  "investment_amount": 10.00,
  "players": [
    { "name": "AAPL", "ticker": "AAPL" },
    { "name": "NVDA", "ticker": "NVDA" }
  ]
}
```

You can also add and remove tickers from the sidebar in the running app.

## Project Structure

```
├── app.py              # Streamlit application
├── players.json        # Player/ticker configuration
├── requirements.txt    # Python dependencies
└── README.md
```
