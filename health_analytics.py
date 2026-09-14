import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import loaders as L

PALETTE = ["#2C5F8A", "#C1440E", "#4C8C4A", "#8A5FC1", "#C19A2C",
           "#3A9BA0", "#B03A5B", "#6B6B6B", "#5B7C99", "#9C6B30"]


def kpi_row(items):
    cols = st.columns(len(items))
    for c, (label, value, delta) in zip(cols, items):
        c.metric(label, value, delta)


def section(title):
    st.markdown(f"#### {title}")


def bar(df=None, x=None, y=None, title="", **kw):
    if df is not None:
        fig = px.bar(df, x=x, y=y, title=title, color_discrete_sequence=PALETTE, **kw)
    else:
        fig = px.bar(x=x, y=y, title=title, color_discrete_sequence=PALETTE, **kw)
    orient = fig.data[0].orientation if fig.data else 'v'
    axis_title = (fig.layout.xaxis.title.text or '') if orient == 'h' else (fig.layout.yaxis.title.text or '')
    is_pct = '%' in axis_title
    n_traces = len(fig.data)
    if 1 < n_traces <= 4:
        for tr in fig.data:
            nm = tr.name or ''
            fmt = f'{nm}: %{{value:,.1f}}%' if is_pct else f'{nm}: %{{value:,.0f}}'
            tr.update(texttemplate=fmt, textposition='outside', cliponaxis=False)
    else:
        vfmt = '%{value:,.1f}%' if is_pct else '%{value:,.0f}'
        fig.update_traces(texttemplate=vfmt, textposition='outside', cliponaxis=False)
    fig.update_layout(uniformtext_minsize=8, uniformtext_mode='hide',
                       margin=dict(r=70, t=40) if orient == 'h' else dict(t=40))
    st.plotly_chart(fig, use_container_width=True)


def line(df, x, y, title="", trend=True, **kw):
    fig = px.line(df, x=x, y=y, title=title, markers=True, color_discrete_sequence=PALETTE, **kw)
    for tr in fig.data:
        if 'lines' in str(tr.mode or '') and len(tr.x) <= 12:
            is_pct = '%' in str(tr.name or '') or '%' in (fig.layout.yaxis.title.text or '')
            tr.update(texttemplate='%{y:,.1f}%' if is_pct else '%{y:,.0f}',
                      textposition='top center', mode='lines+markers+text')
    if trend and "color" not in kw:
        y_cols = y if isinstance(y, list) else [y]
        for i, col in enumerate(y_cols):
            yv = pd.to_numeric(df[col], errors="coerce")
            if yv.notna().sum() >= 3:
                idx = list(range(len(df)))
                coeffs = np.polyfit(idx, yv.fillna(yv.mean()), 1)
                tr = np.poly1d(coeffs)(idx)
                fig.add_scatter(x=df[x], y=tr, mode="lines", name=f"{col} trend",
                                 line=dict(dash="dash", color=PALETTE[(i + 5) % len(PALETTE)]))
    fig.update_layout(uniformtext_minsize=7, uniformtext_mode='hide')
    st.plotly_chart(fig, use_container_width=True)


def pie(names, values, title="", hole=0.45):
    fig = px.pie(names=names, values=values, title=title, hole=hole, color_discrete_sequence=PALETTE)
    fig.update_traces(textinfo="label+percent", textposition="inside")
    st.plotly_chart(fig, use_container_width=True)


# ============================================================
# 1. Health institutes & beds
# ============================================================

