"""Newsletter editions: email HTML, plain text, and the PDF print edition all
render from one snapshot, stay email-safe, and carry the new sections."""

from __future__ import annotations

import pytest

from smfd.compute import returns
from smfd.config import GROUP_RACE_PNG_URL
from smfd.newsletter import build, charts, pdf, template


@pytest.fixture
def snapshot(fixture_roster):
    data = fixture_roster
    computed = {"scores": returns.compute_scores(data),
                "total_returns": returns.total_return_series(data)}
    return build.build_snapshot(data, computed, period="all", edition="Half-Birthday Edition")


def test_snapshot_carries_every_section(snapshot):
    for key in ("edition", "progress_pct", "age_months", "all_picks", "group_series",
                "throne", "awards", "trivia", "roast", "n_up"):
        assert key in snapshot
    assert snapshot["edition"] == "Half-Birthday Edition"
    assert len(snapshot["all_picks"]) == snapshot["n_picks"] == 4
    assert 0 <= snapshot["progress_pct"] <= 100
    assert len(snapshot["awards"]) <= build.AWARD_COUNT
    assert snapshot["group_series"][-1]["date"] == snapshot["as_of"]


def test_email_is_gmail_safe(snapshot):
    html = template.render_html(snapshot)
    assert "<script" not in html.lower()
    assert "<style" not in html.lower()  # Gmail strips <style>; everything is inline
    assert "data:image" not in html      # Gmail drops pasted data: images
    assert f'{GROUP_RACE_PNG_URL}?v={snapshot["as_of"]}' in html
    assert "Half-Birthday Edition" in html
    for section in ("On the podium", "Where everyone stands", "Throne watch",
                    "Fun fact", "Shots fired"):
        assert section.lower() in html.lower()
    assert "crystal ball" not in html.lower()


def test_preview_can_inline_the_chart(snapshot):
    html = template.render_html(snapshot, chart_src="data:image/png;base64,AAAA")
    assert "data:image/png;base64,AAAA" in html
    assert GROUP_RACE_PNG_URL not in html


def test_plain_text_twin(snapshot):
    text = template.render_plain_text(snapshot)
    assert "Half-Birthday Edition" in text
    assert "THRONE WATCH" in text
    assert snapshot["standings_top"][0]["ticker"] in text


def test_group_race_png(snapshot):
    png = charts.group_race_png(snapshot["group_series"])
    assert png[:8] == b"\x89PNG\r\n\x1a\n"


def test_print_edition_html(snapshot):
    html = pdf.render_print_html(snapshot)
    assert "The Full Table" in html
    assert html.count("<svg") == 2  # group race + every pick
    for p in snapshot["all_picks"]:
        assert p["ticker"] in html
    assert not pdf._EMOJI.search(pdf._clean(snapshot["headline_stat"]))


def test_render_pdf(snapshot):
    pytest.importorskip("weasyprint")
    out = pdf.render_pdf(snapshot)
    assert out[:5] == b"%PDF-"
