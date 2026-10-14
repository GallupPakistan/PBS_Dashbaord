"""Dental doctors registered with PMDC (PBS Yearbook table 10-3), 2009-2024."""
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

import chart_helpers as CH

DATA_DIR = "data"
PALETTE = CH.PALETTE


@st.cache_data
def load_dental_registered():
    d = pd.read_excel(f"{DATA_DIR}/No.-of-Dental-Doctors.xls", sheet_name="10-3", header=None)
    rows = []
    for _, r in d.iterrows():
        y = pd.to_numeric(r[0], errors="coerce")
        if pd.isna(y) or not (1990 < y < 2100):
            continue
        v = [pd.to_numeric(x, errors="coerce") for x in r.iloc[1:5]]
        rows.append({"Year": int(y), "Males": v[0], "Females": v[1], "Registered": v[2], "Progressive total": v[3]})
    out = pd.DataFrame(rows).sort_values("Year").reset_index(drop=True)
    out["Female share %"] = (out["Females"] / out["Registered"] * 100).round(1)
    out["YoY %"] = (out["Registered"].pct_change() * 100).round(1)
    return out


def _cat(fig, xs):
    fig.update_xaxes(type="category", tickmode="array", tickvals=list(xs), ticktext=list(xs), tickangle=0)


def render_dental_doctors():
    d = load_dental_registered()
    xs = d["Year"].astype(str)
    last, prev, first = d.iloc[-1], d.iloc[-2], d.iloc[0]
    st.caption("Source: Pakistan Medical & Dental Council (via PBS). Counts are dentists newly registered each year; "
               "the progressive total is all dentists registered since 1952.")
    k = st.columns(5)
    k[0].metric(f"Registered in {int(last['Year'])}", f"{int(last['Registered']):,}", f"{(last['Registered']/prev['Registered']-1)*100:+.1f}% vs {int(prev['Year'])}")
    k[1].metric("Total registered (since 1952)", f"{int(last['Progressive total']):,}")
    k[2].metric("Female share", f"{last['Female share %']:.1f}%", f"{first['Female share %']:.1f}% in {int(first['Year'])}")
    k[3].metric("Peak year", str(int(d.loc[d['Registered'].idxmax(), 'Year'])), f"{int(d['Registered'].max()):,} registered")
    k[4].metric(f"Growth since {int(first['Year'])}", f"{(last['Registered']/first['Registered']-1)*100:+.0f}%", f"{int(first['Registered']):,} → {int(last['Registered']):,}")
    st.divider()

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("#### 1. New registrations per year — male vs female")
        mode = st.radio("View as", ["Count", "% share"], horizontal=True, key="dd_m1", label_visibility="collapsed")
        long = d.melt(id_vars="Year", value_vars=["Males", "Females"], var_name="Sex", value_name="n")
        if mode == "Count":
            long["v"], long["t"] = long["n"], long["n"].map(lambda v: f"{int(v):,}")
        else:
            tot = long.groupby("Year")["n"].transform("sum")
            long["v"] = (long["n"] / tot * 100).round(1)
            long["t"] = long["v"].map(lambda v: f"{v:.0f}%")
        long["Year"] = long["Year"].astype(str)
        fig = px.bar(long, x="Year", y="v", color="Sex", text="t", barmode="stack",
                     color_discrete_sequence=[PALETTE[0], PALETTE[1]])
        fig.update_traces(textposition="inside")
        fig.update_layout(uniformtext_minsize=8, uniformtext_mode="hide", margin=dict(t=30), xaxis_title="",
                          yaxis_title="Dentists registered" if mode == "Count" else "Share (%)", legend_title_text="")
        _cat(fig, xs)
        st.plotly_chart(fig, use_container_width=True)
    with c2:
        st.markdown("#### 2. Total registered per year (with trend line)")
        mode = st.radio("View as", ["Count", f"% change vs {int(first['Year'])}"], horizontal=True, key="dd_m2", label_visibility="collapsed")
        y = d["Registered"].astype(float) if mode == "Count" else (d["Registered"] / first["Registered"] * 100 - 100).round(0)
        fig = go.Figure()
        fig.add_scatter(x=xs, y=y, mode="lines+markers+text", name="Registered", line=dict(color=PALETTE[0]),
                        text=[f"{v:,.0f}" if mode == "Count" else f"{v:+.0f}%" for v in y], textposition="top center")
        import numpy as np
        co = np.polyfit(range(len(d)), y, 1)
        fig.add_scatter(x=xs, y=np.poly1d(co)(range(len(d))), mode="lines", name="Trend", line=dict(dash="dash", color=PALETTE[1]))
        fig.update_layout(margin=dict(t=30), xaxis_title="", legend=dict(orientation="h", y=-0.15),
                          yaxis_title="Registered" if mode == "Count" else "% change")
        _cat(fig, xs)
        st.plotly_chart(fig, use_container_width=True)

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("#### 3. Female share of new registrations (%)")
        fig = px.bar(d, x=xs, y="Female share %", text=d["Female share %"].map(lambda v: f"{v:.0f}%"), color_discrete_sequence=[PALETTE[1]])
        fig.update_traces(textposition="outside", cliponaxis=False)
        fig.update_layout(margin=dict(t=30), xaxis_title="", yaxis_title="Female share (%)", yaxis_range=[0, 100])
        _cat(fig, xs)
        st.plotly_chart(fig, use_container_width=True)
    with c2:
        st.markdown("#### 4. Dentists registered since 1952 (progressive total)")
        fig = px.bar(d, x=xs, y="Progressive total", text=d["Progressive total"].map(lambda v: f"{v/1000:.1f}k"), color_discrete_sequence=[PALETTE[2]])
        fig.update_traces(textposition="outside", cliponaxis=False)
        fig.update_layout(margin=dict(t=30), xaxis_title="", yaxis_title="Dentists")
        _cat(fig, xs)
        st.plotly_chart(fig, use_container_width=True)

    st.markdown("#### 5. Year-over-year change in registrations (%)")
    dd = d.dropna(subset=["YoY %"]).copy()
    dd["Dir"] = (dd["YoY %"] >= 0).map({True: "Increase", False: "Decrease"})
    dd["Year"] = dd["Year"].astype(str)
    fig = px.bar(dd, x="Year", y="YoY %", color="Dir", text=dd["YoY %"].map(lambda v: f"{v:+.1f}%"),
                 color_discrete_map={"Increase": PALETTE[2], "Decrease": PALETTE[1]})
    fig.update_traces(textposition="outside", cliponaxis=False)
    fig.update_layout(margin=dict(t=30), xaxis_title="", legend_title_text="")
    _cat(fig, dd["Year"])
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("#### 6. Full data table")
    st.dataframe(d, use_container_width=True, hide_index=True)
