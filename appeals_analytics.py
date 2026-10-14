"""Appeals & Petitions in the High Courts (PBS Yearbook table 19.6).

The source sheet holds many stacked blocks:
    Pakistan | Islamabad | Punjab (Lahore HC) | Sindh | Khyber Pakhtunkhwa | Balochistan
    each with  A) Appeals  and  B) Petitions,  one row per year.
Year labels carry footnote marks ('2021*', '2020 (P)'), which must be kept, not dropped.
"""
import re
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

import chart_helpers as CH

DATA_DIR = "data"
PALETTE = CH.PALETTE
COLS = ["Last Balance", "Fresh Registered", "Included Remaining", "Total for Disposal",
        "Disposed off", "Physical Verification", "Transferred", "Pending"]
COURT_ORDER = ["Pakistan", "Islamabad", "Punjab (Lahore HC)", "Sindh", "Khyber Pakhtunkhwa", "Balochistan"]


def _court(label):
    s = str(label).strip().lower()
    if s == "pakistan":
        return "Pakistan"
    if s == "islamabad":
        return "Islamabad"
    if s == "punjab":
        return "Punjab (Lahore HC)"
    if s.startswith("sindh"):
        return "Sindh"
    if s.startswith("khyber"):
        return "Khyber Pakhtunkhwa"
    if s == "balochistan":
        return "Balochistan"
    return None


@st.cache_data
def load_appeals():
    df = pd.read_excel(f"{DATA_DIR}/Appeal-and-Petition-Hogh-Courts-1.xls", sheet_name=0, header=None)
    rows, court, ctype = [], None, None
    for _, r in df.iterrows():
        c0 = r[0]
        if pd.isna(c0):
            continue
        s = str(c0).strip()
        c = _court(s)
        if c:
            court, ctype = c, None
            continue
        low = s.lower()
        if low.startswith(("a-", "a.", "a -")):
            ctype = "Appeals"
            continue
        if low.startswith(("b-", "b.", "b -")):
            ctype = "Petitions"
            continue
        m = re.match(r"^(\d{4})\s*(.*)$", s)
        if not m or court is None or ctype is None:
            continue
        mark = m.group(2).strip()
        vals = [pd.to_numeric(v, errors="coerce") for v in r.iloc[1:9].tolist()]
        rec = dict(zip(COLS, vals))
        rec.update({"Court": court, "Case type": ctype, "Year": int(m.group(1)), "Mark": mark})
        rows.append(rec)
    out = pd.DataFrame(rows)
    out["Disposal rate %"] = (out["Disposed off"] / out["Total for Disposal"] * 100).round(1)
    out["Clearance ratio"] = (out["Disposed off"] / out["Fresh Registered"]).round(2)
    return out


# ------------------------------------------------------------------ helpers
def _kpi(items):
    cols = st.columns(len(items))
    for c, (l, v, d) in zip(cols, items):
        c.metric(l, v, d)


_sec = {"n": 0}


def _section(t):
    _sec["n"] += 1
    st.markdown(f"#### {_sec['n']}. {t}")


def _k(n):
    n = float(n)
    return f"{n/1e6:.2f}M" if abs(n) >= 1e6 else f"{n:,.0f}"


def _mode(key, opts):
    return st.radio("View as", list(opts), horizontal=True, key=key, label_visibility="collapsed")


def _cat(fig, xs):
    fig.update_xaxes(type="category", tickmode="array", tickvals=list(xs), ticktext=list(xs), tickangle=0)


