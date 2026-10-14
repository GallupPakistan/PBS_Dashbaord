"""Museums & Heritage Sites dashboard tabs (2015-2025).

Three tabs, one shared engine:
    render_museums()   - museums, annual 2015-2025
    render_heritage()  - heritage sites, annual 2015-2025
    render_monthly()   - month-by-month pattern 2022-2025 (museums + heritage)

Every number comes from heritage_loaders.py (PBS annual + monthly tables).
Count / % toggles are built in; every '%' is a share or change computed live.
"""
import re
from collections import Counter
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

import heritage_loaders as HL
import chart_helpers as CH

PALETTE = CH.PALETTE
LAHORE = HL.LAHORE_TRIO
FIRST_YEAR, LAST_FULL_YEAR, YTD_YEAR = 2015, 2024, 2025
KIND_LABEL = {"museum": "Museums", "heritage": "Heritage sites"}


# ------------------------------------------------------------------ helpers
def kpi_row(items):
    cols = st.columns(len(items))
    for c, (label, value, delta) in zip(cols, items):
        c.metric(label, value, delta)


_sec = {"n": 0}


def section(title):
    """Auto-numbered section heading (numbers stay correct when sections are added)."""
    _sec["n"] += 1
    st.markdown(f"#### {_sec['n']}. {re.sub(r'^[0-9]+[.] *', '', title)}")


def _mode(key, options=("Count", "%")):
    return st.radio("View as", list(options), horizontal=True, key=key, label_visibility="collapsed")


def _fmt(n):
    return f"{n:,.0f}"


def _k(n):
    """Compact label: 6,793,503 -> 6.79M, 674,000 -> 674k."""
    n = float(n)
    if abs(n) >= 1e6:
        return f"{n/1e6:.2f}M"
    if abs(n) >= 1e4:
        return f"{n/1e3:.0f}k"
    return f"{n:,.0f}"


def _cat_axis(fig, xs):
    fig.update_xaxes(type="category", tickmode="array", tickvals=list(xs), ticktext=list(xs), tickangle=0)


def _spikes(kind, year=None):
    """Months where one site's figure is >5x its own median month (and >50k) —
    shown as a warning, never removed from the data."""
    ms, _ = HL.load_monthly()
    m = ms[(ms["Kind"] == kind) & ~ms["Place"].isin(LAHORE) & ms["Total"].notna()].copy()
    med = m.groupby("Place")["Total"].median()
    m["x"] = m["Total"] / m["Place"].map(med).replace(0, np.nan)
    s = m[(m["x"] > 5) & (m["Total"] > 50000)]
    if year is not None:
        s = s[s["Year"] == year]
    return [f"{r.Place}, {str(r.Month)[:3]} {int(r.Year)}: {r.Total:,.0f} (~{r.x:.0f}x its median month)"
            for r in s.itertuples()]


def _year_label(y):
    return f"{y} (Jan–Apr)" if y == YTD_YEAR else str(y)


def _core_sites(df):
    """Sites that report (>= 9 months) in EVERY year 2015-2024, Lahore trio excluded.
    This is the like-for-like basis for trends."""
    yrs = range(FIRST_YEAR, LAST_FULL_YEAR + 1)
    d = df[df["Year"].isin(yrs) & (df["Months"] >= 9)]
    n = d.groupby("Place")["Year"].nunique()
    return [p for p in n[n == len(yrs)].index if p not in LAHORE]


def _yearly(df, core):
    """Per-year totals: as published (sum of all listed sites) vs like-for-like core."""
    full = df[df["Year"] <= LAST_FULL_YEAR]
    allr = full.groupby("Year")[["Foreigner", "National", "Total"]].sum()
    cr = full[full["Place"].isin(core)].groupby("Year")[["Foreigner", "National", "Total"]].sum()
    out = pd.DataFrame({
        "Year": allr.index,
        "All listed sites": allr["Total"].values,
        "Like-for-like core sites": cr["Total"].reindex(allr.index).values,
        "Foreigner": allr["Foreigner"].values,
        "Foreigner (core)": cr["Foreigner"].reindex(allr.index).values,
        "Sites reporting": full.groupby("Year")["Place"].nunique().reindex(allr.index).values,
    })
    return out


def _ranked(df, year, metric, exclude=()):
    d = df[(df["Year"] == year) & (~df["Place"].isin(exclude))].copy()
    d = d[d[metric].notna() & (d[metric] > 0)]
    d["Rank"] = d[metric].rank(method="min", ascending=False).astype(int)
    d["Share %"] = (d[metric] / d[metric].sum() * 100).round(1)
    return d.sort_values("Rank").reset_index(drop=True)


