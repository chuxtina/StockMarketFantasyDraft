"""PDF print edition: two Letter pages laid out like a magazine.

Page 1: masthead + growth chart, headline, stat tiles, podium + top 10, group
race, every pick as one chart. Page 2: the full table (find your pick),
movers, throne watch, trophy shelf, fun fact, roast.

Rendered with WeasyPrint from the same snapshot as the email. Fonts are
bundled (SIL OFL) so the PDF looks identical everywhere; emoji are stripped
because servers rarely have a color-emoji font.
"""

from __future__ import annotations

import datetime
import html as html_mod
import re

from smfd.config import GAME_END, GAME_START, GROUP_COLORS, GROUP_NAMES, GROUPS
from smfd.newsletter import charts
from smfd.newsletter.template import throne_lines

INK, MUTED, RULE, GOLD, DARK, PAPER = "#13221a", "#5d6f65", "#d9e0d6", "#b8860b", "#0d2f20", "#fbfaf5"
GREEN, RED = "#0e5f3a", "#b3422f"
TABLE_ROWS_PER_COLUMN = 24  # 71 picks -> 3 columns on page 2

_EMOJI = re.compile("[\U0001F000-\U0001FAFF☀-➿⬀-⯿️‍]")


def _esc(s) -> str:
    return html_mod.escape(str(s))


def _clean(s: str) -> str:
    return re.sub(r"\s{2,}", " ", _EMOJI.sub("", s)).strip()


def _pct(v: float) -> str:
    return f'<span class="{"up" if v >= 0 else "dn"}">{v:+.1f}%</span>'


def _dot(etf: str) -> str:
    return f'<i class="dot" style="background:{GROUP_COLORS.get(etf, MUTED)}"></i>'


def _growth_bar(s: dict) -> str:
    total = (GAME_END - GAME_START).days
    ticks, d = "", datetime.date(GAME_START.year, GAME_START.month, 1)
    while d < GAME_END:
        x = (d - GAME_START).days / total * 100
        if 0 < x < 100:
            ticks += f'<span class="tick" style="left:{x:.1f}%"><em>{d:%b}</em></span>'
        d = (d + datetime.timedelta(days=32)).replace(day=1)
    return (f'<div class="growth"><div class="gl"><span>Growth chart · Alessi is {s["age_months"]} months old</span>'
            f'<span>{s["progress_pct"]:.0f}% of the way to one</span></div>'
            f'<div class="track"><div class="fill" style="width:{s["progress_pct"]:.1f}%"></div>{ticks}</div>'
            f'<div class="gl small"><span>Draft day · {GAME_START:%b} {GAME_START.day}, {GAME_START.year}</span>'
            f'<span>First birthday · {GAME_END:%b} {GAME_END.day}, {GAME_END.year}</span></div></div>')


def _tiles(s: dict) -> str:
    pl = s["total_value"] - s["total_invested"]
    draft_ret = pl / s["total_invested"] * 100 if s["total_invested"] else 0.0
    tiles = [("The pot", f'${s["total_value"]:,.0f}', f'from ${s["total_invested"]:,.0f} invested'),
             ("Whole draft", f"{draft_ret:+.1f}%", "every pick, equal stakes"),
             ("In the green", f'{s["n_up"]}<small>/{s["n_picks"]}</small>', "picks are up"),
             ("Days to go", f'{s["days_remaining"]}', "until the final bell")]
    return "".join(f'<div class="tile"><div class="k">{k}</div><div class="v">{v}</div>'
                   f'<div class="s">{sub}</div></div>' for k, v, sub in tiles)


def _podium(s: dict) -> str:
    top = s["standings_top"][:3]
    if len(top) < 3:
        return ""
    spots = [(top[1], "2", 62, "silver"), (top[0], "1", 86, "gold"), (top[2], "3", 46, "bronze")]
    return '<div class="podium">' + "".join(
        f'<div class="pod"><div class="pt">{_esc(p["ticker"])}</div><div class="pn">{_esc(p["name"][:16])}</div>'
        f'<div class="block {cls}" style="height:{h}px"><span class="place">{n}</span>'
        f'<span class="pr">{p["total_return_pct"]:+.0f}%</span></div></div>'
        for p, n, h, cls in spots) + "</div>"


def _top10(s: dict) -> str:
    return '<table class="top10">' + "".join(
        f'<tr><td class="rk">{i}</td><td>{_dot(p["etf"])}<b>{_esc(p["ticker"])}</b> '
        f'<span class="nm">{_esc(p["name"][:20])}</span></td><td class="num">{_pct(p["total_return_pct"])}</td></tr>'
        for i, p in enumerate(s["standings_top"][:10], start=1)) + "</table>"


