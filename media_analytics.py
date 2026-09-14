import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import loaders as L
import chart_helpers as CH

PALETTE = ["#2C5F8A", "#C1440E", "#4C8C4A", "#8A5FC1", "#C19A2C",
           "#3A9BA0", "#B03A5B", "#6B6B6B", "#5B7C99", "#9C6B30"]

bar = CH.bar
line = CH.line


def kpi_row(items):
    cols = st.columns(len(items))
    for c, (label, value, delta) in zip(cols, items):
        c.metric(label, value, delta)


def section(title):
    st.markdown(f"#### {title}")


def pie(names, values, title="", hole=0.45):
    fig = px.pie(names=names, values=values, title=title, hole=hole, color_discrete_sequence=PALETTE)
    fig.update_traces(textinfo="label+percent", textposition="inside")
    st.plotly_chart(fig, use_container_width=True)


# ============================================================
# 1. Documentary films
# ============================================================

def render_documentary_films():
    df = L.load_documentary_films()
    df["Release Rate %"] = (df["Federal Released"] / df["Federal Produced"] * 100).round(1)
    latest, first = df.iloc[-1], df.iloc[0]

    kpi_row([
        (f"Films produced ({latest['Year']})", f"{int(latest['Federal Produced'])}", None),
        (f"Films released ({latest['Year']})", f"{int(latest['Federal Released'])}", None),
        ("Release rate", f"{latest['Release Rate %']:.0f}%", None),
        ("Growth since first year", f"{(latest['Federal Produced']-first['Federal Produced'])/first['Federal Produced']*100:+.1f}%", f"since {first['Year']}"),
        ("Total produced (all years)", f"{int(df['Federal Produced'].sum())}", None),
    ])
    st.info("Note: only Federal-level data has ever been recorded in this file — Punjab, Sindh and KP columns "
            "are blank ('--') for every year, so this tab focuses on the Federal series.")
    st.divider()

    c1, c2 = st.columns(2)
    with c1:
        section("1. Films produced over time (with trend line)")
        line(df, "Year", "Federal Produced", "Documentary films produced — Federal")
    with c2:
        section("2. Produced vs Released")
        bar(df, "Year", ["Federal Produced", "Federal Released"], "Produced vs Released", barmode="group")

    c1, c2 = st.columns(2)
    with c1:
        section("3. Release rate over time (%)")
        line(df, "Year", "Release Rate %", "Release rate (Released / Produced)")
    with c2:
        section("4. Year-over-year % change in production")
        yoy = df.copy()
        yoy["YoY %"] = df["Federal Produced"].pct_change() * 100
        bar(yoy, "Year", "YoY %", "YoY change in films produced", color="YoY %", color_continuous_scale="RdYlGn")

    c1, c2 = st.columns(2)
    with c1:
        section("5. Cumulative films produced")
        d = df.copy()
        d["Cumulative"] = d["Federal Produced"].cumsum()
        line(d, "Year", "Cumulative", "Cumulative films produced", trend=False)
    with c2:
        section("6. Films not released (produced − released)")
        df["Unreleased"] = df["Federal Produced"] - df["Federal Released"]
        bar(df, "Year", "Unreleased", "Films produced but not released")

    c1, c2 = st.columns(2)
    with c1:
        section("7. Highest vs lowest production year")
        peak = df.loc[df["Federal Produced"].idxmax()]
        low = df.loc[df["Federal Produced"].idxmin()]
        bar(x=[f"Peak ({peak['Year']})", f"Lowest ({low['Year']})"],
            y=[peak["Federal Produced"], low["Federal Produced"]], title="Peak vs lowest year")
    with c2:
        section("8. 3-year moving average")
        d = df.copy()
        d["3yr MA"] = d["Federal Produced"].rolling(3).mean()
        line(d, "Year", "3yr MA", "3-year moving average", trend=False)

    c1, c2 = st.columns(2)
    with c1:
        section("9. Share of total production by year")
        pie(df["Year"], df["Federal Produced"], "Share of total (all years) by year")
    with c2:
        section("10. Full data table")
        st.dataframe(df, use_container_width=True, hide_index=True)


# ============================================================
# 2. Dramas & plays
# ============================================================