def _short(name, n=34):
    return name if len(name) <= n else name[: n - 1] + "…"


# ------------------------------------------------------------------ sections
def _coverage_banner(kind):
    if kind == "museum":
        st.info(
            "**Coverage:** annual 2015–2024 plus **2025 = Jan–Apr only** (the months PBS has published). "
            "2020–21 *are* published (2020 is low because museums closed Mar–Jul for Covid-19). "
            "**Comparability:** *Lahore Fort* is counted as a museum only in 2022–23 (earlier years list it under "
            "Heritage Sites) and new KP museums were added from 2021, so trends use a **like-for-like basis** — "
            "the same museums in every year, Lahore Fort excluded."
        )
    else:
        st.info(
            "**Coverage:** annual 2015–2024 plus **2025 = Jan–Apr only**. 2020–21 *are* published (Covid-19 closures "
            "Mar–Jul 2020). **Important:** Lahore Fort, Shalamar Garden and Jahangir's Tomb were 70–80% of all "
            "heritage visits until 2022, but PBS reports them for only part of 2023 and **not at all from 2024**. "
            "The headline total therefore falls sharply for a reporting reason, not a visitor reason — so trends use "
            "a **like-for-like basis** (same sites every year, Lahore sites excluded)."
        )


def _trend_section(kind, df, core, yearly):
    c1, c2 = st.columns(2)
    base_row = yearly[yearly["Year"] == 2019].iloc[0]
    with c1:
        section("1. Visitors per year, 2015–2024 (as published vs like-for-like)")
        mode = _mode(f"{kind}_trend_mode", ("Count", "% vs 2019"))
        fig = go.Figure()
        gap = ((yearly["All listed sites"] - yearly["Like-for-like core sites"]) / yearly["All listed sites"]).abs().max()
        for i, col in enumerate(["All listed sites", "Like-for-like core sites"]):
            y = yearly[col].astype(float)
            label_it = (i == 1) or gap > 0.15   # two near-identical lines: label only one
            if mode != "Count":
                y = (y / float(base_row[col]) * 100 - 100).round(1)
            fig.add_scatter(
                x=yearly["Year"].astype(str), y=y, mode="lines+markers+text", name=col,
                line=dict(color=PALETTE[i], dash="solid" if i else "dot"),
                text=[((f"{v:+.1f}%" if mode != "Count" else _k(v)) if label_it else "") for v in y],
                textposition="top center" if i else "bottom center",
                texttemplate="%{text}")
        fig.add_vrect(x0=4.5, x1=6.5, fillcolor="#C1440E", opacity=0.07, line_width=0,
                      annotation_text="Covid-19", annotation_position="top left")
        fig.update_layout(yaxis_title="Visitors" if mode == "Count" else "% change vs 2019",
                          xaxis_title="", margin=dict(t=40), legend=dict(orientation="h", y=-0.15))
        _cat_axis(fig, yearly["Year"].astype(str))
        st.plotly_chart(fig, use_container_width=True)
        st.caption(f"Like-for-like = {len(core)} sites reporting ≥9 months in every year 2015–2024. "
                   "2025 is shown separately (right) because only Jan–Apr exists.")
    with c2:
        section("2. 2025 so far: Jan–Apr compared with Jan–Apr of earlier years")
        ytd = _ytd_like_for_like(kind)
        if ytd is None or ytd.empty:
            st.info("Not enough monthly data for a like-for-like Jan–Apr comparison.")
        else:
            mode2 = _mode(f"{kind}_ytd_mode", ("Count", "% vs 2022"))
            d = ytd.copy()
            if mode2 != "Count":
                d["Value"] = (d["Visitors"] / d["Visitors"].iloc[0] * 100 - 100).round(1)
                d["Label"] = d["Value"].map(lambda v: f"{v:+.1f}%")
                ytitle = "% change vs Jan–Apr 2022"
            else:
                d["Value"] = d["Visitors"]
                d["Label"] = d["Visitors"].map(_fmt)
                ytitle = "Visitors, Jan–Apr"
            fig = px.bar(d, x=d["Year"].astype(str), y="Value", text="Label",
                         color_discrete_sequence=[PALETTE[0]])
            fig.update_traces(textposition="outside", cliponaxis=False)
            fig.update_layout(yaxis_title=ytitle, xaxis_title="", margin=dict(t=40))
            st.plotly_chart(fig, use_container_width=True)
            st.caption(f"Same {int(d['Sites'].iloc[0])} sites, same four months (Jan–Apr) in every year.")
            sp = _spikes(kind, YTD_YEAR)
            if sp:
                st.warning("Unusual figure published by PBS (kept as published — worth confirming with PBS): "
                           + "; ".join(sp))


