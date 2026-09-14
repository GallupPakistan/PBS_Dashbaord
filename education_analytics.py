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


def _get_series(df, level, metric, stat="Total"):
    sub = df[(df["Level"] == level) & (df["Metric"] == metric) & (df["Stat"] == stat)]
    return sub.sort_values("Year")[["Year", "Value"]].reset_index(drop=True)


SCHOOL_LEVELS = ["Primary Schools", "Middle Schools", "High Schools", "Secondary  Schools"]
COLLEGE_LEVELS = ["Atrs & Science Colleges", "Professional Colleges", "Secondary Vocational Institutions"]
UNIVERSITY_LEVELS = ["Universities (Public)", "Universities (Private)", "Universities (Public+Private)"]


def render_education(group_levels=None, widget_prefix="edu"):
    df = L.load_education()
    all_levels = df["Level"].unique().tolist()
    levels = [l for l in (group_levels or all_levels) if l in all_levels]
    level = st.selectbox("Education level", levels, key=f"{widget_prefix}_level")

    metrics_here = df[df["Level"] == level]["Metric"].unique().tolist()
    enrol_metric = next((m for m in metrics_here if m.startswith("Enrolment")), None)
    teach_metric = next((m for m in metrics_here if m.startswith("Teachers") and "per" not in m.lower()), None)
    num_metric = next((m for m in metrics_here if m.startswith("Number")), None)
    ratio_metric = next((m for m in metrics_here if "Ratio" in m), None)
    female_pct_metric = next((m for m in metrics_here if "Percentage of Female" in m), None)

    enrol = _get_series(df, level, enrol_metric) if enrol_metric else pd.DataFrame()
    teach = _get_series(df, level, teach_metric) if teach_metric else pd.DataFrame()
    num = _get_series(df, level, num_metric) if num_metric else pd.DataFrame()
    ratio = _get_series(df, level, ratio_metric, stat="Value") if ratio_metric else pd.DataFrame()
    female_pct = _get_series(df, level, female_pct_metric, stat="Value") if female_pct_metric else pd.DataFrame()

    latest_enrol = enrol.iloc[-1] if len(enrol) else None
    first_enrol = enrol.iloc[0] if len(enrol) else None
    latest_teach = teach.iloc[-1] if len(teach) else None
    latest_ratio = ratio.iloc[-1] if len(ratio) else None
    latest_num = num.iloc[-1] if len(num) else None
    latest_fpct = female_pct.iloc[-1] if len(female_pct) else None

    kpi_row([
        (f"Enrolment ({latest_enrol['Year']})" if latest_enrol is not None else "Enrolment",
         f"{latest_enrol['Value']:,.0f}k" if latest_enrol is not None else "N/A", None),
        (f"Teachers ({latest_teach['Year']})" if latest_teach is not None else "Teachers",
         f"{latest_teach['Value']:,.0f}k" if latest_teach is not None else "N/A", None),
        ("Student:Teacher ratio", f"{latest_ratio['Value']:.1f}" if latest_ratio is not None else "N/A", None),
        ("Female teachers", f"{latest_fpct['Value']:.1f}%" if latest_fpct is not None else "N/A", None),
        ("Enrolment growth", f"{(latest_enrol['Value']-first_enrol['Value'])/first_enrol['Value']*100:+.1f}%" if latest_enrol is not None else "N/A",
         f"since {first_enrol['Year']}" if first_enrol is not None else None),
    ])
    st.divider()

    c1, c2 = st.columns(2)
    with c1:
        section("1. Enrolment over time (with trend line)")
        if len(enrol):
            line(enrol, "Year", "Value", f"Enrolment — {level} (thousands/number)")
        else:
            st.info("No enrolment series for this level.")
    with c2:
        section("2. Teachers over time (with trend line)")
        if len(teach):
            line(teach, "Year", "Value", f"Teachers — {level}")
        else:
            st.info("No teacher series for this level.")

    c1, c2 = st.columns(2)
    with c1:
        section("3. Number of institutions over time")
        if len(num):
            line(num, "Year", "Value", f"Institutions — {level}")
        else:
            st.info("No institution-count series for this level.")
    with c2:
        section("4. Student:Teacher ratio over time")
        if len(ratio):
            line(ratio, "Year", "Value", f"Student:Teacher ratio — {level}", trend=True)
        else:
            st.info("No ratio series for this level.")

    c1, c2 = st.columns(2)
    with c1:
        section("5. Female teacher share over time (%)")
        if len(female_pct):
            line(female_pct, "Year", "Value", f"% Female teachers — {level}")
        else:
            st.info("No female-teacher-share series for this level.")
    with c2:
        section("6. Enrolment growth rate (Year-over-year %)")
        if len(enrol) > 2:
            yoy = enrol.copy()
            yoy["YoY %"] = pd.to_numeric(yoy["Value"], errors="coerce").pct_change() * 100
            bar(yoy, "Year", "YoY %", "YoY change in enrolment", color="YoY %", color_continuous_scale="RdYlGn")
        else:
            st.info("Not enough data points.")

    c1, c2 = st.columns(2)
    with c1:
        section(f"7. Enrolment comparison across all levels — latest year")
        comp = []
        for lvl in levels:
            lvl_metrics = df[df["Level"] == lvl]["Metric"].unique().tolist()
            em = next((m for m in lvl_metrics if m.startswith("Enrolment")), None)
            if em:
                s = _get_series(df, lvl, em)
                if len(s):
                    comp.append({"Level": lvl, "Latest Enrolment": s.iloc[-1]["Value"]})
        comp_df = pd.DataFrame(comp)
        if len(comp_df):
            bar(comp_df.sort_values("Latest Enrolment", ascending=False), "Level", "Latest Enrolment",
                "Enrolment by level (latest year available)")
    with c2:
        section("8. Enrolment share across levels (latest year)")
        if len(comp_df):
            pie(comp_df["Level"], comp_df["Latest Enrolment"], "Share of total enrolment by level")

    c1, c2 = st.columns(2)
    with c1:
        section("9. Enrolment vs Teachers growth (indexed, base=100)")
        if len(enrol) and len(teach):
            merged = pd.merge(enrol, teach, on="Year", suffixes=("_enrol", "_teach"))
            if len(merged):
                idx = pd.DataFrame({"Year": merged["Year"]})
                idx["Enrolment"] = merged["Value_enrol"] / merged["Value_enrol"].iloc[0] * 100
                idx["Teachers"] = merged["Value_teach"] / merged["Value_teach"].iloc[0] * 100
                melt = idx.melt(id_vars="Year", value_vars=["Enrolment", "Teachers"], var_name="Metric", value_name="Index")
                fig = px.line(melt, x="Year", y="Index", color="Metric", markers=True, color_discrete_sequence=PALETTE)
                fig.add_hline(y=100, line_dash="dot", line_color="gray")
                st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Need both enrolment and teacher series for this comparison.")
    with c2:
        section("10. Full data table — this level")
        st.dataframe(df[df["Level"] == level], use_container_width=True, hide_index=True)


def render_schools():
    render_education(SCHOOL_LEVELS, widget_prefix="edu_sch")


def render_colleges():
    render_education(COLLEGE_LEVELS, widget_prefix="edu_col")


def render_universities():
    render_education(UNIVERSITY_LEVELS, widget_prefix="edu_uni")
