"""Plotly figure builders. Pure: data in, figure out — no Streamlit calls."""

from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go

from smfd.config import GROUP_COLORS, GROUP_EMOJI, GROUP_NAMES

FONT = "Space Grotesk, sans-serif"
TEXT = "#102018"
GRID = "rgba(31, 26, 23, 0.06)"
PAPER = "rgba(0,0,0,0)"
PLOT_BG = "#fbfdf9"

BASE_LAYOUT = dict(
    paper_bgcolor=PAPER,
    plot_bgcolor=PLOT_BG,
    font=dict(family=FONT, color=TEXT),
    hoverlabel=dict(bgcolor="white", font_color=TEXT, font_size=13, bordercolor="#ccc"),
    margin=dict(t=50, r=14, b=40, l=14),
)

CHART_CONFIG = {"displayModeBar": False, "scrollZoom": False}

CHART_COLORS = [
    "#1f77b4", "#e45756", "#2ca02c", "#ff7f0e", "#9467bd",
    "#17becf", "#d62728", "#8c564b", "#e377c2", "#7f7f7f",
]


# --- Growth Chart (weekly rank check-ups, like a pediatrician's chart) ---

def _sigmoid_between(x_from, x_to, y_from, y_to, n=100, smooth=8):
    t = np.linspace(-smooth, smooth, n)
    s = np.exp(t) / (np.exp(t) + 1)
    x_out = x_from + (x_to - x_from) * ((t + smooth) / (2 * smooth))
    y_out = y_from + (y_to - y_from) * s
    return x_out, y_out