def render_health_institutes():
    df = L.load_health_institutes_beds()
    years = [c for c in df.columns if c != "Indicator"]
    top_level = [i for i in df["Indicator"] if i[0].isdigit()]

    inst_row = df[df["Indicator"].str.startswith("1.")].iloc[0]
    beds_row = df[df["Indicator"].str.startswith("2.")].iloc[0]
    doctors_row = df[df["Indicator"].str.startswith("3.")].iloc[0]
    latest_yr, first_yr = years[-1], years[0]

    kpi_row([
        (f"Institutions ({latest_yr})", f"{int(inst_row[latest_yr]):,}", None),
        (f"Total beds ({latest_yr})", f"{int(beds_row[latest_yr]):,}", None),
        (f"Doctors ({latest_yr})", f"{int(doctors_row[latest_yr]):,}", None),
        ("Beds growth", f"{(beds_row[latest_yr]-beds_row[first_yr])/beds_row[first_yr]*100:+.1f}%", f"since {first_yr}"),
        ("Doctors growth", f"{(doctors_row[latest_yr]-doctors_row[first_yr])/doctors_row[first_yr]*100:+.1f}%", f"since {first_yr}"),
    ])
    st.divider()

    c1, c2 = st.columns(2)
    with c1:
        section("1. Number of institutions over time")
        d = pd.DataFrame({"Year": years, "Institutions": inst_row[years].astype(float).values})
        line(d, "Year", "Institutions", "Health institutions — yearly")
    with c2:
        section("2. Total beds over time")
        d = pd.DataFrame({"Year": years, "Beds": beds_row[years].astype(float).values})
        line(d, "Year", "Beds", "Total beds — yearly")

    c1, c2 = st.columns(2)
    with c1:
        section("3. Medical personnel over time")
        personnel = ["3. Doctors", "4. Dentists", "5. Lady Health Visitors", "6. Midwives", "7. Nurses"]
        sub = df[df["Indicator"].isin(personnel)].set_index("Indicator")[years].T.reset_index()
        sub.columns = ["Year"] + personnel
        melt = sub.melt(id_vars="Year", value_vars=personnel, var_name="Role", value_name="Count")
        fig = px.line(melt, x="Year", y="Count", color="Role", markers=True, color_discrete_sequence=PALETTE)
        for _tr in fig.data:
            if len(_tr.x) <= 12:
                _isp = '%' in str(_tr.name or '') or '%' in (fig.layout.yaxis.title.text or '')
                _tr.update(texttemplate='%{y:,.1f}%' if _isp else '%{y:,.0f}', textposition='top center', mode='lines+markers+text')
        st.plotly_chart(fig, use_container_width=True)
    with c2:
        section(f"4. Personnel composition — {latest_yr}")
        vals = df[df["Indicator"].isin(personnel)].set_index("Indicator")[latest_yr]
        pie(vals.index, vals.values, f"Health workforce mix — {latest_yr}")

    c1, c2 = st.columns(2)
    with c1:
        section("5. Facility type breakdown (selected year)")
        yr_sel = st.selectbox("Year", years[::-1], key="hi_yr")
        facility_rows = [i for i in df["Indicator"] if "beds" not in i.lower() and i[0].islower()]
        fac = df[df["Indicator"].isin(facility_rows)].set_index("Indicator")[yr_sel]
        bar(x=fac.index, y=fac.values, title=f"Facility counts — {yr_sel}")
    with c2:
        section("6. Beds by facility type (selected year)")
        bed_rows = [i for i in df["Indicator"] if "no. of beds" in i.lower()]
        beds_by_type = df[df["Indicator"].isin(bed_rows)].set_index("Indicator")[yr_sel]
        beds_by_type.index = [i.split("—")[0].strip() for i in beds_by_type.index]
        bar(x=beds_by_type.index, y=beds_by_type.values, title=f"Beds by facility type — {yr_sel}")

    c1, c2 = st.columns(2)
    with c1:
        section("7. Doctor-to-institution ratio over time")
        ratio = pd.DataFrame({"Year": years,
                               "Doctors per institution": (doctors_row[years].astype(float).values / inst_row[years].astype(float).values).round(1)})
        line(ratio, "Year", "Doctors per institution", "Doctors per institution")
    with c2:
        section("8. Nurses vs Doctors over time")
        d2 = pd.DataFrame({"Year": years, "Doctors": doctors_row[years].astype(float).values,
                            "Nurses": df[df["Indicator"] == "7. Nurses"].iloc[0][years].astype(float).values})
        bar(d2, "Year", ["Doctors", "Nurses"], "Doctors vs Nurses", barmode="group")

    c1, c2 = st.columns(2)
    with c1:
        section("9. Year-over-year % growth in beds")
        yoy = pd.DataFrame({"Year": years, "Beds": beds_row[years].astype(float).values})
        yoy["YoY %"] = yoy["Beds"].pct_change() * 100
        bar(yoy, "Year", "YoY %", "YoY change in total beds", color="YoY %", color_continuous_scale="RdYlGn")
    with c2:
        section("10. Full data table")
        st.dataframe(df, use_container_width=True, hide_index=True)


# ============================================================
# 2. Immunization — yearly
# ============================================================

