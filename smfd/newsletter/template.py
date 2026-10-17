"""Render a snapshot into a self-contained HTML email (and a plain-text twin).

Email-client rules: inline CSS only (clients strip <style>), single column,
~600px max width, table-based layout, no JavaScript. Every chart except the
group race is drawn with table cells so it survives a paste into Gmail; the
group race is a PNG linked from the public repo (see newsletter/charts.py).
"""

from __future__ import annotations

import datetime
import html as html_mod

from smfd.config import (GAME_END, GAME_START, GROUP_COLORS, GROUP_EMOJI, GROUP_NAMES,
                         GROUP_RACE_PNG_URL, GROUPS)

_GREEN = "#0e5f3a"
_RED = "#b3422f"
_TEXT = "#102018"
_MUTED = "#5d6f65"
_BG = "#f4f7f2"
_PANEL = "#ffffff"
_BORDER = "#dde5dc"
_GOLD = "#b8860b"
_BRIGHT_GOLD = "#d7a83a"
_DARK = "#0d2f20"
_CREAM = "#f4f0e3"

_TABLE = 'role="presentation" width="100%" cellpadding="0" cellspacing="0"'


def _esc(s) -> str:
    return html_mod.escape(str(s))


def _pct(v: float, size: int = 14) -> str:
    color = _GREEN if v >= 0 else _RED
    return f'<span style="color:{color};font-weight:700;font-size:{size}px;">{v:+.1f}%</span>'


def _bar(width_pct: float, color: str, height: int = 12) -> str:
    """A horizontal bar as a two-cell table — the most email-safe bar there is."""
    w = min(max(width_pct, 1.5), 100)
    return (f'<table {_TABLE}><tr><td style="width:{w:.1f}%;height:{height}px;background:{color};'
            f'border-radius:3px;font-size:0;line-height:0;">&nbsp;</td>'
            f'<td style="font-size:0;line-height:0;">&nbsp;</td></tr></table>')


def _section(eyebrow: str, title: str, body: str, sub: str = "") -> str:
    sub_html = (f'<div style="font-size:12px;color:{_MUTED};padding-bottom:8px;">{_esc(sub)}</div>'
                if sub else "")
    return (
        f'<tr><td style="padding:22px 24px 0;">'
        f'<div style="font-size:11px;font-weight:700;letter-spacing:0.1em;text-transform:uppercase;'
        f'color:{_GOLD};">{_esc(eyebrow)}</div>'
        f'<div style="font-size:19px;font-weight:800;color:{_TEXT};padding:2px 0 4px;">{_esc(title)}</div>'
        f'{sub_html}'
        f'<div style="background:{_PANEL};border:1px solid {_BORDER};border-radius:12px;'
        f'padding:14px 16px;">{body}</div></td></tr>'
    )


# --- Header: growth chart toward the first birthday ---

def _month_marks() -> list:
    total = (GAME_END - GAME_START).days
    marks, d = [], datetime.date(GAME_START.year, GAME_START.month, 1)
    while d <= GAME_END:
        x = (d - GAME_START).days / total
        if 0 < x < 1:
            marks.append((x, d.strftime("%b")))
        d = (d + datetime.timedelta(days=32)).replace(day=1)
    return marks