def _group_rows(s: dict) -> str:
    top = max((abs(g["avg_return_pct"]) for g in s["group_standings"]), default=1) or 1
    return "".join(
        f'<div class="grow"><span class="gn" style="color:{GROUP_COLORS.get(g["etf"], INK)}">'
        f'{g["rank"]}. {GROUP_NAMES.get(g["etf"], g["etf"])}</span>'
        f'<span class="gb"><i style="width:{abs(g["avg_return_pct"]) / top * 100:.0f}%;'
        f'background:{GROUP_COLORS.get(g["etf"], INK)}"></i></span>'
        f'<span class="num">{_pct(g["avg_return_pct"])}</span></div>' for g in s["group_standings"])


def _full_table(s: dict) -> str:
    rows = [f'<tr><td class="rk">{i}</td><td>{_dot(p["etf"])}<b>{_esc(p["ticker"])}</b> '
            f'<span class="nm">{_esc(p["name"][:18])}</span></td><td class="num">{_pct(p["total_return_pct"])}</td></tr>'
            for i, p in enumerate(s["all_picks"], start=1)]
    cols = [rows[i:i + TABLE_ROWS_PER_COLUMN] for i in range(0, len(rows), TABLE_ROWS_PER_COLUMN)]
    return "".join(f'<table class="tbl">{"".join(c)}</table>' for c in cols)


def _movers(s: dict) -> str:
    items = [(m, "up") for m in s["top_movers"]] + [(m, "dn") for m in s["bottom_movers"]]
    return '<ul class="mv">' + "".join(
        f'<li><b>{_esc(m["ticker"])}</b><span class="{cls}">{m["period_change_pct"]:+.1f} pts</span></li>'
        for m, cls in items) + "</ul>"


def _throne(s: dict) -> str:
    return "".join(f'<p class="tw"><span class="lab">{_esc(label)}</span>{_esc(text)}</p>'
                   for _, label, text in throne_lines(s))


def _awards(s: dict) -> str:
    return "".join(f'<div class="aw"><div class="an">{_esc(a["name"])}</div><div class="ad">{_esc(a["desc"])}</div>'
                   f'<div class="ah">{_esc(a["holder"])}</div></div>' for a in s["awards"])


def _font_faces() -> str:
    faces = [("Fraunces", 600, "normal"), ("Fraunces", 800, "normal"), ("Fraunces", 500, "italic"),
             ("Public Sans", 400, "normal"), ("Public Sans", 600, "normal"), ("Public Sans", 800, "normal")]
    out = ""
    for fam, weight, style in faces:
        f = charts.FONTS_DIR / f"{fam.replace(' ', '')}-{weight}{'i' if style == 'italic' else ''}.ttf"
        out += (f"@font-face{{font-family:'{fam}';font-weight:{weight};font-style:{style};"
                f"src:url('{f.as_uri()}')}}\n")
    return out