def weekly_rank_history(total_returns: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """One 'check-up' per trading week: (sampled returns, full-field ranks).

    Rows are the last trading day of each week (so the latest day is always
    included) plus the very first day. Ranks run across ALL picks — #12 means
    12th in the whole game, not 12th among whichever ten get drawn.
    """
    by_week = pd.Series(total_returns.index, index=total_returns.index).groupby(
        total_returns.index.to_period("W")).last()
    dates = pd.DatetimeIndex(by_week.values)
    if len(total_returns) and total_returns.index[0] not in dates:
        dates = dates.insert(0, total_returns.index[0])
    sampled = total_returns.loc[dates]
    ranks = sampled.rank(axis=1, ascending=False, method="min")
    # Day 0 is an all-zero tie; start each line where week 1 ended instead of
    # stacking the whole field at #1.
    if len(ranks) > 1 and sampled.iloc[0].nunique() == 1:
        ranks.iloc[0] = ranks.iloc[1]
    return sampled, ranks


GROWTH_CHART_HEIGHT = 420
GROWTH_LABEL_PX = 17  # approx pixel height of one end-of-line label


def _dodge_labels(targets: list, lo: float, hi: float, min_sep: float) -> list:
    """Spread 1-D label positions so neighbors sit >= min_sep apart in [lo, hi].

    *targets* must be sorted ascending; order is preserved.
    """
    out = []
    for y in targets:  # push later labels down
        if out and y < out[-1] + min_sep:
            y = out[-1] + min_sep
        out.append(y)
    if out and out[-1] > hi:  # ran past the bottom: pull the stack back up
        out[-1] = hi
        for i in range(len(out) - 2, -1, -1):
            out[i] = min(out[i], out[i + 1] - min_sep)
        out[0] = max(out[0], lo)
    return out


def growth_chart(total_returns: pd.DataFrame, tickers: list, name_map: dict,
                 group_map: dict, title: str) -> go.Figure:
    """Weekly full-field rank trajectories for the given tickers."""
    sampled, ranks_all = weekly_rank_history(total_returns)
    final = sampled.iloc[-1]

    traces = []
    dates = sampled.index
    dates_num = np.arange(len(sampled))

    rank_vals_by_ticker = {t: ranks_all[t].values for t in tickers}
    colors = {t: CHART_COLORS[i % len(CHART_COLORS)] for i, t in enumerate(tickers)}

    for ticker in tickers:
        rank_vals = rank_vals_by_ticker[ticker]
        color = colors[ticker]

        all_x, all_y = [], []
        for j in range(len(rank_vals) - 1):
            sx, sy = _sigmoid_between(dates_num[j], dates_num[j + 1],
                                      rank_vals[j], rank_vals[j + 1])
            all_x.extend(sx)
            all_y.extend(sy)
        d0, d1 = dates[0], dates[-1]
        total_secs = (d1 - d0).total_seconds() or 1
        date_x = [d0 + pd.Timedelta(seconds=(xv / (dates_num[-1] or 1)) * total_secs)
                  for xv in all_x]

        traces.append(go.Scatter(x=date_x, y=all_y, mode="lines",
                                 line=dict(width=3, color=color),
                                 hoverinfo="skip", showlegend=False))
        traces.append(go.Scatter(
            x=list(dates), y=list(rank_vals), mode="markers",
            name=name_map.get(ticker, ticker),
            marker=dict(size=8, color=color, line=dict(width=1.5, color="white")),
            customdata=[round(float(v), 2) for v in sampled[ticker].values],
            hovertemplate="#%{y:.0f} %{fullData.name} %{customdata:.2f}%<extra></extra>",
            showlegend=False,
        ))

    fig = go.Figure(data=traces)

    # End-of-line labels, collision-dodged. The journeys can span the whole
    # field (#65 -> #12) while the endpoints cluster (#1..#10), so labels
    # anchored to the axis would overlap — spread them out and tether each to
    # its line end with a faint connector.
    y_lo = 0.5
    y_hi = max(v.max() for v in rank_vals_by_ticker.values()) + 0.5
    px_per_unit = (GROWTH_CHART_HEIGHT - 90) / (y_hi - y_lo)  # minus t/b margins
    min_sep = GROWTH_LABEL_PX / px_per_unit
    order = sorted(tickers, key=lambda t: rank_vals_by_ticker[t][-1])
    label_ys = _dodge_labels([float(rank_vals_by_ticker[t][-1]) for t in order],
                             y_lo + 0.2, y_hi - 0.2, min_sep)
    for ticker, label_y in zip(order, label_ys):
        end_rank = float(rank_vals_by_ticker[ticker][-1])
        emoji = GROUP_EMOJI.get(group_map.get(ticker, ""), "")
        fig.add_annotation(
            x=dates[-1].isoformat(), y=end_rank,
            text=f"<b>#{int(end_rank)}</b> {emoji} {ticker} {float(final[ticker]):+.2f}%",
            font=dict(size=11, color=colors[ticker]),
            xanchor="left", align="left",
            ax=16, ay=(label_y - end_rank) * px_per_unit,
            showarrow=True, arrowhead=0, arrowwidth=1,
            arrowcolor="rgba(18,51,36,0.3)",
        )

    layout = {**BASE_LAYOUT, "margin": dict(t=50, r=150, b=40, l=14)}
    fig.update_layout(
        title=title, height=GROWTH_CHART_HEIGHT, showlegend=False, hovermode="x",
        title_font=dict(size=18, color=TEXT),
        yaxis=dict(range=[y_hi, y_lo], gridcolor=GRID, side="left",
                   tickfont=dict(size=11), zeroline=False, fixedrange=True,
                   tickformat="d"),
        **layout,
    )
    fig.update_xaxes(showgrid=False, fixedrange=True, tickfont=dict(color=TEXT))
    return fig


# --- Group Battle ---

def group_battle_chart(group_series: pd.DataFrame) -> go.Figure:
    """The 3-line head-to-head: average total return per group over time."""
    fig = go.Figure()
    for g in group_series.columns:
        fig.add_trace(go.Scatter(
            x=group_series.index, y=group_series[g], mode="lines",
            name=f"{GROUP_EMOJI.get(g, '')} {GROUP_NAMES.get(g, g)}",
            line=dict(width=4, color=GROUP_COLORS.get(g)),
            hovertemplate="%{fullData.name} %{y:.2f}%<extra></extra>",
        ))
    fig.add_hline(y=0, line_width=1, line_color="rgba(18,51,36,0.25)")
    fig.update_layout(
        height=380, hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
        yaxis=dict(title="Avg total return (%)", gridcolor=GRID, fixedrange=True),
        **BASE_LAYOUT,
    )
    fig.update_xaxes(showgrid=False, fixedrange=True)
    return fig


# --- Race to the Finish ---

def gap_to_leader_chart(race: pd.DataFrame, group_map: dict, top_n: int = 15) -> go.Figure:
    """Horizontal bars: how far behind the leader each chasing pick sits."""
    chasers = race.iloc[1:top_n + 1][::-1]  # skip the leader; closest at top
    colors = [GROUP_COLORS.get(group_map.get(t, ""), "#5d6f65") for t in chasers.index]
    fig = go.Figure(go.Bar(
        x=chasers["gap_to_leader"], y=list(chasers.index), orientation="h",
        marker_color=colors,
        customdata=np.stack([chasers["total_return_pct"]], axis=-1),
        hovertemplate="%{y}: %{x:.2f} pp behind (at %{customdata[0]:.2f}%)<extra></extra>",
        text=[f"-{v:.1f} pp" for v in chasers["gap_to_leader"]],
        textposition="outside", textfont=dict(size=11),
        cliponaxis=False,  # outside labels must not clip at the plot edge
    ))
    layout = {**BASE_LAYOUT, "margin": dict(t=50, r=58, b=40, l=14)}
    fig.update_layout(
        height=max(330, 28 * len(chasers) + 90),
        xaxis=dict(title="Percentage points behind the leader", gridcolor=GRID,
                   fixedrange=True),
        yaxis=dict(fixedrange=True, tickfont=dict(size=12)),
        **layout,
    )
    return fig


def fmt_odds(p: float) -> str:
    """Probability -> friendly label: 0% / <1% / 42% / >99%."""
    if p <= 0:
        return "0%"
    if p < 0.01:
        return "<1%"
    if p > 0.99:
        return ">99%"
    return f"{p * 100:.0f}%"


def title_odds_chart(race: pd.DataFrame, group_map: dict, top_n: int = 10) -> go.Figure:
    """Horizontal bars: each contender's simulated chance of winning it all."""
    contenders = race[race["title_odds"] > 0].sort_values("title_odds").tail(top_n)
    colors = [GROUP_COLORS.get(group_map.get(t, ""), "#5d6f65") for t in contenders.index]
    fig = go.Figure(go.Bar(
        x=contenders["title_odds"] * 100, y=list(contenders.index), orientation="h",
        marker_color=colors,
        customdata=np.stack([contenders["total_return_pct"]], axis=-1),
        hovertemplate="%{y}: %{x:.1f}% chance to finish #1 "
                      "(at %{customdata[0]:.2f}% today)<extra></extra>",
        text=[fmt_odds(p) for p in contenders["title_odds"]],
        textposition="outside", textfont=dict(size=12),
        cliponaxis=False,  # outside labels must not clip at the plot edge
    ))
    layout = {**BASE_LAYOUT, "margin": dict(t=50, r=58, b=40, l=14)}
    fig.update_layout(
        height=max(330, 32 * len(contenders) + 90),
        xaxis=dict(title="Chance of being #1 on the final day (%)",
                   gridcolor=GRID, fixedrange=True),
        yaxis=dict(fixedrange=True, tickfont=dict(size=12)),
        **layout,
    )
    return fig


# --- Risk & Income ---

def risk_scatter(risk: pd.DataFrame, group_map: dict) -> go.Figure:
    """Volatility vs total return, one dot per pick, colored by group."""
    fig = go.Figure()
    for g, color in GROUP_COLORS.items():
        members = [t for t in risk.index if group_map.get(t) == g]
        if not members:
            continue
        sub = risk.loc[members]
        fig.add_trace(go.Scatter(
            x=sub["annualized_vol_pct"], y=sub["total_return_pct"],
            mode="markers+text", text=list(sub.index), textposition="top center",
            textfont=dict(size=9, color=color),
            name=f"{GROUP_EMOJI.get(g, '')} {GROUP_NAMES.get(g, g)}",
            marker=dict(size=9, color=color, opacity=0.85),
            customdata=np.stack([sub["max_drawdown_pct"]], axis=-1),
            hovertemplate="%{text}: vol %{x:.1f}%, return %{y:.2f}%, "
                          "max drawdown %{customdata[0]:.1f}%<extra></extra>",
        ))
    fig.add_hline(y=0, line_width=1, line_color="rgba(18,51,36,0.25)")
    fig.update_layout(
        height=460, legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
        xaxis=dict(title="Annualized volatility (%)", gridcolor=GRID, fixedrange=True),
        yaxis=dict(title="Total return (%)", gridcolor=GRID, fixedrange=True),
        **BASE_LAYOUT,
    )
    return fig


def income_split_chart(risk: pd.DataFrame, top_n: int = 12) -> go.Figure:
    """Stacked bars: price vs dividend contribution for the top dividend earners."""
    payers = risk[risk["dividend_return_pct"] > 0]
    sub = payers.sort_values("dividend_return_pct", ascending=False).head(top_n)[::-1]
    fig = go.Figure()
    fig.add_trace(go.Bar(
        y=list(sub.index), x=sub["price_return_pct"], orientation="h",
        name="Price", marker_color="#0e5f3a",
        hovertemplate="%{y} price: %{x:.2f}%<extra></extra>"))
    fig.add_trace(go.Bar(
        y=list(sub.index), x=sub["dividend_return_pct"], orientation="h",
        name="Dividends", marker_color="#d7a83a",
        hovertemplate="%{y} dividends: %{x:.2f}%<extra></extra>"))
    fig.update_layout(
        barmode="relative", height=max(330, 30 * len(sub) + 100),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
        xaxis=dict(title="Return contribution (%)", gridcolor=GRID, fixedrange=True),
        yaxis=dict(fixedrange=True),
        **BASE_LAYOUT,
    )
    return fig