def _ytd_like_for_like(kind):
    ms, _ = HL.load_monthly()
    m = ms[(ms["Kind"] == kind) & (ms["Month"].isin(HL.MONTHS[:4])) & ~ms["Place"].isin(LAHORE)]
    m = m.assign(_rep=m["Total"].notna().astype(int))
    cnt = m.groupby(["Place", "Year"], observed=True)["_rep"].sum().unstack("Year")
    ok = cnt[(cnt == 4).all(axis=1)].index
    if len(ok) == 0:
        return None
    d = m[m["Place"].isin(ok)].groupby("Year", observed=True)["Total"].sum().reset_index()
    d.columns = ["Year", "Visitors"]
    d["Sites"] = len(ok)
    return d


def _foreign_section(kind, yearly, df):
    c1, c2 = st.columns(2)
    with c1:
        section("3. Foreign visitors per year")
        mode = _mode(f"{kind}_foreign_mode", ("Count", "% of year's visitors"))
        d = yearly[["Year", "Foreigner", "All listed sites"]].copy()
        if mode == "Count":
            d["Value"] = d["Foreigner"]
            d["Label"] = d["Value"].map(_fmt)
            yt = "Foreign visitors"
        else:
            d["Value"] = (d["Foreigner"] / d["All listed sites"] * 100).round(2)
            d["Label"] = d["Value"].map(lambda v: f"{v:.2f}%")
            yt = "Foreign share of all visitors (%)"
        fig = px.bar(d, x=d["Year"].astype(str), y="Value", text="Label", color_discrete_sequence=[PALETTE[1]])
        fig.update_traces(textposition="outside", cliponaxis=False)
        fig.update_layout(yaxis_title=yt, xaxis_title="", margin=dict(t=40))
        _cat_axis(fig, d["Year"].astype(str))
        st.plotly_chart(fig, use_container_width=True)
    with c2:
        section("4. Which province do visitors go to?")
        mode_p = _mode(f"{kind}_prov_mode", ("Count", "% of year's visitors"))
        full = df[df["Year"] <= LAST_FULL_YEAR]
        pv = full.groupby(["Year", "Province"])["Total"].sum().reset_index()
        pv["Year"] = pv["Year"].astype(str)
        yr_tot = pv.groupby("Year")["Total"].transform("sum")
        if mode_p == "Count":
            pv["Value"] = pv["Total"]
            pv["Label"] = pv["Total"].map(_k)
            yt = "Visitors"
        else:
            pv["Value"] = (pv["Total"] / yr_tot * 100).round(1)
            pv["Label"] = pv["Value"].map(lambda v: f"{v:.0f}%")
            yt = "Share of the year's visitors (%)"
        order = [p for p in ["Punjab", "Sindh", "Khyber Pakhtunkhwa", "Balochistan", "Islamabad"] if p in set(pv["Province"])]
        fig = px.bar(pv, x="Year", y="Value", color="Province", text="Label",
                     category_orders={"Province": order}, color_discrete_sequence=PALETTE)
        fig.update_traces(textposition="inside", textfont_size=9)
        fig.update_layout(uniformtext_minsize=8, uniformtext_mode="hide", yaxis_title=yt, xaxis_title="",
                          margin=dict(t=40), legend=dict(orientation="h", y=-0.15, title=""))
        _cat_axis(fig, pv["Year"].unique())
        st.plotly_chart(fig, use_container_width=True)
        st.caption("Small segments are unlabelled to avoid clutter — hover for the exact value.")


def _pct(a, b):
    return f"{(b / a - 1) * 100:+.0f}%" if a else "n/a"