def render_immunization_yearly():
    df = L.load_immunization_yearly()
    latest, first = df.iloc[-1], df.iloc[0]
    core = ["Polio (0+1)", "Measles", "BCG"]

    kpi_row([
        (f"Polio doses ({int(latest['Year'])})", f"{int(latest['Polio (0+1)']):,}", None),
        (f"Measles doses ({int(latest['Year'])})", f"{int(latest['Measles']):,}", None),
        (f"BCG doses ({int(latest['Year'])})", f"{int(latest['BCG']):,}", None),
        ("Polio growth", f"{(latest['Polio (0+1)']-first['Polio (0+1)'])/first['Polio (0+1)']*100:+.1f}%", f"since {int(first['Year'])}"),
        ("Measles growth", f"{(latest['Measles']-first['Measles'])/first['Measles']*100:+.1f}%", f"since {int(first['Year'])}"),
    ])
    st.divider()

    c1, c2 = st.columns(2)
    with c1:
        section("1. Core vaccines over time (with trend lines)")
        line(df, "Year", core, "Polio / Measles / BCG doses — yearly")
    with c2:
        section("2. Polio dose series (0+1, II, III)")
        line(df, "Year", ["Polio (0+1)", "Polio II", "Polio III"], "Polio dose completion by dose number")

    c1, c2 = st.columns(2)
    with c1:
        section("3. Pentavalent doses (I, II, III)")
        line(df, "Year", ["Pentavalent I", "Pentavalent II", "Pentavalent III"], "Pentavalent dose series")
    with c2:
        section("4. Pneumococcal doses (I, II, III)")
        pn = df.dropna(subset=["Pneumococcal I"])
        line(pn, "Year", ["Pneumococcal I", "Pneumococcal II", "Pneumococcal III"], "Pneumococcal dose series")

    c1, c2 = st.columns(2)
    with c1:
        section("5. TT (Tetanus Toxoid) doses over time")
        line(df, "Year", ["TT I", "TT II", "TT III"], "TT doses I-III")
    with c2:
        section(f"6. Vaccine mix — {int(latest['Year'])}")
        mix = latest[["Polio (0+1)", "Measles", "BCG", "Pentavalent I", "Pneumococcal I"]]
        pie(mix.index, mix.values, f"Dose share by vaccine — {int(latest['Year'])}")

    c1, c2 = st.columns(2)
    with c1:
        section("7. Dose completion drop-off (dose I → III)")
        dropoff = pd.DataFrame({
            "Vaccine": ["Polio", "Pentavalent", "Pneumococcal"],
            "Dose I": [latest["Polio (0+1)"], latest["Pentavalent I"], latest["Pneumococcal I"]],
            "Dose III": [latest["Polio III"], latest["Pentavalent III"], latest["Pneumococcal III"]],
        })
        bar(dropoff, "Vaccine", ["Dose I", "Dose III"], "First vs third dose completion", barmode="group")
    with c2:
        section("8. Year-over-year % change — Measles")
        yoy = df.copy()
        yoy["YoY %"] = df["Measles"].pct_change() * 100
        bar(yoy, "Year", "YoY %", "Measles YoY change", color="YoY %", color_continuous_scale="RdYlGn")

    c1, c2 = st.columns(2)
    with c1:
        section("9. BCG vs Measles growth (indexed, base=100)")
        idx = df[["BCG", "Measles"]].div(df[["BCG", "Measles"]].iloc[0]) * 100
        idx["Year"] = df["Year"]
        melt = idx.melt(id_vars="Year", value_vars=["BCG", "Measles"], var_name="Vaccine", value_name="Index")
        fig = px.line(melt, x="Year", y="Index", color="Vaccine", markers=True, color_discrete_sequence=PALETTE)
        for _tr in fig.data:
            if len(_tr.x) <= 12:
                _isp = '%' in str(_tr.name or '') or '%' in (fig.layout.yaxis.title.text or '')
                _tr.update(texttemplate='%{y:,.1f}%' if _isp else '%{y:,.0f}', textposition='top center', mode='lines+markers+text')
        fig.add_hline(y=100, line_dash="dot", line_color="gray")
        st.plotly_chart(fig, use_container_width=True)
    with c2:
        section("10. Full data table")
        st.dataframe(df, use_container_width=True, hide_index=True)


# ============================================================
# 3. Immunization — monthly
# ============================================================