def render_dramas_plays():
    df = L.load_dramas_plays()
    df["Telecast Rate %"] = (df["TV Telecasted"] / df["TV Produced"] * 100).round(1)
    radio_active = df[df["Radio Produced"] > 0]
    latest, first = df.iloc[-1], df.iloc[0]

    kpi_row([
        (f"TV dramas produced ({int(latest['Year'])})", f"{int(latest['TV Produced'])}", None),
        (f"TV telecasted ({int(latest['Year'])})", f"{int(latest['TV Telecasted'])}", None),
        ("Telecast rate", f"{latest['Telecast Rate %']:.0f}%", None),
        ("Peak year (TV produced)", str(int(df.loc[df['TV Produced'].idxmax(), 'Year'])), f"{int(df['TV Produced'].max())}"),
        ("Radio active years", f"{len(radio_active)} / {len(df)}", "stopped after 2012"),
    ])
    st.divider()

    c1, c2 = st.columns(2)
    with c1:
        section("1. TV dramas: produced vs telecasted (with trend lines)")
        line(df, "Year", ["TV Produced", "TV Telecasted"], "TV dramas over time")
    with c2:
        section("2. Radio: produced vs broadcasted (2008-2012 only)")
        line(radio_active, "Year", ["Radio Produced", "Radio Broadcasted"], "Radio dramas (active years)")

    c1, c2 = st.columns(2)
    with c1:
        section("3. Telecast rate over time (%)")
        line(df, "Year", "Telecast Rate %", "TV telecast rate")
    with c2:
        section("4. Year-over-year % change (TV produced)")
        yoy = df.copy()
        yoy["YoY %"] = df["TV Produced"].pct_change() * 100
        bar(yoy, "Year", "YoY %", "YoY change in TV dramas produced", color="YoY %", color_continuous_scale="RdYlGn")

    c1, c2 = st.columns(2)
    with c1:
        section("5. Total media output (TV + Radio)")
        df["Total Output"] = df["TV Produced"] + df["Radio Produced"]
        line(df, "Year", "Total Output", "Combined TV + Radio dramas produced")
    with c2:
        section("6. Backlog (produced − telecasted)")
        df["Backlog"] = df["TV Produced"] - df["TV Telecasted"]
        bar(df, "Year", "Backlog", "Produced but not yet telecasted")

    c1, c2 = st.columns(2)
    with c1:
        section("7. Pre vs post-2013 average (TV produced)")
        pre = df[df["Year"] < 2013]["TV Produced"].mean()
        post = df[df["Year"] >= 2013]["TV Produced"].mean()
        bar(x=["2008-2012 avg", "2013-2024 avg"], y=[pre, post], title="Average TV dramas produced per year")
    with c2:
        section("8. Share of total TV dramas by year")
        pie(df["Year"], df["TV Produced"], "Share of total (all years) by year")

    c1, c2 = st.columns(2)
    with c1:
        section("9. 3-year moving average (TV produced)")
        d = df.copy()
        d["3yr MA"] = d["TV Produced"].rolling(3).mean()
        line(d, "Year", "3yr MA", "3-year moving average", trend=False)
    with c2:
        section("10. Full data table")
        st.dataframe(df, use_container_width=True, hide_index=True)


# ============================================================
# 3. TV sets by province
# ============================================================

def render_tv_sets():
    df = L.load_tv_sets()
    provinces = ["Punjab", "Sindh", "KP", "Balochistan"]
    latest, first = df.iloc[-1], df.iloc[0]

    kpi_row([
        (f"Total TV sets ({int(latest['Year'])})", f"{int(latest['Total']):,}", None),
        ("Largest province", max(provinces, key=lambda p: latest[p]), f"{int(latest[max(provinces, key=lambda p: latest[p])]):,}"),
        ("Growth since first year", f"{(latest['Total']-first['Total'])/first['Total']*100:+.1f}%", f"since {int(first['Year'])}"),
        ("YoY change (latest)", f"{(latest['Total']-df.iloc[-2]['Total'])/df.iloc[-2]['Total']*100:+.1f}%", None),
        ("Years tracked", str(len(df)), None),
    ])
    st.divider()

    c1, c2 = st.columns(2)
    with c1:
        section("1. TV sets by province over time")
        melt = df.melt(id_vars="Year", value_vars=provinces, var_name="Province", value_name="TV Sets")
        fig = px.line(melt, x="Year", y="TV Sets", color="Province", markers=True, color_discrete_sequence=PALETTE)
        st.plotly_chart(fig, use_container_width=True)
    with c2:
        section(f"2. Province share — {int(latest['Year'])}")
        pie(provinces, [latest[p] for p in provinces], f"Share by province — {int(latest['Year'])}")

    c1, c2 = st.columns(2)
    with c1:
        section("3. Total TV sets trend (with trend line)")
        line(df, "Year", "Total", "Total registered TV sets")
    with c2:
        section(f"4. Province ranking — {int(latest['Year'])}")
        rank = pd.DataFrame({"Province": provinces, "TV Sets": [latest[p] for p in provinces]})
        bar(rank.sort_values("TV Sets", ascending=False), "Province", "TV Sets", "Ranking by TV sets")

    c1, c2 = st.columns(2)
    with c1:
        section(f"5. Growth % by province ({int(first['Year'])} → {int(latest['Year'])})")
        growth = pd.DataFrame({"Province": provinces,
                                "Growth %": [(latest[p] - first[p]) / first[p] * 100 for p in provinces]})
        bar(growth.sort_values("Growth %"), "Province", "Growth %", "Growth since first year",
            color="Growth %", color_continuous_scale="RdYlGn")
    with c2:
        section("6. Year-over-year % change (national total)")
        yoy = df.copy()
        yoy["YoY %"] = df["Total"].pct_change() * 100
        bar(yoy, "Year", "YoY %", "YoY change in total TV sets", color="YoY %", color_continuous_scale="RdYlGn")

    section("7. Composition over time — % share by province (stacked area)")
    pct_df = df[provinces].div(df["Total"], axis=0) * 100
    pct_df["Year"] = df["Year"]
    melt = pct_df.melt(id_vars="Year", value_vars=provinces, var_name="Province", value_name="Share %")
    fig = px.area(melt, x="Year", y="Share %", color="Province", color_discrete_sequence=PALETTE)
    fig.update_layout(yaxis=dict(ticksuffix="%"))
    st.plotly_chart(fig, use_container_width=True)

    c1, c2 = st.columns(2)
    with c1:
        section("8. Heatmap — province × year")
        pivot = df.set_index("Year")[provinces].T
        fig = px.imshow(pivot, aspect="auto", color_continuous_scale="OrRd", labels=dict(color="TV Sets"))
        st.plotly_chart(fig, use_container_width=True)
    with c2:
        section("9. Average annual share by province")
        avg_share = (df[provinces].sum() / df[provinces].sum().sum() * 100).sort_values(ascending=False)
        bar(x=avg_share.index, y=avg_share.values, title="% of all TV sets (avg across years)")

    section("10. Full data table")
    st.dataframe(df, use_container_width=True, hide_index=True)