def _key_findings(kind, df, yearly, exclude):
    y = yearly.set_index("Year")
    lf, fc = y["Like-for-like core sites"], y["Foreigner (core)"]
    what = "museums" if kind == "museum" else "heritage sites"
    leaders = {yr: _ranked(df, yr, "Total", exclude).iloc[0]["Place"] for yr in range(FIRST_YEAR, LAST_FULL_YEAR + 1)}
    top_name, top_n = Counter(leaders.values()).most_common(1)[0]
    latest_lead = leaders[LAST_FULL_YEAR]
    fr_lead = _ranked(df, LAST_FULL_YEAR, "Foreigner", exclude).iloc[0]["Place"]
    prov = df[df["Year"] == LAST_FULL_YEAR].groupby("Province")["Total"].sum()
    prov_top, prov_share = prov.idxmax(), prov.max() / prov.sum() * 100
    lines = [
        f"**Growth before Covid:** like-for-like visits to {what} rose {_pct(lf[2015], lf[2019])} between 2015 "
        f"({lf[2015]:,.0f}) and 2019 ({lf[2019]:,.0f}).",
        f"**Covid and recovery:** 2020 was {_pct(lf[2019], lf[2020])} vs 2019; by {LAST_FULL_YEAR} visits were "
        f"{_pct(lf[2019], lf[LAST_FULL_YEAR])} vs 2019 ({lf[LAST_FULL_YEAR]:,.0f}).",
        f"**Most popular:** {top_name} was #1 in {top_n} of the {len(leaders)} years"
        + ("" if latest_lead == top_name else f"; in {LAST_FULL_YEAR} the leader is {latest_lead}") + ".",
        f"**Foreign visitors:** {fc[2019]:,.0f} in 2019 → {fc[LAST_FULL_YEAR]:,.0f} in {LAST_FULL_YEAR} "
        f"({_pct(fc[2019], fc[LAST_FULL_YEAR])}, same sites). Most visited by foreigners in {LAST_FULL_YEAR}: {fr_lead}.",
        f"**Where:** {prov_top} accounts for {prov_share:.0f}% of {LAST_FULL_YEAR} visits.",
    ]
    with st.container(border=True):
        st.markdown("##### Key findings")
        st.markdown("\n".join(f"- {l}" for l in lines))


def _compare_section():
    section("Museums vs heritage sites")
    mus = HL.load_place_year("museum")
    mus = mus[~mus["Place"].isin(LAHORE) & (mus["Year"] <= LAST_FULL_YEAR)]
    her = HL.load_place_year("heritage")
    her = her[her["Year"] <= LAST_FULL_YEAR]
    c1, c2 = st.columns([1, 1])
    with c1:
        what = st.radio("Measure", ["All visits", "Foreign visits"], horizontal=True, key="cmp_measure")
    with c2:
        mode = _mode("cmp_mode", ("Count", "% of combined"))
    col = "Total" if what == "All visits" else "Foreigner"
    a = mus.groupby("Year")[col].sum()
    b = her.groupby("Year")[col].sum()
    d = pd.DataFrame({"Museums": a, "Heritage sites": b}).reset_index()
    d["Year"] = d["Year"].astype(str)
    if mode == "Count":
        long = d.melt("Year", var_name="Type", value_name="Value")
        long["Label"] = long["Value"].map(_k)
        yt = what
    else:
        s = d[["Museums", "Heritage sites"]].sum(axis=1)
        for c in ["Museums", "Heritage sites"]:
            d[c] = (d[c] / s * 100).round(1)
        long = d.melt("Year", var_name="Type", value_name="Value")
        long["Label"] = long["Value"].map(lambda v: f"{v:.0f}%")
        yt = f"Share of combined {what.lower()} (%)"
    fig = px.bar(long, x="Year", y="Value", color="Type", text="Label", barmode="group",
                 color_discrete_sequence=[PALETTE[0], PALETTE[4]])
    fig.update_traces(textposition="outside", cliponaxis=False, textfont_size=9)
    fig.update_layout(yaxis_title=yt, xaxis_title="", margin=dict(t=30), legend=dict(orientation="h", y=-0.15, title=""))
    _cat_axis(fig, long["Year"].unique())
    st.plotly_chart(fig, use_container_width=True)
    st.caption("Museums exclude Lahore Fort (PBS lists it under both only in 2022–23). Heritage sites are as published: "
               "Lahore Fort / Shalamar / Jahangir's Tomb are included to 2023 and missing from 2024, which lowers the "
               "heritage line in 2023–24.")


def _province_section(kind, df):
    section("Province view")
    full = df[df["Year"] <= LAST_FULL_YEAR]
    provs = sorted(full["Province"].dropna().unique().tolist())
    c1, c2 = st.columns([1, 1])
    with c1:
        prov = st.selectbox("Province", provs, index=provs.index("Punjab") if "Punjab" in provs else 0,
                            key=f"{kind}_prov_pick")
    with c2:
        mode = _mode(f"{kind}_prov_view_mode", ("Count", "% of national visits"))
    tot = full.groupby("Year")["Total"].sum()
    pv = full[full["Province"] == prov].groupby("Year")["Total"].sum().reindex(tot.index).fillna(0)
    d = pd.DataFrame({"Year": tot.index.astype(str), "Value": pv.values})
    if mode == "Count":
        d["Label"] = d["Value"].map(_k)
        yt = f"Visitors — {prov}"
    else:
        d["Value"] = (pv.values / tot.values * 100).round(1)
        d["Label"] = d["Value"].map(lambda v: f"{v:.1f}%")
        yt = f"{prov}'s share of national visits (%)"
    fig = px.bar(d, x="Year", y="Value", text="Label", color_discrete_sequence=[PALETTE[2]])
    fig.update_traces(textposition="outside", cliponaxis=False)
    fig.update_layout(yaxis_title=yt, xaxis_title="", margin=dict(t=30))
    _cat_axis(fig, d["Year"])
    st.plotly_chart(fig, use_container_width=True)
    top = full[(full["Province"] == prov) & (full["Year"] == LAST_FULL_YEAR)].sort_values("Total", ascending=False).head(3)
    if len(top):
        st.caption(f"Top sites in {prov}, {LAST_FULL_YEAR}: " + "; ".join(f"{p} ({v:,.0f})" for p, v in zip(top["Place"], top["Total"])))