def _growth_chart(s: dict) -> str:
    p = s["progress_pct"]
    ticks, labels, prev = "", "", 0.0
    for x, label in _month_marks():
        w = (x - prev) * 100
        ticks += (f'<td style="width:{w:.2f}%;border-right:1px solid rgba(244,240,227,0.35);'
                  f'height:6px;font-size:0;line-height:0;">&nbsp;</td>')
        labels += (f'<td style="width:{w:.2f}%;font-size:9px;color:rgba(244,240,227,0.55);'
                   f'text-align:right;padding-top:2px;">{label}</td>')
        prev = x
    rest = f'{(1 - prev) * 100:.2f}%'
    ticks += f'<td style="width:{rest};font-size:0;line-height:0;">&nbsp;</td>'
    labels += f'<td style="width:{rest};"></td>'
    months = s["age_months"]
    return f'''
    <div style="margin-top:16px;">
      <table {_TABLE}><tr>
        <td style="font-size:12px;color:{_CREAM};">\U0001f4cf <b>Growth chart</b> · Alessi is {months} month{"" if months == 1 else "s"} old</td>
        <td style="font-size:12px;color:{_BRIGHT_GOLD};text-align:right;font-weight:700;">{p:.0f}% of the way to 1</td>
      </tr></table>
      <table {_TABLE} style="margin-top:6px;border-radius:999px;background:rgba(255,255,255,0.12);">
        <tr><td style="width:{max(p, 2):.1f}%;height:14px;border-radius:999px;background:{_BRIGHT_GOLD};
                       background-image:linear-gradient(90deg,#c9962b,#f0c75e);font-size:0;line-height:0;">&nbsp;</td>
        <td style="font-size:0;line-height:0;">&nbsp;</td></tr></table>
      <table {_TABLE}><tr>{ticks}</tr><tr>{labels}</tr></table>
      <table {_TABLE} style="margin-top:4px;"><tr>
        <td style="font-size:11px;color:rgba(244,240,227,0.7);">\U0001f4c8 Draft day · {GAME_START:%b} {GAME_START.day}</td>
        <td style="font-size:11px;color:rgba(244,240,227,0.7);text-align:right;">\U0001f382 First birthday · {GAME_END:%b} {GAME_END.day}</td>
      </tr></table>
    </div>'''


def _header(s: dict) -> str:
    as_of = datetime.date.fromisoformat(s["as_of"])
    badge = (f'<span style="font-size:11px;font-weight:700;background:{_BRIGHT_GOLD};color:{_DARK};'
             f'padding:4px 10px;border-radius:999px;">{_esc(s["edition"])}</span>'
             if s.get("edition") else "")
    return f'''
  <tr><td style="background-color:{_DARK};background-image:linear-gradient(135deg,#0d2f20,#145236);
                 border-radius:16px;padding:24px;color:{_CREAM};">
    <table {_TABLE}><tr>
      <td style="font-size:11px;font-weight:700;letter-spacing:0.14em;text-transform:uppercase;color:{_BRIGHT_GOLD};">
        \U0001f380 Stock Market Fantasy Draft</td>
      <td style="text-align:right;">{badge}</td>
    </tr></table>
    <div style="font-size:30px;font-weight:800;margin:10px 0 4px;color:{_CREAM};">Alessi's Stock Draft</div>
    <div style="font-size:13px;color:rgba(244,240,227,0.8);">Numbers as of {as_of:%B} {as_of.day}, {as_of.year}</div>
    {_growth_chart(s)}
  </td></tr>'''


def _stat_tiles(s: dict) -> str:
    pl = s["total_value"] - s["total_invested"]
    draft_ret = pl / s["total_invested"] * 100 if s["total_invested"] else 0.0
    tiles = [
        ("The pot", f'${s["total_value"]:,.0f}', f'from ${s["total_invested"]:,.0f} invested',
         _GREEN if pl >= 0 else _RED),
        ("Whole draft", f"{draft_ret:+.1f}%", "if you'd bought every pick",
         _GREEN if draft_ret >= 0 else _RED),
        ("In the green", f'{s["n_up"]} of {s["n_picks"]}', "picks are up", _TEXT),
        ("Days to go", f'{s["days_remaining"]}', f"until {GAME_END:%b} {GAME_END.day}, {GAME_END.year}", _GOLD),
    ]
    cells = "".join(
        f'<td width="25%" style="padding:4px;vertical-align:top;">'
        f'<div style="background:{_PANEL};border:1px solid {_BORDER};border-radius:12px;padding:12px 8px;text-align:center;">'
        f'<div style="font-size:10px;font-weight:700;letter-spacing:0.08em;text-transform:uppercase;color:{_MUTED};">{t}</div>'
        f'<div style="font-size:21px;font-weight:800;color:{c};padding:4px 0 2px;">{v}</div>'
        f'<div style="font-size:11px;color:{_MUTED};line-height:1.3;">{sub}</div></div></td>'
        for t, v, sub, c in tiles)
    return f'<tr><td style="padding:18px 20px 0;"><table {_TABLE}><tr>{cells}</tr></table></td></tr>'