# ============================================================
# 4. Telecom subscribers — monthly
# ============================================================

def render_telecom_monthly():
    year = st.selectbox("Year", [2022, 2023, 2024, 2025], key="tc_year")
    df = L.load_telecom_monthly(year)
    operators = ["PMCL (Jazz)", "CM Pak", "PTML Ufone", "Telenor", "SCO"]
    latest, first = df.iloc[-1], df.iloc[0]
    op_totals = df[operators].sum()

    kpi_row([
        (f"Total subscribers ({df.iloc[-1]['Month']})", f"{int(latest['Total']):,}", None),
        ("Market leader", op_totals.idxmax(), f"{op_totals.max()/op_totals.sum()*100:.1f}% share"),
        ("YoY-equivalent growth (Jan→Dec)", f"{(latest['Total']-first['Total'])/first['Total']*100:+.2f}%", None),
        ("Operators tracked", str(len(operators)), None),
        ("Year", str(year), None),
    ])
    st.divider()

    c1, c2 = st.columns(2)
    with c1:
        section("1. Total subscribers by month (with trend line)")
        line(df, "Month", "Total", f"Total mobile subscribers — {year}")
    with c2:
        section("2. Market share by operator (annual total)")
        pie(op_totals.index, op_totals.values, f"Operator market share — {year}")

    c1, c2 = st.columns(2)
    with c1:
        section("3. Subscribers by operator over time")
        melt = df.melt(id_vars="Month", value_vars=operators, var_name="Operator", value_name="Subscribers")
        fig = px.line(melt, x="Month", y="Subscribers", color="Operator", markers=True, color_discrete_sequence=PALETTE)
        st.plotly_chart(fig, use_container_width=True)
    with c2:
        section(f"4. Operator ranking — {df.iloc[-1]['Month']}")
        rank = pd.DataFrame({"Operator": operators, "Subscribers": [latest[o] for o in operators]})
        bar(rank.sort_values("Subscribers", ascending=False), "Operator", "Subscribers", "Latest month ranking")

    c1, c2 = st.columns(2)
    with c1:
        section("5. Month-over-month % change (total)")
        mom = df.copy()
        mom["MoM %"] = df["Total"].pct_change() * 100
        bar(mom, "Month", "MoM %", "Month-over-month change", color="MoM %", color_continuous_scale="RdYlGn")
    with c2:
        section("6. Composition over time — % share by operator (stacked area)")
        pct_df = df[operators].div(df["Total"], axis=0) * 100
        pct_df["Month"] = df["Month"]
        melt = pct_df.melt(id_vars="Month", value_vars=operators, var_name="Operator", value_name="Share %")
        fig = px.area(melt, x="Month", y="Share %", color="Operator", color_discrete_sequence=PALETTE)
        fig.update_layout(yaxis=dict(ticksuffix="%"))
        st.plotly_chart(fig, use_container_width=True)

    c1, c2 = st.columns(2)
    with c1:
        section("7. Growth since January (%) by operator")
        growth = pd.DataFrame({"Operator": operators,
                                "Growth %": [(latest[o] - first[o]) / first[o] * 100 for o in operators]})
        bar(growth.sort_values("Growth %"), "Operator", "Growth %", "Growth Jan → latest month",
            color="Growth %", color_continuous_scale="RdYlGn")
    with c2:
        section("8. Heatmap — operator × month")
        pivot = df.set_index("Month")[operators].T
        fig = px.imshow(pivot, aspect="auto", color_continuous_scale="OrRd", labels=dict(color="Subscribers"))
        st.plotly_chart(fig, use_container_width=True)

    c1, c2 = st.columns(2)
    with c1:
        section("9. Smallest operator trend")
        smallest = op_totals.idxmin()
        line(df, "Month", smallest, f"{smallest} — subscribers by month")
    with c2:
        section("10. Full data table")
        st.dataframe(df, use_container_width=True, hide_index=True)