def render_immunization_monthly():
    year = st.selectbox("Year", [2022, 2023, 2024, 2025], key="im_year")
    topic = st.selectbox("Age group", ["0-11 months", "12-23 months", "TT (women)"], key="im_topic")
    df = L.load_immunization_monthly(year, topic)
    if df.empty:
        st.info("Data not available for this selection.")
        return

    vaccine_cols = [c for c in df.columns if c != "Month" and df[c].notna().any()]
    totals = df[vaccine_cols].sum()
    top_vaccine = totals.idxmax()

    kpi_row([
        (f"Total doses ({year})", f"{int(totals.sum()):,}", None),
        ("Top vaccine/dose", top_vaccine, f"{int(totals.max()):,}"),
        ("Vaccines/doses tracked", str(len(vaccine_cols)), None),
        ("Peak month (top vaccine)", df.loc[df[top_vaccine].idxmax(), "Month"] if df[top_vaccine].notna().any() else "N/A", None),
        ("Age group", topic, None),
    ])
    st.divider()

    default_sel = vaccine_cols[:3]
    section("1. Monthly trend — select vaccines/doses (with trend lines)")
    selected = st.multiselect("Vaccines/doses", vaccine_cols, default=default_sel, key="im_sel")
    if selected:
        line(df, "Month", selected, f"Monthly doses — {topic} ({year})")

    c1, c2 = st.columns(2)
    with c1:
        section("2. Total doses by month (all selected vaccines)")
        d = df.copy()
        d["Total (selected)"] = d[selected].sum(axis=1) if selected else 0
        bar(d, "Month", "Total (selected)", "Monthly total — selected vaccines")
    with c2:
        section("3. Share by vaccine (annual total)")
        pie(totals.index, totals.values, f"Vaccine share — {year}")

    c1, c2 = st.columns(2)
    with c1:
        section("4. Heatmap — vaccine × month")
        heat = df.set_index("Month")[vaccine_cols].T
        fig = px.imshow(heat, aspect="auto", color_continuous_scale="OrRd", labels=dict(color="Doses"))
        st.plotly_chart(fig, use_container_width=True)
    with c2:
        section("5. Top vaccine — seasonal pattern")
        avg = df[top_vaccine].mean()
        idx = (df[top_vaccine] / avg * 100).round(1)
        bar(x=df["Month"], y=idx.values, title=f"Seasonal index — {top_vaccine} (100=avg)",
            color=idx.values, color_continuous_scale="RdYlGn")

    c1, c2 = st.columns(2)
    with c1:
        section("6. Ranking — total doses by vaccine")
        bar(x=totals.sort_values(ascending=False).index, y=totals.sort_values(ascending=False).values,
            title="Total doses by vaccine (annual)")
    with c2:
        section("7. Cumulative doses through the year (top vaccine)")
        cum = df[["Month", top_vaccine]].copy()
        cum["Cumulative"] = cum[top_vaccine].cumsum()
        line(cum, "Month", "Cumulative", f"Cumulative {top_vaccine} doses", trend=False)

    c1, c2 = st.columns(2)
    with c1:
        section("8. Month-to-month volatility by vaccine")
        vol = df[vaccine_cols].std().sort_values(ascending=False).head(8)
        bar(x=vol.index, y=vol.values, title="Std. deviation across months (top 8)")
    with c2:
        section("9. Min vs Max month (top vaccine)")
        mn, mx = df[top_vaccine].min(), df[top_vaccine].max()
        bar(x=["Min month", "Max month"], y=[mn, mx], title=f"{top_vaccine}: lowest vs highest month")

    section("10. Full data table")
    st.dataframe(df, use_container_width=True, hide_index=True)


# ============================================================
# 4. HIV/AIDS treatment centres
# ============================================================