# --- Leaders, basement, everyone ---

def _podium(s: dict) -> str:
    top = s["standings_top"][:3]
    if len(top) < 3:
        return ""
    spots = [(top[1], 70, "\U0001f948", "#a3aca6"), (top[0], 100, "\U0001f947", "#c9962b"),
             (top[2], 50, "\U0001f949", "#b9784a")]
    cells = "".join(
        f'<td width="33%" style="vertical-align:bottom;text-align:center;padding:0 5px;">'
        f'<div style="font-size:26px;">{medal}</div>'
        f'<div style="font-size:17px;font-weight:800;color:{GROUP_COLORS.get(p["etf"], _TEXT)};">{_esc(p["ticker"])}</div>'
        f'<div style="font-size:11px;color:{_MUTED};padding-bottom:4px;">{_esc(p["name"])}</div>'
        f'<div style="background:{color};height:{h}px;border-radius:8px 8px 0 0;color:#ffffff;font-weight:800;'
        f'font-size:16px;padding-top:10px;box-sizing:border-box;">{p["total_return_pct"]:+.0f}%</div></td>'
        for p, h, medal, color in spots)
    return f'<table {_TABLE}><tr>{cells}</tr></table><div style="height:14px;"></div>'


def _ranked_bars(picks: list, first_rank: int, scale: float) -> str:
    rows = ""
    for i, p in enumerate(picks):
        rows += (
            f'<tr><td style="padding:5px 4px;font-size:12px;color:{_MUTED};width:22px;">{first_rank + i}</td>'
            f'<td style="padding:5px 4px;font-size:13px;width:150px;">{GROUP_EMOJI.get(p["etf"], "")} '
            f'<b style="color:{_TEXT};">{_esc(p["ticker"])}</b> '
            f'<span style="color:{_MUTED};font-size:11px;">{_esc(p["name"][:16])}</span></td>'
            f'<td style="padding:5px 4px;">{_bar(abs(p["total_return_pct"]) / scale * 100, GROUP_COLORS.get(p["etf"], _MUTED))}</td>'
            f'<td style="padding:5px 4px;text-align:right;width:62px;">{_pct(p["total_return_pct"], 13)}</td></tr>')
    return f'<table {_TABLE}>{rows}</table>'


def _everyone_chart(s: dict) -> str:
    """All picks as one column chart: bars up from the axis for gains, down for losses."""
    picks = s["all_picks"]
    rets = [p["total_return_pct"] for p in picks]
    hi, lo = max(max(rets), 1), min(min(rets), -1)
    up_h, down_h = 90, 30
    up, down = "", ""
    empty = '<td style="font-size:0;line-height:0;">&nbsp;</td>'
    for p, v in zip(picks, rets):
        c = GROUP_COLORS.get(p["etf"], _MUTED)
        if v >= 0:
            h = max(round(v / hi * up_h), 1)
            up += (f'<td style="vertical-align:bottom;padding:0 1px;"><div style="height:{h}px;background:{c};'
                   f'border-radius:2px 2px 0 0;font-size:0;line-height:0;">&nbsp;</div></td>')
            down += empty
        else:
            h = max(round(v / lo * down_h), 1)
            up += empty
            down += (f'<td style="vertical-align:top;padding:0 1px;"><div style="height:{h}px;background:{c};'
                     f'opacity:0.55;border-radius:0 0 2px 2px;font-size:0;line-height:0;">&nbsp;</div></td>')
    legend = " &nbsp; ".join(
        f'<span style="display:inline-block;width:9px;height:9px;border-radius:2px;background:{GROUP_COLORS[g]};"></span> '
        f'{GROUP_NAMES[g]}' for g in GROUPS)
    n_up = sum(v >= 0 for v in rets)
    first, last = picks[0], picks[-1]
    return f'''
    <table {_TABLE} style="table-layout:fixed;">
      <tr style="height:{up_h}px;">{up}</tr>
      <tr><td colspan="{len(picks)}" style="border-top:2px solid {_TEXT};font-size:0;line-height:0;height:0;">&nbsp;</td></tr>
      <tr style="height:{down_h}px;">{down}</tr>
    </table>
    <table {_TABLE} style="margin-top:6px;"><tr>
      <td style="font-size:11px;color:{_MUTED};">\U0001f451 {_esc(first["ticker"])} {first["total_return_pct"]:+.0f}%</td>
      <td style="font-size:11px;color:{_MUTED};text-align:center;">{n_up} up · {len(picks) - n_up} down</td>
      <td style="font-size:11px;color:{_MUTED};text-align:right;">{_esc(last["ticker"])} {last["total_return_pct"]:+.0f}% \U0001f4a9</td>
    </tr></table>
    <div style="font-size:11px;color:{_MUTED};padding-top:8px;text-align:center;">{legend}</div>'''