# ------------------------------------------------------------------ render
def render_appeals():
    _sec["n"] = 0
    df = load_appeals()

    c1, c2 = st.columns([2, 1])
    with c1:
        court = st.radio("Court", COURT_ORDER, horizontal=True, key="ap_court")
    with c2:
        ctype = st.radio("Case type", ["Appeals", "Petitions"], horizontal=True, key="ap_type")

    d = df[(df["Court"] == court) & (df["Case type"] == ctype)].sort_values("Year").reset_index(drop=True)
    if d.empty:
        st.info("No data for this selection.")
        return

    if court == "Pakistan":
        st.warning("**Not comparable across 2020 → 2021:** from 2021 PBS's national figures **exclude the Lahore High "
                   "Court** (its data was not supplied), so the national numbers drop sharply in 2021 for that reason, "
                   "not because the case load fell. Compare years before 2021 and from 2021 separately, or use the "
                   "individual courts below.")
    if court == "Punjab (Lahore HC)":
        st.warning("**Lahore High Court data ends at 2020**, and the 2020 row is marked provisional (P) and is identical "
                   "to 2019 — treat 2020 as a placeholder. 2011 (marked *) includes cases transferred from the "
                   "Rawalpindi Bench to Islamabad High Court.")
    marks = d[d["Mark"] != ""]
    if len(marks) and court not in ("Pakistan", "Punjab (Lahore HC)"):
        st.caption("PBS footnote marks: " + ", ".join(f"{int(y)} ({m})" for y, m in zip(marks["Year"], marks["Mark"])))

    last, first = d.iloc[-1], d.iloc[0]
    prev = d.iloc[-2] if len(d) > 1 else last
    _kpi([
        (f"Pending ({int(last['Year'])})", _k(last["Pending"]), f"{(last['Pending']/prev['Pending']-1)*100:+.1f}% vs {int(prev['Year'])}"),
        ("Fresh registered", _k(last["Fresh Registered"]), None),
        ("Disposed off", _k(last["Disposed off"]), None),
        ("Disposal rate", f"{last['Disposal rate %']:.1f}%", "disposed ÷ total for disposal"),
        (f"Pending vs {int(first['Year'])}", f"{(last['Pending']/first['Pending']-1)*100:+.0f}%", f"{_k(first['Pending'])} → {_k(last['Pending'])}"),
    ])
    st.divider()

    xs = d["Year"].astype(str)
    c1, c2 = st.columns(2)
    with c1:
        _section(f"Pending {ctype.lower()} over time (with trend line)")
        mode = _mode("ap_m1", ("Count", f"% change vs {int(first['Year'])}"))
        y = d["Pending"].astype(float)
        if mode != "Count":
            y = (y / float(first["Pending"]) * 100 - 100).round(1)
        fig = go.Figure()
        fig.add_scatter(x=xs, y=y, mode="lines+markers+text", name="Pending", line=dict(color=PALETTE[0]),
                        text=[(f"{v:+.1f}%" if mode != "Count" else _k(v)) for v in y],
                        textposition="top center", texttemplate="%{text}")
        if len(d) >= 3:
            co = np.polyfit(range(len(d)), y.fillna(y.mean()), 1)
            fig.add_scatter(x=xs, y=np.poly1d(co)(range(len(d))), mode="lines", name="Trend",
                            line=dict(dash="dash", color=PALETTE[1]))
        fig.update_layout(margin=dict(t=30), xaxis_title="", yaxis_title="Pending" if mode == "Count" else "% change",
                          legend=dict(orientation="h", y=-0.15))
        _cat(fig, xs)
        st.plotly_chart(fig, use_container_width=True)
    with c2:
        _section("Fresh registered vs disposed off")
        mode = _mode("ap_m2", ("Count", "Disposed as % of fresh"))
        fig = go.Figure()
        if mode == "Count":
            for i, col in enumerate(["Fresh Registered", "Disposed off"]):
                fig.add_scatter(x=xs, y=d[col], mode="lines+markers+text", name=col, line=dict(color=PALETTE[i + 1]),
                                text=[_k(v) if pd.notna(v) else "" for v in d[col]],
                                textposition="top center" if i == 0 else "bottom center", texttemplate="%{text}")
            yt = "Cases"
        else:
            r = (d["Disposed off"] / d["Fresh Registered"] * 100).round(1)
            fig.add_scatter(x=xs, y=r, mode="lines+markers+text", name="Disposed ÷ fresh (%)",
                            line=dict(color=PALETTE[2]), text=[f"{v:.0f}%" for v in r], textposition="top center",
                            texttemplate="%{text}")
            fig.add_hline(y=100, line_dash="dot", line_color="gray")
            yt = "% of fresh cases disposed"
        fig.update_layout(margin=dict(t=30), xaxis_title="", yaxis_title=yt, legend=dict(orientation="h", y=-0.15))
        _cat(fig, xs)
        st.plotly_chart(fig, use_container_width=True)
        st.caption("Above 100% = the court cleared more cases than were newly filed (backlog shrinking).")

    c1, c2 = st.columns(2)
    with c1:
        _section("Disposal rate (%) — share of cases cleared each year")
        fig = px.bar(d, x=xs, y="Disposal rate %", text=d["Disposal rate %"].map(lambda v: f"{v:.1f}%"),
                     color_discrete_sequence=[PALETTE[2]])
        fig.update_traces(textposition="outside", cliponaxis=False)
        fig.update_layout(margin=dict(t=30), xaxis_title="", yaxis_title="Disposed ÷ total for disposal (%)")
        _cat(fig, xs)
        st.plotly_chart(fig, use_container_width=True)
    with c2:
        _section("Year-over-year change in pending cases (%)")
        yoy = (d["Pending"].astype(float).pct_change() * 100).round(1)
        dd = pd.DataFrame({"Year": xs, "YoY": yoy}).dropna()
        fig = px.bar(dd, x="Year", y="YoY", text=dd["YoY"].map(lambda v: f"{v:+.1f}%"),
                     color=(dd["YoY"] >= 0).map({True: "Backlog grew", False: "Backlog shrank"}),
                     color_discrete_map={"Backlog grew": PALETTE[1], "Backlog shrank": PALETTE[2]})
        fig.update_traces(textposition="outside", cliponaxis=False)
        fig.update_layout(margin=dict(t=30), xaxis_title="", yaxis_title="% change in pending", legend_title_text="")
        _cat(fig, dd["Year"])
        st.plotly_chart(fig, use_container_width=True)

    _section(f"Court comparison — pending {ctype.lower()} in a chosen year")
    allc = df[(df["Case type"] == ctype) & (df["Court"] != "Pakistan")]
    years = sorted(allc["Year"].unique().tolist())
    cc1, cc2 = st.columns([2, 1])
    with cc1:
        yr = st.select_slider("Year", options=years, value=2024 if 2024 in years else years[-1], key="ap_year")
    with cc2:
        mode = _mode("ap_m5", ("Count", "% of the courts shown"))
    cmp_ = allc[allc["Year"] == yr].sort_values("Pending", ascending=False)
    if cmp_.empty:
        st.info("No court reported this year.")
    else:
        tot = cmp_["Pending"].sum()
        cmp_ = cmp_.assign(Value=cmp_["Pending"] if mode == "Count" else (cmp_["Pending"] / tot * 100).round(1))
        cmp_["Label"] = cmp_["Value"].map(_k if mode == "Count" else (lambda v: f"{v:.1f}%"))
        fig = px.bar(cmp_, x="Court", y="Value", text="Label", color_discrete_sequence=[PALETTE[0]])
        fig.update_traces(textposition="outside", cliponaxis=False)
        fig.update_layout(margin=dict(t=30), xaxis_title="",
                          yaxis_title="Pending cases" if mode == "Count" else "Share of pending (%)")
        st.plotly_chart(fig, use_container_width=True)
        missing = [c for c in COURT_ORDER[1:] if c not in set(cmp_["Court"])]
        if missing:
            st.caption("Not reported for this year: " + ", ".join(missing))

    _section("Full data table")
    st.dataframe(d.drop(columns=["Court", "Case type"]), use_container_width=True, hide_index=True)