def _css(footer: str) -> str:
    return _font_faces() + f"""
@page {{ size: Letter; margin: 0.45in 0.5in 0.5in;
  @bottom-left {{ content: "{footer}"; font: 600 7pt 'Public Sans'; color: {MUTED}; }}
  @bottom-right {{ content: "Page " counter(page) " of " counter(pages); font: 600 7pt 'Public Sans'; color: {MUTED}; }} }}
@page :first {{ margin-top: 0; }}
* {{ box-sizing: border-box; }}
body {{ font: 400 8.6pt/1.45 'Public Sans', sans-serif; color: {INK}; margin: 0; }}
.mast {{ background: {DARK}; color: #f4f0e3; margin: 0 -0.5in; padding: 0.38in 0.5in 0.24in; }}
.eyebrow {{ font: 800 7pt 'Public Sans'; letter-spacing: 0.16em; text-transform: uppercase; color: #d7a83a;
  display: flex; justify-content: space-between; }}
.mast h1 {{ font: 800 40pt/1 'Fraunces', serif; margin: 8px 0 4px; letter-spacing: -0.01em; }}
.dateline {{ font: italic 500 11pt 'Fraunces', serif; opacity: 0.85; }}
.growth {{ margin-top: 14px; }}
.gl {{ display: flex; justify-content: space-between; font: 600 7.5pt 'Public Sans'; color: #e8dfc4; }}
.gl.small {{ font-size: 6.5pt; opacity: 0.7; margin-top: 12px; }}
.track {{ position: relative; height: 9px; background: rgba(255,255,255,0.14); border-radius: 9px; margin-top: 5px; }}
.fill {{ height: 9px; border-radius: 9px; background: linear-gradient(90deg,#c9962b,#f0c75e); }}
.tick {{ position: absolute; top: 9px; width: 0; height: 4px; border-left: 0.6pt solid rgba(244,240,227,0.45); }}
.tick em {{ position: absolute; top: 4px; left: -10px; width: 20px; text-align: center;
  font: normal 600 5.5pt 'Public Sans'; color: rgba(244,240,227,0.55); }}
.deck {{ font: 600 14pt/1.3 'Fraunces', serif; margin: 16px 0 12px; padding-bottom: 12px; border-bottom: 1.5pt solid {INK}; }}
.tiles {{ display: flex; gap: 10px; margin-bottom: 16px; }}
.tile {{ flex: 1; border-top: 2.5pt solid {GOLD}; padding-top: 6px; }}
.k, .lab, h2 {{ font: 800 6.8pt 'Public Sans'; letter-spacing: 0.14em; text-transform: uppercase; color: {GOLD}; }}
.v {{ font: 800 21pt/1.1 'Fraunces', serif; margin: 2px 0; }}
.v small {{ font-size: 11pt; color: {MUTED}; }}
.s {{ font-size: 7pt; color: {MUTED}; }}
.cols {{ display: flex; gap: 22px; }}
.col {{ flex: 1; min-width: 0; }}
h2 {{ margin: 0 0 2px; }}
h3 {{ font: 800 13pt/1.2 'Fraunces', serif; margin: 0 0 8px; }}
.podium {{ display: flex; align-items: flex-end; gap: 6px; margin-bottom: 10px; }}
.pod {{ flex: 1; text-align: center; }}
.pt {{ font: 800 11pt 'Fraunces', serif; }}
.pn {{ font-size: 6.5pt; color: {MUTED}; margin-bottom: 3px; }}
.block {{ border-radius: 4px 4px 0 0; color: #fff; padding-top: 5px; display: flex; flex-direction: column; align-items: center; }}
.block.gold {{ background: #c9962b; }} .block.silver {{ background: #9aa59e; }} .block.bronze {{ background: #b9784a; }}
.place {{ font: 800 15pt/1 'Fraunces', serif; }}
.pr {{ font: 800 8pt 'Public Sans'; }}
.top10 {{ width: 100%; border-collapse: collapse; }}
.top10 td {{ padding: 2.2px 0; border-bottom: 0.5pt solid {RULE}; }}
.up {{ color: {GREEN}; font-weight: 800; }} .dn {{ color: {RED}; font-weight: 800; }}
.num {{ text-align: right; font-variant-numeric: tabular-nums; white-space: nowrap; }}
.rk {{ width: 16px; color: {MUTED}; font-size: 7pt; }}
.nm {{ color: {MUTED}; font-size: 6.8pt; }}
.dot {{ display: inline-block; width: 6px; height: 6px; border-radius: 50%; margin-right: 4px; vertical-align: 1px; }}
.chart svg {{ width: 100%; height: auto; }}
.grow {{ display: flex; align-items: center; gap: 6px; margin-top: 4px; }}
.gn {{ width: 62px; font-weight: 800; }}
.gb {{ flex: 1; }} .gb i {{ display: block; height: 7px; border-radius: 4px; }}
.strip {{ margin-top: 16px; padding-top: 10px; border-top: 1.5pt solid {INK}; }}
.strip h3 {{ display: flex; justify-content: space-between; align-items: baseline; }}
.legend {{ font: 400 7pt 'Public Sans'; color: {MUTED}; }}
.legend i {{ display: inline-block; width: 7px; height: 7px; border-radius: 2px; margin: 0 3px 0 8px; vertical-align: -0.5px; }}
.p2 {{ page-break-before: always; }}
.p2 h1 {{ font: 800 22pt/1 'Fraunces', serif; margin: 0 0 2px; }}
.sub {{ font: italic 500 9.5pt 'Fraunces', serif; color: {MUTED}; margin-bottom: 10px; }}
.tables {{ display: flex; gap: 16px; padding-bottom: 12px; border-bottom: 1.5pt solid {INK}; }}
.tbl {{ flex: 1; border-collapse: collapse; font-size: 7.6pt; }}
.tbl td {{ padding: 1.6px 0; border-bottom: 0.5pt solid {RULE}; }}
.three {{ display: flex; gap: 20px; margin-top: 14px; }}
.three > div {{ flex: 1; min-width: 0; }}
.mv {{ list-style: none; padding: 0; margin: 0; }}
.mv li {{ display: flex; justify-content: space-between; padding: 2.5px 0; border-bottom: 0.5pt solid {RULE}; }}
.tw {{ margin: 0 0 6px; }} .tw .lab {{ display: block; color: {MUTED}; letter-spacing: 0.1em; }}
.awards {{ display: flex; flex-wrap: wrap; gap: 6px; }}
.aw {{ width: calc(50% - 3px); background: {PAPER}; border: 0.5pt solid {RULE}; border-radius: 4px; padding: 5px 6px; }}
.an {{ font: 800 8pt 'Fraunces', serif; }} .ad {{ font-size: 6.3pt; color: {MUTED}; }}
.ah {{ font-weight: 800; color: {GOLD}; font-size: 7.3pt; }}
.closer {{ display: flex; gap: 20px; margin-top: 14px; padding-top: 10px; border-top: 1.5pt solid {INK}; }}
.closer > div {{ flex: 1; }}
.quote {{ font: italic 500 10pt/1.4 'Fraunces', serif; }}
.sign {{ text-align: center; margin-top: 16px; font: italic 500 9pt 'Fraunces', serif; color: {MUTED}; }}
"""