def _top10_section(kind, df, exclude):
    section("5. Top 10 — pick any year")
    years = sorted(df["Year"].unique().tolist())
    c1, c2 = st.columns([2, 1])
    with c2:
        metric_name = st.radio("Rank by", ["All visitors", "Foreign visitors", "National visitors"],
                               key=f"{kind}_rank_metric")
    metric = {"All visitors": "Total", "Foreign visitors": "Foreigner", "National visitors": "National"}[metric_name]
    with c1:
        year = st.select_slider("Year", options=years, value=LAST_FULL_YEAR,
                                format_func=_year_label, key=f"{kind}_top_year")
    r = _ranked(df, year, metric, exclude)
    top = r.head(10).copy()
    if year == YTD_YEAR:
        st.warning("2025 covers January–April only; ranks are valid for that period but are not full-year figures.")
    mode = _mode(f"{kind}_top_mode", ("Count", f"% of {year} total"))
    if mode == "Count":
        top["Value"] = top[metric]
        top["Label"] = top["Value"].map(_fmt)
        xt = f"{metric_name} ({_year_label(year)})"
    else:
        top["Value"] = top["Share %"]
        top["Label"] = top["Value"].map(lambda v: f"{v:.1f}%")
        xt = f"Share of all {metric_name.lower()} in {_year_label(year)} (%)"
    top["Site"] = top["Place"].map(_short)
    fig = px.bar(top.iloc[::-1], x="Value", y="Site", orientation="h", text="Label",
                 color_discrete_sequence=[PALETTE[0]])
    fig.update_traces(textposition="outside", cliponaxis=False)
    fig.update_layout(xaxis_title=xt, yaxis_title="", margin=dict(r=90, t=30), height=440)
    st.plotly_chart(fig, use_container_width=True)
    part = top[top["Months"] < 12] if year < YTD_YEAR else pd.DataFrame()
    if len(part):
        st.caption("⚠ Fewer than 12 months reported: " + "; ".join(
            f"{p} ({int(mo)} months)" for p, mo in zip(part["Place"], part["Months"])))
    return metric