# --- Groups, movers, throne, awards ---

def _group_section(s: dict, chart_src: str | None) -> str:
    img = (f'<img src="{_esc(chart_src)}" width="552" style="display:block;width:100%;max-width:552px;'
           f'height:auto;border-radius:6px;" alt="Line chart of each group\'s average return over time">'
           f'<div style="height:12px;"></div>') if chart_src else ""
    medals = {1: "\U0001f947", 2: "\U0001f948", 3: "\U0001f949"}
    top = max((abs(g["avg_return_pct"]) for g in s["group_standings"]), default=1) or 1
    rows = "".join(
        f'<tr><td style="padding:5px 4px;font-size:14px;width:130px;">{medals.get(g["rank"], "")} '
        f'{GROUP_EMOJI.get(g["etf"], "")} <b style="color:{GROUP_COLORS.get(g["etf"], _TEXT)};">'
        f'{_esc(GROUP_NAMES.get(g["etf"], g["etf"]))}</b></td>'
        f'<td style="padding:5px 4px;">{_bar(abs(g["avg_return_pct"]) / top * 100, GROUP_COLORS.get(g["etf"], _MUTED), 16)}</td>'
        f'<td style="padding:5px 4px;text-align:right;width:62px;">{_pct(g["avg_return_pct"])}</td></tr>'
        for g in s["group_standings"])
    note = ""
    if s.get("group_lead_changes"):
        note = f'The group lead has changed hands <b>{s["group_lead_changes"]} times</b>.'
        longest = s.get("group_longest_lead")
        if longest:
            note += f' {GROUP_NAMES[longest["etf"]]} once led {longest["days"]} days straight.'
        note = f'<div style="font-size:12px;color:{_MUTED};padding-top:8px;line-height:1.5;">{note}</div>'
    return img + f'<table {_TABLE}>{rows}</table>' + note


def _movers(s: dict) -> str:
    moves = s["top_movers"] + s["bottom_movers"]
    scale = max((abs(m["period_change_pct"]) for m in moves), default=1) or 1

    def rows(ms, emoji, color):
        return "".join(
            f'<tr><td style="padding:4px;font-size:13px;width:80px;">{emoji} <b>{_esc(m["ticker"])}</b></td>'
            f'<td style="padding:4px;">{_bar(abs(m["period_change_pct"]) / scale * 100, color, 10)}</td>'
            f'<td style="padding:4px;text-align:right;width:74px;font-size:13px;font-weight:700;color:{color};">'
            f'{m["period_change_pct"]:+.1f} pts</td></tr>' for m in ms)

    return (f'<table {_TABLE}>{rows(s["top_movers"], chr(0x1f680), _GREEN)}'
            f'{rows(s["bottom_movers"], chr(0x1f9ca), _RED)}</table>')