def render_hiv():
    frames = L.load_hiv_data()
    months = list(frames.keys())
    month = st.selectbox("Month", months, key="hiv_month")
    df = frames[month]
    top10 = df.sort_values("TOTAL", ascending=False).head(10)
    gcols = ["Male Total", "Female Total", "Children Total", "Transgender Total"]
    gshares = df[gcols].sum()

    kpi_row([
        ("Total patients", f"{int(df['TOTAL'].sum()):,}", month),
        ("On ART", f"{int(df['TOTAL on ART'].sum()):,}", None),
        ("ART coverage", f"{df['TOTAL on ART'].sum()/df['TOTAL'].sum()*100:.1f}%", None),
        ("Centres reporting", str(len(df)), None),
        ("Top centre", top10.iloc[0]["Centre"], f"{int(top10.iloc[0]['TOTAL']):,}"),
    ])
    st.divider()

    c1, c2 = st.columns(2)
    with c1:
        section("1. Top 10 centres by total patients")
        bar(top10, "Centre", "TOTAL", f"Top 10 HIV centres — {month}")
    with c2:
        section("2. Patient composition by group")
        pie(gshares.index, gshares.values, f"Patient composition — {month}")

    c1, c2 = st.columns(2)
    with c1:
        section("3. ART coverage — top 10 centres")
        top10c = top10.copy()
        top10c["ART %"] = (top10c["TOTAL on ART"] / top10c["TOTAL"] * 100).round(1)
        bar(top10c, "Centre", "ART %", "% on ART — top 10 centres")
    with c2:
        section("4. Total vs On ART (top 10)")
        bar(top10, "Centre", ["TOTAL", "TOTAL on ART"], "Total vs On ART", barmode="group")

    c1, c2 = st.columns(2)
    with c1:
        section("5. Male vs Female patients (top 10)")
        bar(top10, "Centre", ["Male Total", "Female Total"], "Gender split — top 10 centres", barmode="group")
    with c2:
        section("6. Trend across months — total patients (national)")
        trend_data = []
        for m, d in frames.items():
            trend_data.append({"Month": m, "Total": d["TOTAL"].sum(), "On ART": d["TOTAL on ART"].sum()})
        tdf = pd.DataFrame(trend_data)
        line(tdf, "Month", ["Total", "On ART"], "National totals across all months", trend=False)

    c1, c2 = st.columns(2)
    with c1:
        section("7. Children & Transgender patients (centres with any)")
        sub = df[(df["Children Total"] > 0) | (df["Transgender Total"] > 0)].sort_values("TOTAL", ascending=False).head(10)
        if len(sub):
            bar(sub, "Centre", ["Children Total", "Transgender Total"], "Children & Transgender — top centres", barmode="group")
        else:
            st.info("No centres with children/transgender patients this month.")
    with c2:
        section("8. Distribution of centre sizes")
        fig = px.histogram(df, x="TOTAL", nbins=15, color_discrete_sequence=[PALETTE[3]])
        st.plotly_chart(fig, use_container_width=True)

    c1, c2 = st.columns(2)
    with c1:
        section("9. Bottom 10 centres by total patients")
        bottom10 = df.sort_values("TOTAL", ascending=True).head(10)
        bar(bottom10, "Centre", "TOTAL", "Smallest 10 centres")
    with c2:
        section("10. Full data table")
        st.dataframe(df, use_container_width=True, hide_index=True)


# ============================================================
# 5. Traffic accidents — monthly (by region)
# ============================================================

