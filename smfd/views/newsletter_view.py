"""Newsletter generator: pick a period, preview, copy/download, self-send.

Renders inside the password-protected Admin tab only (CR-1) — there is no
public newsletter tab. The generated HTML and PDF stay group-safe (no owner
PII). No email infrastructure — Christina pastes the HTML into Gmail (or
forwards the downloaded file) herself. Sent whenever she likes, so the
optional edition name ("Half-Birthday Edition") brands each one.
"""

from __future__ import annotations

import base64
import datetime
import json

import streamlit as st
import streamlit.components.v1 as components

from smfd.data import GameData
from smfd.newsletter import build, charts, pdf, template


@st.cache_data(show_spinner=False, max_entries=8)
def _pdf_bytes(snapshot_json: str) -> bytes | None:
    """Rendering takes a second or two, so cache per snapshot. None = the PDF
    engine isn't installed here (the rest of the newsletter still works)."""
    try:
        return pdf.render_pdf(json.loads(snapshot_json))
    except (ImportError, OSError):
        return None


@st.cache_data(show_spinner=False, max_entries=8)
def _chart_data_uri(series_json: str) -> str:
    png = charts.group_race_png(json.loads(series_json))
    return "data:image/png;base64," + base64.b64encode(png).decode()


def _copy_button(label: str, payload: str, key: str):
    """A small self-contained copy-to-clipboard button (iframe)."""
    components.html(
        f"""
        <style>
        body {{ margin:0; padding:0; }}
        .copy-btn {{
            font-family:'Space Grotesk',sans-serif; width:100%; padding:0.5rem 1rem;
            border:none; border-radius:999px; cursor:pointer; font-weight:700; font-size:0.85rem;
            background:linear-gradient(90deg,#0e5f3a,#0f8773); color:#fff;
        }}
        .copy-btn.copied {{ background:#19a05f; }}
        </style>
        <button class="copy-btn" id="btn_{key}">{label}</button>
        <script>
        var payload_{key} = {json.dumps(payload)};
        document.getElementById("btn_{key}").addEventListener("click", function() {{
            var btn = this;
            navigator.clipboard.writeText(payload_{key}).then(function() {{
                btn.textContent = "✓ Copied!";
                btn.classList.add("copied");
                setTimeout(function() {{
                    btn.textContent = {json.dumps(label)};
                    btn.classList.remove("copied");
                }}, 2000);
            }}).catch(function() {{
                btn.textContent = "Copy failed — use Download";
            }});
        }});
        </script>
        """,
        height=44,
    )


def render(data: GameData, computed: dict):
    st.markdown(
        '<div class="panel-card" style="margin-top:0.6rem;font-size:0.85rem;">'
        '\U0001f4ec Generate a snapshot of the game, then send it yourself: '
        '<b>Copy HTML</b> and paste straight into Gmail compose (it pastes as rich text), '
        'or <b>Download</b> the file and forward it. The newsletter reads the same numbers '
        'as the dashboard, so it can never disagree with the site.</div>',
        unsafe_allow_html=True,
    )

    last = build.last_newsletter_date()
    period_options = {
        "month": "\U0001f4c5 Last month",
        "since_last": ("\U0001f4ee Since last newsletter"
                       + (f" ({last.strftime('%b %d')})" if last else " (none sent yet)")),
        "all": "\U0001f30d All-time",
    }
    pcol, ecol = st.columns([3, 2])
    with pcol:
        period = st.radio("Movers period", list(period_options),
                          format_func=period_options.get, horizontal=True)
    with ecol:
        edition = st.text_input("Edition name (optional)", max_chars=40,
                                placeholder="e.g. Half-Birthday Edition")

    snapshot = build.build_snapshot(data, computed, period=period, edition=edition)
    html = template.render_html(snapshot)
    plain = template.render_plain_text(snapshot)
    pdf_data = _pdf_bytes(json.dumps(snapshot, sort_keys=True))

    cols = st.columns([1, 1, 1, 1, 1])
    with cols[0]:
        _copy_button("\U0001f4cb Copy HTML", html, "html")
    with cols[1]:
        _copy_button("\U0001f4dd Copy plain text", plain, "plain")
    with cols[2]:
        st.download_button(
            "\U0001f4be Download .html",
            data=html,
            file_name=f"fantasy-draft-newsletter-{snapshot['as_of']}.html",
            mime="text/html",
            width="stretch",
        )
    with cols[3]:
        if pdf_data:
            st.download_button(
                "\U0001f5a8 Download PDF",
                data=pdf_data,
                file_name=f"fantasy-draft-print-edition-{snapshot['as_of']}.pdf",
                mime="application/pdf",
                width="stretch",
            )
        else:
            st.button("\U0001f5a8 PDF unavailable", disabled=True, width="stretch",
                      help="The PDF engine (WeasyPrint + Pango) isn't installed on this server.")
    with cols[4]:
        if st.button("\U0001f4ec Mark as sent", width="stretch",
                     help="Logs today as a newsletter date so the next "
                          "'since last newsletter' starts here"):
            build.record_newsletter(snapshot["period_label"],
                                    snapshot.get("roast_key", ""))
            st.toast(f"Logged — next 'since last newsletter' starts "
                     f"{datetime.date.today().strftime('%b %d')}.", icon="✅")
            st.rerun()

    st.caption("The email's group-race chart is linked from the repo and refreshed by the "
               "nightly data update; the preview below draws it fresh.")
    with st.expander(f"\U0001f440 Live Preview — {snapshot['period_label']}", expanded=False):
        preview_chart = (_chart_data_uri(json.dumps(snapshot["group_series"]))
                         if snapshot["group_series"] else None)
        components.html(template.render_html(snapshot, chart_src=preview_chart),
                        height=1400, scrolling=True)