def throne_lines(s: dict) -> list:
    """(icon, label, sentence) rows shared by the email, plain text, and PDF."""
    t = s["throne"]
    lines = [("\U0001f451", f'{t["king"]} wears the crown',
              f'{t["king_name"]}, {t["king_days"]} trading days on the throne and counting.')]
    if t.get("longest_reign"):
        r = t["longest_reign"]
        start, end = datetime.date.fromisoformat(r["start"]), datetime.date.fromisoformat(r["end"])
        lines.append(("\U0001f3f0", "Longest reign",
                      f'{r["ticker"]} held #1 for {r["days"]} straight days '
                      f'({start:%b} {start.day} to {end:%b} {end.day}).'))
    crown = f'The #1 spot has changed hands {t["crown_changes"]} times.'
    if t.get("rivalry"):
        rv = t["rivalry"]
        crown += f' {rv["a"]} and {rv["b"]} have swapped it {rv["swaps"]} times.'
    lines.append(("\U0001f501", "Crown changes", crown))
    if t.get("longest_timeout"):
        b = t["longest_timeout"]
        lines.append(("\U0001fa91", "Longest timeout",
                      f'{b["ticker"]} has been dead last for {b["days"]} straight days.'))
    return lines


def _throne(s: dict) -> str:
    rows = "".join(
        f'<tr><td style="padding:7px 4px;font-size:20px;width:34px;vertical-align:top;">{icon}</td>'
        f'<td style="padding:7px 4px;font-size:13px;line-height:1.45;"><b>{_esc(label)}</b><br>'
        f'<span style="color:{_MUTED};">{_esc(text)}</span></td></tr>'
        for icon, label, text in throne_lines(s))
    return f'<table {_TABLE}>{rows}</table>'


def _awards(s: dict) -> str:
    cells = [
        f'<td width="50%" style="padding:5px;vertical-align:top;"><div style="border:1px solid {_BORDER};'
        f'border-radius:10px;padding:10px;background:#fbfaf3;">'
        f'<div style="font-size:22px;">{a["icon"]}</div>'
        f'<div style="font-size:13px;font-weight:800;color:{_TEXT};">{_esc(a["name"])}</div>'
        f'<div style="font-size:11px;color:{_MUTED};">{_esc(a["desc"])}</div>'
        f'<div style="font-size:13px;font-weight:700;color:{_GOLD};padding-top:4px;">{_esc(a["holder"])}</div>'
        f'</div></td>' for a in s["awards"]]
    if len(cells) % 2:
        cells.append('<td width="50%"></td>')
    rows = "".join("<tr>" + "".join(cells[i:i + 2]) + "</tr>" for i in range(0, len(cells), 2))
    return f'<table {_TABLE}>{rows}</table>'


def render_html(snapshot: dict, chart_src: str | None = None) -> str:
    """The email. *chart_src* overrides the group-race image (e.g. a data: URI
    for the in-app preview); by default it links the nightly PNG in the repo,
    cache-busted by date so Gmail's image proxy fetches the right day's chart."""
    s = snapshot
    if chart_src is None and s.get("group_series"):
        chart_src = f'{GROUP_RACE_PNG_URL}?v={s["as_of"]}'
    n = s["n_picks"]
    scale = max((abs(p["total_return_pct"]) for p in s["all_picks"]), default=1) or 1
    bottom = s["standings_bottom"]

    sections = [
        _section("The leaders", "On the podium",
                 _podium(s) + _ranked_bars(s["standings_top"][:5], 1, scale)),
        _section("The basement", f"Bottom {len(bottom)}",
                 _ranked_bars(bottom, n - len(bottom) + 1, scale),
                 "Bars use the same scale as the leaders, so you can see the gap."),
        _section(f"All {n} picks", "Where everyone stands", _everyone_chart(s),
                 "Every pick from best to worst, colored by group."),
        _section("Group race", "Aunties vs Uncles vs Kids", _group_section(s, chart_src)),
        _section("This period", "Biggest movers", _movers(s),
                 f'Change in total return, {s["period_label"]}.'),
        _section("Throne watch", "Who's held the crown", _throne(s)),
    ]
    if s["awards"]:
        sections.append(_section("Award winners", "The trophy shelf", _awards(s)))
    sections += [
        _section("Did you know?", "Fun fact",
                 f'<div style="font-size:14px;line-height:1.55;">\U0001f4a1 {_esc(s["trivia"])}</div>'),
        _section("Today's roast", "Shots fired",
                 f'<div style="font-size:14px;line-height:1.55;font-style:italic;">{_esc(s["roast"])}</div>'),
    ]
    body = "\n".join(sections)

    return f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"></head>