def _rank_history(kind, df, exclude, metric):
    years = sorted(df["Year"].unique().tolist())
    ranks = {y: _ranked(df, y, metric, exclude).set_index("Place") for y in years}

    section("6. Top 10 of every year, side by side")
    grid = {}
    for y in years:
        t = ranks[y].head(10)
        col = []
        for p, row in t.iterrows():
            col.append(_short(p, 30) + (" *" if row["Months"] < 12 and y < YTD_YEAR else ""))
        grid[_year_label(y)] = col + [""] * (10 - len(col))
    gdf = pd.DataFrame(grid, index=range(1, 11))
    gdf.index.name = "Rank"
    st.dataframe(gdf, use_container_width=True)
    st.caption("* = fewer than 12 months reported that year. 2025 = Jan–Apr only.")

    ever = []
    for y in years:
        for p in ranks[y].head(10).index:
            if p not in ever:
                ever.append(p)

    section("7. How the rankings moved (rank in each year)")
    fig = go.Figure()
    xs = [_year_label(y) for y in years]
    for i, p in enumerate(ever):
        rr = [int(ranks[y].loc[p, "Rank"]) if p in ranks[y].index and ranks[y].loc[p, "Rank"] <= 12 else None
              for y in years]
        if not any(v is not None for v in rr):
            continue
        last = max(j for j, v in enumerate(rr) if v is not None)
        fig.add_scatter(x=xs, y=rr, mode="lines+markers+text", name=_short(p, 30),
                        text=[str(v) if v is not None else "" for v in rr],
                        textposition="middle center", textfont=dict(color="white", size=10),
                        marker=dict(size=20, color=PALETTE[i % len(PALETTE)]),
                        line=dict(color=PALETTE[i % len(PALETTE)], width=2), connectgaps=False)
    fig.update_yaxes(range=[12.5, 0.5], tickmode="array", tickvals=list(range(1, 13)), title="Rank (1 = most visited)")
    _cat_axis(fig, xs)
    fig.update_layout(height=560, margin=dict(t=30), legend=dict(font=dict(size=10)), xaxis_title="")
    st.plotly_chart(fig, use_container_width=True)
    st.caption("A line stops where the site is outside the top 12 or has no published figure that year.")

    section("8. Biggest risers and fallers between two years")
    c1, c2, c3 = st.columns([1, 1, 1])
    full_years = [y for y in years if y < YTD_YEAR]
    with c1:
        y0 = st.selectbox("From", full_years, index=full_years.index(2019), key=f"{kind}_mv_from")
    with c2:
        y1 = st.selectbox("To", full_years, index=len(full_years) - 1, key=f"{kind}_mv_to")
    with c3:
        mode = _mode(f"{kind}_mv_mode", ("Count", "% change in visitors"))
    a, b = ranks[y0], ranks[y1]
    both = a.index.intersection(b.index)
    if len(both) == 0 or y0 == y1:
        st.info("Pick two different years that share at least one site.")
        return
    mv = pd.DataFrame({
        "Site": [_short(p) for p in both],
        "Rank change": (a.loc[both, "Rank"] - b.loc[both, "Rank"]).astype(int).values,
        "Visitors % change": ((b.loc[both, metric] / a.loc[both, metric] - 1) * 100).round(1).values,
    })
    if mode == "Count":
        mv["Value"] = mv["Rank change"]
        mv["Label"] = mv["Value"].map(lambda v: f"{v:+d}" if v else "0")
        xt = f"Rank positions gained (+) or lost (−), {y0} → {y1}"
    else:
        mv["Value"] = mv["Visitors % change"]
        mv["Label"] = mv["Value"].map(lambda v: f"{v:+.1f}%")
        xt = f"% change in visitors, {y0} → {y1}"
    mv = mv.sort_values("Value")
    fig = px.bar(mv, x="Value", y="Site", orientation="h", text="Label",
                 color=(mv["Value"] >= 0).map({True: "Up", False: "Down"}),
                 color_discrete_map={"Up": PALETTE[2], "Down": PALETTE[1]})
    fig.update_traces(textposition="outside", cliponaxis=False)
    fig.update_layout(xaxis_title=xt, yaxis_title="", showlegend=False, margin=dict(r=80, t=30),
                      height=max(360, 26 * len(mv) + 120))
    st.plotly_chart(fig, use_container_width=True)
    if kind == "heritage" and (y1 >= 2024 or y0 >= 2024):
        st.caption("Lahore Fort, Shalamar and Jahangir's Tomb have no 2024 figures, so they are absent from 2024 comparisons.")


def _data_notes(kind):
    with st.expander("Data notes — how these numbers were built"):
        st.markdown(
            "- **Years 2015–2021:** PBS annual tables. **2022–2024:** the 12 monthly sheets added up "
            "(they match the annual table for all sites except three place/year pairs where the annual "
            "table mixes up neighbouring rows: Taxila / Lahore Fort 2022 and 2024, Taxila / Wah Garden 2024). "
            "**2025:** Jan–Apr only.\n"
            "- **Place names** are spelled differently across PBS files (e.g. *Khawara / Khewra*, "
            "*Birth House / House Museum*); each place is mapped to one name before ranking.\n"
            "- **Totals** are the sum of listed sites. (PBS's own printed ‘Pakistan’ row for Heritage Sites "
            "2015–18 is shifted by a year and does not agree with the provincial rows.)\n"
            "- Blank / ‘…’ / ‘Nil’ = not reported and is **never treated as a visit count**; "
            "‘–’ next to a real number = 0.\n"
            "- Museum and heritage tables are **not additive**: Lahore Fort appears in both in 2022–23."
        )


def _table_section(kind, df):
    section("9. Full data table")
    show = df.copy()
    show["Year"] = show["Year"].astype(int)
    show = show[["Year", "Province", "Place", "Foreigner", "National", "Total", "Months", "Basis"]]
    st.dataframe(show.sort_values(["Year", "Total"], ascending=[False, False]),
                 use_container_width=True, hide_index=True)