def render_traffic_monthly():
    year = st.selectbox("Year", [2022, 2023, 2024, 2025], key="tm_year")
    regions = L.load_traffic_monthly(year)
    region = st.selectbox("Region", list(regions.keys()), key="tm_region")
    df = regions[region].copy()
    df = df[df["Total"] > 0] if df["Total"].sum() > 0 else df
    df["Fatality Rate %"] = (df["Killed"] / df["Total"].replace(0, np.nan) * 100).round(1)
    latest = df.iloc[-1] if len(df) else None

    kpi_row([
        (f"Total accidents ({region})", f"{int(df['Total'].sum()):,}", str(year)),
        ("Fatal", f"{int(df['Fatal'].sum()):,}", None),
        ("Killed", f"{int(df['Killed'].sum()):,}", None),
        ("Injured", f"{int(df['Injured'].sum()):,}", None),
        ("Avg fatality rate", f"{df['Fatality Rate %'].mean():.1f}%" if len(df) else "N/A", None),
    ])
    st.divider()

    c1, c2 = st.columns(2)
    with c1:
        section("1. Total accidents by month (with trend line)")
        line(df, "Month", "Total", f"{region} — accidents by month ({year})")
    with c2:
        section("2. Fatal vs Non-fatal by month")
        bar(df, "Month", ["Fatal", "Non-Fatal"], "Fatal vs Non-fatal", barmode="stack")

    c1, c2 = st.columns(2)
    with c1:
        section("3. Killed vs Injured by month")
        bar(df, "Month", ["Killed", "Injured"], "Casualties by month", barmode="group")
    with c2:
        section("4. Fatality rate trend (%)")
        line(df, "Month", "Fatality Rate %", "Fatality rate by month")

    c1, c2 = st.columns(2)
    with c1:
        section("5. Compare all regions — total accidents")
        comp = pd.DataFrame({r: d["Total"].values for r, d in regions.items() if len(d) == len(df)})
        comp["Month"] = df["Month"].values
        melt = comp.melt(id_vars="Month", var_name="Region", value_name="Total")
        fig = px.line(melt, x="Month", y="Total", color="Region", markers=True, color_discrete_sequence=PALETTE)
        for _tr in fig.data:
            if len(_tr.x) <= 12:
                _isp = '%' in str(_tr.name or '') or '%' in (fig.layout.yaxis.title.text or '')
                _tr.update(texttemplate='%{y:,.1f}%' if _isp else '%{y:,.0f}', textposition='top center', mode='lines+markers+text')
        st.plotly_chart(fig, use_container_width=True)
    with c2:
        section("6. Vehicles involved by month")
        bar(df, "Month", "Total Vehicles", "Vehicles involved per month")

    c1, c2 = st.columns(2)
    with c1:
        section("7. Share of annual accidents by month")
        pie(df["Month"], df["Total"], f"Monthly share of {year} accidents")
    with c2:
        section("8. Region ranking — total accidents (annual)")
        rank = pd.DataFrame({"Region": list(regions.keys()), "Total": [d["Total"].sum() for d in regions.values()]})
        bar(rank.sort_values("Total", ascending=False), "Region", "Total", "Annual total by region")

    c1, c2 = st.columns(2)
    with c1:
        section("9. Injured-per-accident ratio")
        df["Injured/Accident"] = (df["Injured"] / df["Total"].replace(0, np.nan)).round(2)
        line(df, "Month", "Injured/Accident", "Injured per accident")
    with c2:
        section("10. Full data table")
        st.dataframe(df, use_container_width=True, hide_index=True)


# ============================================================
# 6. Veterinary registrations — monthly
# ============================================================

def render_veterinary_monthly():
    year = st.selectbox("Year", [2022, 2023, 2024, 2025], key="vt_year")
    topic = st.selectbox("Category", ["Veterinary Practitioners", "Animal Husbandry Graduates"], key="vt_topic")
    df = L.load_veterinary_monthly(year, topic)
    reg_cols = [c for c in df.columns if c not in ("Month", "Total")]
    total = df["Total"].sum()

    kpi_row([
        (f"Total registered ({year})", f"{int(total):,}" if pd.notna(total) else "0", None),
        ("Male", f"{int(df['Male'].sum()):,}" if df['Male'].notna().any() else "0", None),
        ("Female", f"{int(df['Female'].sum()):,}" if df['Female'].notna().any() else "0", None),
        ("Peak month", df.loc[df["Total"].idxmax(), "Month"] if df["Total"].notna().any() and df["Total"].max() > 0 else "N/A", None),
        ("Category", topic, None),
    ])
    st.divider()

    if total == 0 or pd.isna(total):
        st.info("Source file shows 'NIL' for most/all months in this category for this year — genuinely little to no registration activity, not a data gap.")

    c1, c2 = st.columns(2)
    with c1:
        section("1. Total registrations by month")
        bar(df, "Month", "Total", f"{topic} registered by month — {year}")
    with c2:
        section("2. Male vs Female by month")
        bar(df, "Month", ["Male", "Female"], "Gender split by month", barmode="group")

    c1, c2 = st.columns(2)
    with c1:
        section("3. Qualification breakdown (annual total)")
        qual_totals = df[reg_cols].sum()
        qual_totals = qual_totals[qual_totals > 0]
        if len(qual_totals):
            bar(x=qual_totals.index, y=qual_totals.values, title="Registrations by qualification")
        else:
            st.info("No qualification-level data available (all NIL).")
    with c2:
        section("4. Gender share (annual)")
        gshare = df[["Male", "Female"]].sum()
        if gshare.sum() > 0:
            pie(gshare.index, gshare.values, "Gender share — annual")
        else:
            st.info("No registrations recorded this year.")

    c1, c2 = st.columns(2)
    with c1:
        section("5. Cumulative registrations through the year")
        d = df.copy()
        d["Cumulative"] = d["Total"].fillna(0).cumsum()
        line(d, "Month", "Cumulative", "Cumulative registrations", trend=False)
    with c2:
        section("6. Qualification mix by month (stacked)")
        active_cols = [c for c in reg_cols if df[c].sum() > 0]
        if active_cols:
            bar(df, "Month", active_cols, "Qualification mix by month", barmode="stack")
        else:
            st.info("No qualification-level monthly data available.")

    c1, c2 = st.columns(2)
    with c1:
        section("7. Compare Veterinary vs Animal Husbandry (this year)")
        vet = L.load_veterinary_monthly(year, "Veterinary Practitioners")
        ah = L.load_veterinary_monthly(year, "Animal Husbandry Graduates")
        comp = pd.DataFrame({"Month": vet["Month"], "Veterinary Practitioners": vet["Total"].fillna(0),
                              "Animal Husbandry Graduates": ah["Total"].fillna(0)})
        bar(comp, "Month", ["Veterinary Practitioners", "Animal Husbandry Graduates"], "Category comparison", barmode="group")
    with c2:
        section("8. Months with zero registrations")
        zero_months = df[df["Total"].fillna(0) == 0]["Month"].tolist()
        st.metric("Zero-registration months", f"{len(zero_months)} / {len(df)}")
        if zero_months:
            st.write(", ".join(zero_months))

    c1, c2 = st.columns(2)
    with c1:
        section("9. Highest single month")
        if df["Total"].notna().any() and df["Total"].max() > 0:
            peak = df.loc[df["Total"].idxmax()]
            bar(x=reg_cols, y=[peak[c] if pd.notna(peak[c]) else 0 for c in reg_cols],
                title=f"Breakdown — {peak['Month']} (peak month)")
        else:
            st.info("No peak month to show (all NIL).")
    with c2:
        section("10. Full data table")
        st.dataframe(df, use_container_width=True, hide_index=True)


