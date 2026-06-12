"""Race to the Finish: the countdown to April 15, 2027."""

from __future__ import annotations

import streamlit as st

from smfd import charts
from smfd.compute import race
from smfd.data import GameData
from smfd.views.common import esc, group_colored, group_emoji, ret_color, section


@st.cache_data(ttl=900, show_spinner=False)
def _race_table(total_returns, scores, today):
    """The race table runs a 2,000-season Monte Carlo — cache it per data drop."""
    return race.race_table(total_returns, scores, today=today)


def render(data: GameData, computed: dict):
    scores = computed["scores"]
    total_returns = computed["total_returns"]

    today = data.prices.index[-1].date() if len(data.prices) else None
    ms = race.milestones(today)
    table = _race_table(total_returns, scores, today)
    if table.empty:
        st.info("No race data yet.")
        return

    # Countdown strip
    pct = ms["pct_complete"]
    st.markdown(
        f'<div class="panel-card" style="margin-top:0.6rem;">'
        f'<div style="display:flex;justify-content:space-between;flex-wrap:wrap;gap:0.6rem;margin-bottom:0.6rem;">'
        f'<div><div style="font-size:1.5rem;font-weight:800;">\U0001f37c {ms["days_remaining"]} days</div>'
        f'<div style="font-size:0.75rem;color:var(--muted);">until Alessi\'s first birthday — '
        f'{ms["end_date"].strftime("%B %d, %Y")}</div></div>'
        f'<div style="text-align:right;"><div style="font-size:1.5rem;font-weight:800;">'
        f'{ms["trading_days_remaining"]}</div>'
        f'<div style="font-size:0.75rem;color:var(--muted);">trading days left</div></div></div>'
        f'<div style="background:rgba(18,51,36,0.06);border-radius:999px;height:14px;overflow:hidden;">'
        f'<div style="width:{pct:.1f}%;height:100%;border-radius:999px;'
        f'background:linear-gradient(90deg,#0e5f3a,#19a05f);"></div></div>'
        f'<div style="font-size:0.7rem;color:var(--muted);margin-top:0.3rem;">'
        f'{pct:.0f}% of the game played</div></div>',
        unsafe_allow_html=True,
    )

    leader = table.index[0]
    runner_up = table.index[1] if len(table) > 1 else None
    catchers = int(table["can_catch_leader"].sum()) - 1  # exclude the leader
    if runner_up is not None:
        st.markdown(
            f'<div class="panel-card" style="margin-top:0.6rem;font-size:0.9rem;">'
            f'{group_emoji(leader, data.group_map)} {group_colored(leader, data.group_map)} leads at '
            f'<b style="color:{ret_color(table.loc[leader, "total_return_pct"])};">'
            f'{table.loc[leader, "total_return_pct"]:+.2f}%</b>, with '
            f'{group_emoji(runner_up, data.group_map)} {group_colored(runner_up, data.group_map)} '
            f'{table.loc[runner_up, "gap_to_leader"]:.2f} pp behind. '
            f'The simulations give <b>{max(catchers, 0)}</b> of {len(table) - 1} chasers '
            f'at least a 1-in-200 shot at the title.</div>',
            unsafe_allow_html=True,
        )

    section("\U0001f3c1", "Distance to the Lead", "closest chasers")
    st.plotly_chart(charts.gap_to_leader_chart(table, data.group_map),
                    use_container_width=True, config=charts.CHART_CONFIG)

    remaining = ms["trading_days_remaining"]
    section("\U0001f3c6", "Title Odds",
            f"chance of being #1 on Alessi's birthday — {race.RACE_SIMS:,} simulated "
            f"runs of the remaining {remaining} trading days, using each pick's real "
            f"day-to-day swings")
    st.plotly_chart(charts.title_odds_chart(table, data.group_map),
                    use_container_width=True, config=charts.CHART_CONFIG)

    # The other end of the stakes: who's most likely to finish dead last.
    spoon = table[table["last_odds"] >= 0.01].sort_values("last_odds", ascending=False).head(5)
    if len(spoon):
        chips = "".join(
            f'<span style="display:inline-flex;align-items:center;gap:0.3rem;'
            f'background:rgba(255,255,255,0.6);border-radius:999px;padding:0.2rem 0.6rem;">'
            f'{group_emoji(t, data.group_map)} {group_colored(t, data.group_map)} '
            f'<b>{charts.fmt_odds(row["last_odds"])}</b></span>'
            for t, row in spoon.iterrows())
        st.markdown(
            f'<div style="display:flex;align-items:center;gap:0.5rem;flex-wrap:wrap;'
            f'padding:0.5rem 0.8rem;background:rgba(209,74,52,0.06);'
            f'border:1px solid rgba(209,74,52,0.18);border-radius:12px;'
            f'font-size:0.78rem;margin-top:0.4rem;">'
            f'<span style="font-weight:700;color:#b91c1c;">\U0001f4a9 Diaper Duty Watch '
            f'— odds of finishing last:</span>{chips}</div>',
            unsafe_allow_html=True,
        )

    section("\U0001f3c3", "The Full Field")
    rows = []
    for rank, (t, row) in enumerate(table.iterrows(), start=1):
        alive = "✅" if row["can_catch_leader"] else "\U0001f480"
        if rank == 1:
            alive = "\U0001f451"
        trend = row["trend_per_day"]
        trend_html = (f'<span style="color:{ret_color(trend)};">'
                      f'{"↗" if trend >= 0 else "↘"} {trend:+.3f}%/day</span>')
        gap_str = "—" if rank == 1 else f'{row["gap_to_leader"]:.2f} pp'
        odds_color = "#19a05f" if row["title_odds"] >= 0.10 else (
            "#102018" if row["title_odds"] >= 0.01 else "#5d6f65")
        rows.append(
            f'<tr><td style="font-weight:700;color:var(--accent);">{rank}</td>'
            f'<td>{group_emoji(t, data.group_map)} {group_colored(t, data.group_map)}'
            f'<br><span style="color:var(--muted);font-size:0.72rem;">{esc(data.name_map.get(t, ""))}</span></td>'
            f'<td style="font-weight:700;color:{ret_color(row["total_return_pct"])};">'
            f'{row["total_return_pct"]:+.2f}%</td>'
            f'<td>{gap_str}</td>'
            f'<td>{trend_html}</td>'
            f'<td style="font-weight:700;color:{odds_color};">'
            f'{charts.fmt_odds(row["title_odds"])}</td>'
            f'<td style="text-align:center;">{alive}</td></tr>'
        )
    st.markdown(
        '<div style="overflow-x:auto;-webkit-overflow-scrolling:touch;border-radius:14px;'
        'border:1px solid var(--border);background:var(--panel-strong);">'
        '<table style="width:100%;min-width:640px;border-collapse:separate;border-spacing:0;font-size:0.8rem;">'
        '<tr>'
        + "".join(
            f'<th style="text-align:left;padding:9px 8px;background:linear-gradient(90deg,#0d2f20,#13492f);'
            f'color:#f4f0e3;font-size:0.68rem;font-weight:700;text-transform:uppercase;letter-spacing:0.06em;">{h}</th>'
            for h in ["#", "Pick", "Total Return", "Gap to #1", "30-day Trend",
                      "Title Odds", "Still Alive?"])
        + '</tr>'
        + "".join(rows)
        + '</table></div>'
        '<div style="font-size:0.68rem;color:var(--muted);margin-top:0.3rem;">'
        f'Title odds = share of {race.RACE_SIMS:,} simulated finishes (each pick replaying '
        'its own real daily swings to the final day) where the pick ends up #1 · '
        '✅ = at least a 1-in-200 simulated shot at the title · \U0001f480 = it happened in '
        'basically none of the simulations · Still a game, not financial advice.</div>',
        unsafe_allow_html=True,
    )