# ------------------------------------------------------------------ tabs
def _render_kind(kind):
    df = HL.load_place_year(kind)
    _coverage_banner(kind)

    exclude = ()
    if kind == "museum":
        inc = st.checkbox("Include Lahore Fort in museum rankings (PBS lists it as a museum only in 2022–23)",
                          value=False, key="museum_incl_lahore")
        exclude = () if inc else tuple(LAHORE)
        df_trend = df[~df["Place"].isin(LAHORE)]
    else:
        df_trend = df
    core = _core_sites(df)
    yearly = _yearly(df_trend, core)

    last = yearly[yearly["Year"] == LAST_FULL_YEAR].iloc[0]
    y19 = yearly[yearly["Year"] == 2019].iloc[0]
    peak = yearly.loc[yearly["Like-for-like core sites"].idxmax()]
    top_now = _ranked(df, LAST_FULL_YEAR, "Total", exclude).iloc[0]
    kpi_row([
        (f"Visitors {LAST_FULL_YEAR} (listed sites)", _fmt(last["All listed sites"]), None),
        (f"Like-for-like vs 2019", f"{(last['Like-for-like core sites']/y19['Like-for-like core sites']-1)*100:+.1f}%",
         "same sites, pre-Covid base"),
        ("Like-for-like peak year", str(int(peak["Year"])), _fmt(peak["Like-for-like core sites"])),
        (f"Foreign share {LAST_FULL_YEAR}", f"{last['Foreigner']/last['All listed sites']*100:.2f}%", None),
        (f"#1 in {LAST_FULL_YEAR}", _short(top_now["Place"], 22), f"{top_now['Share %']:.1f}% of visits"),
    ])
    _key_findings(kind, df, yearly, exclude)
    st.divider()

    _trend_section(kind, df_trend, core, yearly)
    st.divider()
    _foreign_section(kind, yearly, df_trend)
    st.divider()
    _compare_section()
    st.divider()
    _province_section(kind, df_trend)
    st.divider()
    metric = _top10_section(kind, df, exclude)
    st.divider()
    _rank_history(kind, df, exclude, metric)
    st.divider()
    _data_notes(kind)
    _table_section(kind, df)


def render_museums():
    _sec["n"] = 0
    _render_kind("museum")


def render_heritage():
    _sec["n"] = 0
    _render_kind("heritage")