def render_print_html(snapshot: dict) -> str:
    """The print edition as HTML (WeasyPrint input; also handy for tests)."""
    s = snapshot
    as_of = datetime.date.fromisoformat(s["as_of"])
    edition = s.get("edition") or "Newsletter"
    footer = f"Alessi's Stock Draft · {edition}".replace('"', "'")
    legend = "".join(f'<i style="background:{GROUP_COLORS[g]}"></i>{GROUP_NAMES[g]}' for g in GROUPS)
    race = charts.group_race_svg(s["group_series"]) if s.get("group_series") else ""
    awards = (f'<div><h2>Award winners</h2><h3>The trophy shelf</h3><div class="awards">{_awards(s)}</div></div>'
              if s["awards"] else "")
    n = s["n_picks"]
    return f"""<html><head><meta charset="utf-8"><style>{_css(footer)}</style></head><body>
<section class="mast">
  <div class="eyebrow"><span>Stock Market Fantasy Draft</span><span>{_esc(edition)} · {as_of:%B} {as_of.day}, {as_of.year}</span></div>
  <h1>Alessi's Stock Draft</h1>
  <div class="dateline">{n} stock picks, one race to Alessi's first birthday. Here's where it all stands.</div>
  {_growth_bar(s)}
</section>
<div class="deck">{_esc(_clean(s["headline_stat"]))}</div>
<div class="tiles">{_tiles(s)}</div>
<div class="cols">
  <div class="col"><h2>The leaders</h2><h3>On the podium</h3>{_podium(s)}{_top10(s)}</div>
  <div class="col"><h2>Group race</h2><h3>Aunties vs Uncles vs Kids</h3><div class="chart">{race}</div>{_group_rows(s)}</div>
</div>
<div class="strip"><h2>All {n} picks</h2><h3>Where everyone stands <span class="legend">{legend}</span></h3>
  <div class="chart">{charts.all_picks_svg(s["all_picks"])}</div></div>

<section class="p2">
  <h1>The Full Table</h1>
  <div class="sub">Every pick, best to worst. Find yours.</div>
  <div class="tables">{_full_table(s)}</div>
  <div class="three">
    <div><h2>This period</h2><h3>Biggest movers</h3>{_movers(s)}</div>
    <div><h2>Throne watch</h2><h3>Who's held the crown</h3>{_throne(s)}</div>
    {awards}
  </div>
  <div class="closer">
    <div><h2>Did you know?</h2><div class="quote">{_esc(_clean(s["trivia"]))}</div></div>
    <div><h2>Shots fired</h2><div class="quote">{_esc(_clean(s["roast"]))}</div></div>
  </div>
  <div class="sign">$10 per pick, all notional. The winner is crowned {GAME_END:%B} {GAME_END.day}, {GAME_END.year}, on Alessi's first birthday.</div>
</section>
</body></html>"""


def render_pdf(snapshot: dict) -> bytes:
    """PDF bytes. WeasyPrint is imported lazily: it needs the Pango system
    library (packages.txt on Streamlit Cloud), and a missing one should only
    disable the PDF button, never the app."""
    from weasyprint import HTML

    return HTML(string=render_print_html(snapshot)).write_pdf()