<body style="margin:0;padding:0;background:{_BG};">
<table {_TABLE} style="background:{_BG};">
<tr><td align="center" style="padding:18px 8px;">
<table role="presentation" width="600" cellpadding="0" cellspacing="0"
       style="max-width:600px;width:100%;font-family:Helvetica,Arial,sans-serif;color:{_TEXT};">
{_header(s)}
  <tr><td style="padding:18px 24px 0;">
    <div style="font-size:17px;line-height:1.45;font-weight:700;border-left:4px solid {_BRIGHT_GOLD};
                padding:4px 0 4px 12px;">{_esc(s["headline_stat"])}</div>
  </td></tr>
{_stat_tiles(s)}
{body}
  <tr><td style="padding:22px 24px;text-align:center;color:{_MUTED};font-size:12px;line-height:1.6;">
    $10 per pick, all notional, zero diapers changed by the market.<br>
    Winner crowned <b>{GAME_END:%B} {GAME_END.day}, {GAME_END.year}</b> \U0001f37c Alessi's first birthday
  </td></tr>
</table>
</td></tr>
</table>
</body>
</html>"""


def render_plain_text(snapshot: dict) -> str:
    s = snapshot
    title = "STOCK MARKET FANTASY DRAFT — Alessi's Stock Draft"
    if s.get("edition"):
        title += f" · {s['edition']}"
    lines = [
        title,
        f"Numbers as of {s['as_of']}",
        f"Alessi is {s['age_months']} months old · {s['progress_pct']:.0f}% of the way to her "
        f"first birthday · {s['days_remaining']} days to go",
        "",
        f"THE HEADLINE: {s['headline_stat']}",
        "",
        f"The pot: ${s['total_value']:,.2f} on ${s['total_invested']:,.0f} invested · "
        f"{s['n_up']} of {s['n_picks']} picks are up",
        "",
        "TOP OF THE TABLE",
    ]
    for i, p in enumerate(s["standings_top"][:5], start=1):
        lines.append(f"  {i}. {p['ticker']} ({p['name']}): {p['total_return_pct']:+.1f}%")
    lines += ["", "...AND THE BASEMENT"]
    n = s["n_picks"]
    for i, p in enumerate(s["standings_bottom"]):
        lines.append(f"  {n - len(s['standings_bottom']) + i + 1}. {p['ticker']} "
                     f"({p['name']}): {p['total_return_pct']:+.1f}%")
    lines += ["", "GROUP RACE"]
    for g in s["group_standings"]:
        lines.append(f"  {g['rank']}. {GROUP_NAMES.get(g['etf'], g['etf'])}: "
                     f"{g['avg_return_pct']:+.1f}%")
    lines += ["", f"BIGGEST MOVERS ({s['period_label']})"]
    for m in s["top_movers"]:
        lines.append(f"  up: {m['ticker']} {m['period_change_pct']:+.1f} pts")
    for m in s["bottom_movers"]:
        lines.append(f"  down: {m['ticker']} {m['period_change_pct']:+.1f} pts")
    lines += ["", "THRONE WATCH"]
    lines += [f"  {label}: {text}" for _, label, text in throne_lines(s)]
    if s["awards"]:
        lines += ["", "THE TROPHY SHELF"]
        lines += [f"  {a['name']} ({a['desc']}): {a['holder']}" for a in s["awards"]]
    lines += [
        "",
        f"FUN FACT: {s['trivia']}",
        "",
        f"TODAY'S ROAST: {s['roast']}",
        "",
        f"Game ends {GAME_END:%B} {GAME_END.day}, {GAME_END.year}.",
    ]
    return "\n".join(lines)