# ------------------------------------------------------------------ monthly
def render_monthly():
    _sec["n"] = 0
    st.info("**Monthly sheets cover Jan 2022 – Apr 2025.** 2025 stops at April. Lahore Fort, Shalamar Garden and "
            "Jahangir's Tomb are excluded here because PBS reports them only for part of 2022–23 and not afterwards, "
            "which would otherwise distort the monthly pattern. Annual 2015–2024 history is on the other two tabs.")
    ms, _ = HL.load_monthly()
    kind_name = st.radio("Show", ["Museums", "Heritage sites"], horizontal=True, key="mon_kind")
    kind = "museum" if kind_name == "Museums" else "heritage"
    m = ms[(ms["Kind"] == kind) & ~ms["Place"].isin(LAHORE)].copy()
    m["Month"] = pd.Categorical(m["Month"].astype(str), categories=HL.MONTHS, ordered=True)

    tot = m.groupby(["Year", "Month"], observed=True)[["Foreigner", "National", "Total"]].sum(min_count=1).reset_index()
    tot = tot[tot["Total"].notna()]
    tot["Period"] = tot["Month"].astype(str).str[:3] + " " + tot["Year"].astype(str)

    peak = tot.loc[tot["Total"].idxmax()]
    kpi_row([
        ("Months covered", str(len(tot)), "Jan 2022 – Apr 2025"),
        ("Busiest month", peak["Period"], _fmt(peak["Total"])),
        ("Average month", _fmt(tot["Total"].mean()), None),
        ("Foreign share (all months)", f"{tot['Foreigner'].sum()/tot['Total'].sum()*100:.2f}%", None),
        ("Sites tracked", str(m["Place"].nunique()), None),
    ])
    st.divider()

    c1, c2 = st.columns(2)
    with c1:
        section("1. Year-on-year by month")
        mode = _mode("mon_yoy_mode", ("Count", "% of the year's visitors"))
        piv = tot.pivot(index="Month", columns="Year", values="Total").reindex(HL.MONTHS)
        fig = go.Figure()
        for i, y in enumerate(piv.columns):
            ser = piv[y]
            if mode != "Count":
                ser = ser / ser.sum() * 100
            fig.add_scatter(x=[mo[:3] for mo in piv.index], y=ser, mode="lines+markers", name=str(y),
                            line=dict(color=PALETTE[i % len(PALETTE)]), connectgaps=False)
        fig.update_layout(yaxis_title="Visitors" if mode == "Count" else "% of that year's Jan–Apr/Dec total",
                          xaxis_title="", margin=dict(t=40), legend=dict(orientation="h", y=-0.15))
        st.plotly_chart(fig, use_container_width=True)
        if mode != "Count":
            st.caption("2025 has only four months, so its percentages are shares of Jan–Apr and not comparable "
                       "with full years.")
    with c2:
        section("2. Month-by-month heatmap (visitors)")
        piv2 = piv.copy()
        piv2.index = [mo[:3] for mo in piv2.index]
        fig = px.imshow(piv2.T, aspect="auto", color_continuous_scale="OrRd", text_auto=",.0f",
                        labels=dict(color="Visitors", x="", y=""))
        fig.update_traces(textfont_size=9)
        fig.update_yaxes(type="category")
        fig.update_layout(margin=dict(t=30))
        st.plotly_chart(fig, use_container_width=True)

    c1, c2 = st.columns(2)
    with c1:
        section("3. One year in detail")
        years = sorted(tot["Year"].unique().tolist())
        y = st.selectbox("Year", years, index=len(years) - 2, key="mon_year")
        d = tot[tot["Year"] == y].copy()
        mode3 = _mode("mon_year_mode", ("Count", "% of the year's total"))
        if mode3 == "Count":
            d["Value"] = d["Total"]
            d["Label"] = d["Value"].map(_fmt)
            yt = "Visitors"
        else:
            d["Value"] = (d["Total"] / d["Total"].sum() * 100).round(1)
            d["Label"] = d["Value"].map(lambda v: f"{v:.1f}%")
            yt = "Share of the year's visitors (%)"
        fig = px.bar(d, x=d["Month"].astype(str).str[:3], y="Value", text="Label",
                     color_discrete_sequence=[PALETTE[0]])
        fig.update_traces(textposition="outside", cliponaxis=False)
        fig.update_layout(yaxis_title=yt, xaxis_title="", margin=dict(t=40))
        st.plotly_chart(fig, use_container_width=True)
        if y == YTD_YEAR:
            st.caption("2025 = Jan–Apr only.")
    with c2:
        section("4. Foreign share by month")
        t2 = tot.copy()
        t2["Foreign %"] = (t2["Foreigner"] / t2["Total"] * 100).round(2)
        t2 = t2[t2["Year"] == y]
        fig = px.line(t2, x=t2["Month"].astype(str).str[:3], y="Foreign %", markers=True,
                      color_discrete_sequence=[PALETTE[1]])
        fig.update_traces(texttemplate="%{y:.2f}%", textposition="top center", mode="lines+markers+text")
        fig.update_layout(yaxis_title="Foreign visitors, % of month's total", xaxis_title="", margin=dict(t=40))
        st.plotly_chart(fig, use_container_width=True)

    section(f"5. Top 10 in {y} — by month or whole year")
    opts = ["Whole year"] + [mo for mo in HL.MONTHS if mo in m[m["Year"] == y]["Month"].astype(str).unique()]
    pick = st.selectbox("Period", opts, key="mon_period")
    base = m[m["Year"] == y]
    if pick != "Whole year":
        base = base[base["Month"].astype(str) == pick]
    t = base.groupby("Place")["Total"].sum(min_count=1).dropna().sort_values(ascending=False)
    t = t[t > 0].head(10)
    mode5 = _mode("mon_top_mode", ("Count", "% of period total"))
    full = base["Total"].sum()
    d5 = pd.DataFrame({"Site": [_short(p) for p in t.index], "Visitors": t.values})
    if mode5 == "Count":
        d5["Value"], d5["Label"], xt = d5["Visitors"], d5["Visitors"].map(_fmt), "Visitors"
    else:
        d5["Value"] = (d5["Visitors"] / full * 100).round(1)
        d5["Label"] = d5["Value"].map(lambda v: f"{v:.1f}%")
        xt = "Share of all visitors in the period (%)"
    fig = px.bar(d5.iloc[::-1], x="Value", y="Site", orientation="h", text="Label",
                 color_discrete_sequence=[PALETTE[0]])
    fig.update_traces(textposition="outside", cliponaxis=False)
    fig.update_layout(xaxis_title=xt, yaxis_title="", margin=dict(r=90, t=30), height=440)
    st.plotly_chart(fig, use_container_width=True)

    sp = _spikes(kind)
    if sp:
        st.warning("Unusual figures published by PBS (kept as published — worth confirming with PBS): " + "; ".join(sp))

    section("6. Full monthly data")
    st.dataframe(m.drop(columns=["Kind"]).sort_values(["Year", "Month", "Total"], ascending=[False, False, False]),
                 use_container_width=True, hide_index=True)