# ============================================================
# 7. TB by province
# ============================================================

def render_tb():
    year = st.selectbox("Year", [2022, 2024], key="tb_year")
    quarters = L.load_tb_by_province(year)
    if not quarters:
        st.info("TB data not available for this year in the source files.")
        return
    quarter = st.selectbox("Quarter", list(quarters.keys()), key="tb_quarter")
    df = quarters[quarter].copy()
    pak = df[df["Province/Region"] == "Pakistan"]
    no_pak = df[df["Province/Region"] != "Pakistan"]

    kpi_row([
        ("Total TB cases (B+)", f"{int(pak['TB Cases B+'].iloc[0]):,}" if len(pak) else "N/A", quarter),
        ("Total cases (all types)", f"{int(pak['Total'].iloc[0]):,}" if len(pak) else "N/A", None),
        ("Avg treatment success", f"{df['% Treatment Success'].mean()*100:.1f}%", None),
        ("Highest-burden province", no_pak.set_index('Province/Region')['Total'].idxmax(), None),
        ("Provinces/regions", str(len(no_pak)), None),
    ])
    st.divider()

    c1, c2 = st.columns(2)
    with c1:
        section("1. TB cases by province")
        bar(no_pak.sort_values("Total", ascending=False), "Province/Region", "Total", f"TB cases by province — {quarter}")
    with c2:
        section("2. Share of national cases by province")
        pie(no_pak["Province/Region"], no_pak["Total"], f"Province share — {quarter}")

    c1, c2 = st.columns(2)
    with c1:
        section("3. Male vs Female cases by province")
        bar(no_pak, "Province/Region", ["Male", "Female"], "Gender split by province", barmode="group")
    with c2:
        section("4. Treatment success rate by province")
        bar(no_pak.sort_values("% Treatment Success", ascending=False), "Province/Region",
            (no_pak["% Treatment Success"] * 100).round(1), title="Treatment success rate (%)")

    c1, c2 = st.columns(2)
    with c1:
        section("5. Case Detection Rate (CDR) by province")
        bar(no_pak.sort_values("CDR", ascending=False), "Province/Region", "CDR", "Case Detection Rate")
    with c2:
        section("6. Trend across quarters — national total")
        trend = []
        for q, d in quarters.items():
            p = d[d["Province/Region"] == "Pakistan"]
            if len(p):
                trend.append({"Quarter": q, "Total": p["Total"].iloc[0]})
        tdf = pd.DataFrame(trend)
        if len(tdf):
            line(tdf, "Quarter", "Total", f"National TB cases across quarters — {year}", trend=False)

    c1, c2 = st.columns(2)
    with c1:
        section("7. TB Cases B+ vs Total (all types)")
        bar(no_pak, "Province/Region", ["TB Cases B+", "Total"], "B+ vs All-type cases", barmode="group")
    with c2:
        section("8. Gender composition (100% stacked)")
        gdf = no_pak.set_index("Province/Region")[["Male", "Female"]]
        gpct = gdf.div(gdf.sum(axis=1), axis=0) * 100
        melt = gpct.reset_index().melt(id_vars="Province/Region", var_name="Gender", value_name="Share %")
        bar(melt, "Province/Region", "Share %", "Gender composition by province", color="Gender")

    c1, c2 = st.columns(2)
    with c1:
        section("9. CNR (Case Notification Rate) by province")
        bar(no_pak.sort_values("CNR B+", ascending=False), "Province/Region", "CNR B+", "Case Notification Rate")
    with c2:
        section("10. Full data table")
        st.dataframe(df, use_container_width=True, hide_index=True)


