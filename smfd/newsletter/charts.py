"""Static newsletter charts (matplotlib): data in, PNG/SVG out.

Email clients run no JavaScript and Gmail drops pasted data: images, so the
email's one real chart (the group race) is a PNG rendered nightly by the
fetch job and linked from the public repo. The PDF edition embeds crisp SVGs.

    python -m smfd.newsletter.charts    # (re)render data/newsletter/group_race.png
"""

from __future__ import annotations

import io
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.dates as mdates  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402
from matplotlib import font_manager  # noqa: E402
from matplotlib.ticker import FuncFormatter  # noqa: E402

from smfd.config import GROUP_COLORS, GROUP_NAMES, GROUP_RACE_PNG_PATH, GROUPS  # noqa: E402

FONTS_DIR = Path(__file__).resolve().parent / "fonts"

INK, MUTED, RULE, GRID = "#13221a", "#5d6f65", "#cfd8ce", "#e4e9e2"

for _f in FONTS_DIR.glob("PublicSans-*.ttf"):
    font_manager.fontManager.addfont(str(_f))
_FONT = {"font.family": ["Public Sans", "DejaVu Sans"], "svg.fonttype": "path"}


def _style(ax):
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_color(RULE)
    ax.tick_params(colors=MUTED, length=0)
    ax.grid(axis="y", color=GRID, lw=0.7)
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:+.0f}%"))


def _dodge(values: dict, min_gap: float) -> dict:
    """Nudge end-of-line label positions apart so close groups don't overlap."""
    placed, prev = {}, None
    for y, g in sorted((v, g) for g, v in values.items()):
        if prev is not None and y - prev < min_gap:
            y = prev + min_gap
        placed[g] = prev = y
    return placed


def _group_race_fig(group_series: list, size: tuple, label_size: float, lw: float):
    df = pd.DataFrame(group_series)
    df["date"] = pd.to_datetime(df["date"])
    df = df.set_index("date")
    cols = [g for g in GROUPS if g in df.columns]
    fig, ax = plt.subplots(figsize=size)
    last = df.iloc[-1]
    span = max(float(df[cols].max().max() - df[cols].min().min()), 1.0)
    label_y = _dodge({g: float(last[g]) for g in cols}, span * 0.09)
    for g in cols:
        ax.plot(df.index, df[g], color=GROUP_COLORS[g], lw=lw, solid_capstyle="round")
        ax.plot(df.index[-1], last[g], "o", color=GROUP_COLORS[g], ms=lw * 2)
        ax.annotate(f"{GROUP_NAMES[g]} {last[g]:+.0f}%", (df.index[-1], label_y[g]),
                    xytext=(6, 0), textcoords="offset points", va="center",
                    fontsize=label_size, fontweight=800, color=GROUP_COLORS[g])
    ax.axhline(0, color=INK, lw=0.7, alpha=0.5)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b"))
    ax.set_xlim(df.index[0], df.index[-1] + (df.index[-1] - df.index[0]) * 0.2)
    ax.tick_params(labelsize=label_size - 1)
    _style(ax)
    fig.tight_layout(pad=0.3)
    return fig


def group_race_png(group_series: list) -> bytes:
    """600px-wide email chart (rendered at 2x for retina)."""
    with plt.rc_context(_FONT):
        fig = _group_race_fig(group_series, (6.0, 2.9), 9, 2.4)
        buf = io.BytesIO()
        fig.savefig(buf, format="png", dpi=200, facecolor="white")
    plt.close(fig)
    return buf.getvalue()


def _svg(fig) -> str:
    buf = io.StringIO()
    fig.savefig(buf, format="svg", transparent=True)
    plt.close(fig)
    out = buf.getvalue()
    return out[out.index("<svg"):]


def group_race_svg(group_series: list) -> str:
    """Half-column chart for the PDF edition."""
    with plt.rc_context(_FONT):
        return _svg(_group_race_fig(group_series, (3.55, 2.25), 7.5, 1.8))


def all_picks_svg(all_picks: list) -> str:
    """Every pick, best to worst, one bar each, colored by group (PDF)."""
    with plt.rc_context(_FONT):
        rets = [p["total_return_pct"] for p in all_picks]
        fig, ax = plt.subplots(figsize=(7.4, 1.55))
        ax.bar(range(len(rets)), rets, width=0.78,
               color=[GROUP_COLORS.get(p["etf"], MUTED) for p in all_picks])
        ax.axhline(0, color=INK, lw=0.8)
        if all_picks:
            ax.annotate(all_picks[0]["ticker"], (0, rets[0]), xytext=(0, 2),
                        textcoords="offset points", ha="center", fontsize=6,
                        color=INK, fontweight=800)
            ax.annotate(all_picks[-1]["ticker"], (len(rets) - 1, rets[-1]), xytext=(0, -8),
                        textcoords="offset points", ha="center", fontsize=6,
                        color=INK, fontweight=800)
        ax.set_xticks([])
        ax.set_xlim(-1, len(rets))
        ax.tick_params(labelsize=6.5)
        _style(ax)
        ax.spines["bottom"].set_visible(False)
        fig.tight_layout(pad=0.2)
        return _svg(fig)


def write_group_race_png(path: Path = GROUP_RACE_PNG_PATH) -> Path:
    """Render the email chart from the current data file (used by the nightly job)."""
    from smfd.compute import returns
    from smfd.data import load_game_data
    from smfd.newsletter.build import weekly_group_series

    data = load_game_data()
    total = returns.total_return_series(data)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(group_race_png(weekly_group_series(total, data.group_map)))
    return path


if __name__ == "__main__":
    print(f"wrote {write_group_race_png()}")