# ============================================================
# 8. Hospitals by province (source file mislabeled "Dental Doctors")
# ============================================================

def render_hospitals_by_province():
    st.warning("Data note: this source file is titled 'No. of Dental Doctors' but its actual contents are "
               "hospitals/dispensaries/beds counts by province — no dental-doctor-specific column exists in "
               "the published file. Showing the file's real content as-is.")
    provinces = L.load_dental_doctors()
    province = st.selectbox("Province", list(provinces.keys()), key="hp_province")
    df = provinces[province]
    latest, first = df.iloc[-1], df.iloc[0]

    kpi_row([
        (f"Hospitals ({int(latest['Year'])})", f"{int(latest['Hospitals']):,}", None),
        (f"Dispensaries ({int(latest['Year'])})", f"{int(latest['Dispensaries']):,}", None),
        (f"Beds ({int(latest['Year'])})", f"{int(latest['Beds']):,}", None),
        ("Hospitals growth", f"{(latest['Hospitals']-first['Hospitals'])/first['Hospitals']*100:+.1f}%", f"since {int(first['Year'])}"),
        ("Beds growth", f"{(latest['Beds']-first['Beds'])/first['Beds']*100:+.1f}%", f"since {int(first['Year'])}"),
    ])
    st.divider()

    c1, c2 = st.columns(2)
    with c1:
        section("1. Hospitals over time (with trend line)")
        line(df, "Year", "Hospitals", f"{province} — hospitals over time")
    with c2:
        section("2. Dispensaries over time (with trend line)")
        line(df, "Year", "Dispensaries", f"{province} — dispensaries over time")

    c1, c2 = st.columns(2)
    with c1:
        section("3. Beds over time (with trend line)")
        line(df, "Year", "Beds", f"{province} — beds over time")
    with c2:
        section("4. Maternity & Child Centres over time")
        line(df, "Year", "Maternity & Child Centres", f"{province} — MCH centres over time")

    c1, c2 = st.columns(2)
    with c1:
        section("5. Compare all provinces — hospitals (latest year)")
        comp = pd.DataFrame({p: d.iloc[-1] for p, d in provinces.items()}).T
        comp = comp.reset_index().rename(columns={"index": "Province"})
        bar(comp.sort_values("Hospitals", ascending=False), "Province", "Hospitals", "Hospitals by province (latest)")
    with c2:
        section("6. Compare all provinces — beds (latest year)")
        bar(comp.sort_values("Beds", ascending=False), "Province", "Beds", "Beds by province (latest)")

    c1, c2 = st.columns(2)
    with c1:
        section("7. Beds per hospital (efficiency indicator)")
        df["Beds per Hospital"] = (df["Beds"] / df["Hospitals"]).round(1)
        line(df, "Year", "Beds per Hospital", "Average beds per hospital")
    with c2:
        section("8. Year-over-year % change — hospitals")
        yoy = df.copy()
        yoy["YoY %"] = df["Hospitals"].pct_change() * 100
        bar(yoy, "Year", "YoY %", "YoY change in hospitals", color="YoY %", color_continuous_scale="RdYlGn")

    c1, c2 = st.columns(2)
    with c1:
        section("9. Share of national beds by province (latest year)")
        pie(comp["Province"], comp["Beds"], "Beds share by province (latest year)")
    with c2:
        section("10. Full data table")
        st.dataframe(df, use_container_width=True, hide_index=True)