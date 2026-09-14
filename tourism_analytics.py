import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import loaders as L

PALETTE = ["#2C5F8A", "#C1440E", "#4C8C4A", "#8A5FC1", "#C19A2C",
           "#3A9BA0", "#B03A5B", "#6B6B6B", "#5B7C99", "#9C6B30"]

PROVINCE_LABELS = {"PAKISTAN", "PUNJAB", "SINDH", "KHYBER PAKHTUNKHWA", "BALOCHISTAN"}


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
        if 'lines' in str(tr.mode or ''):
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
# 1 & 2. Museum / Heritage visitors — multi-year (shared logic)
# ============================================================

def _render_visitor_multiyear(df, kind_label):
    all_places = sorted(df["Place"].unique().tolist())
    province_rows = [p for p in all_places if p.upper() in PROVINCE_LABELS]
    site_rows = [p for p in all_places if p.upper() not in PROVINCE_LABELS and p.upper() != "PAKISTAN"]

    national = df[df["Place"].str.upper() == "PAKISTAN"].sort_values("Year")
    totals_by_site = df[df["Place"].isin(site_rows)].groupby("Place")[["Foreigner", "National"]].sum()
    totals_by_site["Total"] = totals_by_site["Foreigner"] + totals_by_site["National"]
    top10 = totals_by_site.sort_values("Total", ascending=False).head(10)

    latest_year = national["Year"].max()
    latest = national[national["Year"] == latest_year].iloc[0]
    first = national.iloc[0]
    total_latest = latest["Foreigner"] + latest["National"]
    total_first = first["Foreigner"] + first["National"]

    kpi_row([
        (f"Total visitors ({int(latest_year)})", f"{int(total_latest):,}", None),
        ("Foreigner visitors", f"{int(latest['Foreigner']):,}", None),
        ("National visitors", f"{int(latest['National']):,}", None),
        (f"Growth since {int(first['Year'])}", f"{(total_latest-total_first)/total_first*100:+.1f}%", None),
        (f"Top {kind_label.lower()}", top10.index[0], f"{int(top10.iloc[0]['Total']):,}"),
    ])
    st.divider()

    c1, c2 = st.columns(2)
    with c1:
        section("1. National total visitors over time (with trend line)")
        national = national.copy()
        national["Total"] = national["Foreigner"] + national["National"]
        line(national, "Year", "Total", f"National {kind_label.lower()} visitors")
    with c2:
        section("2. Foreigner vs National (national totals)")
        bar(national, "Year", ["Foreigner", "National"], "Visitor type by year", barmode="stack")

    c1, c2 = st.columns(2)
    with c1:
        section("3. Foreigner share of total (%)")
        national["Foreigner Share %"] = (national["Foreigner"] / national["Total"] * 100).round(1)
        line(national, "Year", "Foreigner Share %", "Foreigner share over time")
    with c2:
        section(f"4. Top 10 {kind_label.lower()} by total visitors")
        bar(top10.reset_index(), "Place", "Total", f"Top 10 {kind_label.lower()} (all years combined)")

    c1, c2 = st.columns(2)
    with c1:
        section("5. Province comparison (total visitors, all years)")
        if province_rows:
            prov_df = df[df["Place"].isin(province_rows)].groupby("Place")[["Foreigner", "National"]].sum()
            prov_df["Total"] = prov_df["Foreigner"] + prov_df["National"]
            prov_df = prov_df.sort_values("Total", ascending=False)
            bar(prov_df.reset_index(), "Place", "Total", "Total visitors by province")
    with c2:
        section(f"6. Select a specific {kind_label.lower()}")
        sel = st.selectbox(kind_label, site_rows, key=f"{kind_label}_sel")
        sub = df[df["Place"] == sel].sort_values("Year")
        bar(sub, "Year", ["Foreigner", "National"], f"{sel} — visitors by year", barmode="group")

    c1, c2 = st.columns(2)
    with c1:
        section("7. Foreigner vs National — overall share (pie)")
        totals = national[["Foreigner", "National"]].sum()
        pie(totals.index, totals.values, "Foreigner vs National (all years, national total)")
    with c2:
        section("8. Year-over-year % change (national total)")
        yoy = national.copy()
        yoy["YoY %"] = yoy["Total"].pct_change() * 100
        bar(yoy, "Year", "YoY %", "YoY change in total visitors", color="YoY %", color_continuous_scale="RdYlGn")

    section(f"9. Heatmap — top 15 {kind_label.lower()} × year (total visitors)")
    top15_names = totals_by_site.sort_values("Total", ascending=False).head(15).index.tolist()
    heat = df[df["Place"].isin(top15_names)].copy()
    heat["Total"] = heat["Foreigner"] + heat["National"]
    pivot = heat.pivot_table(index="Place", columns="Year", values="Total", aggfunc="sum")
    pivot = pivot.loc[top15_names]
    fig = px.imshow(pivot, aspect="auto", color_continuous_scale="OrRd", labels=dict(color="Visitors"))
    st.plotly_chart(fig, use_container_width=True)

    section("10. Full data table")
    st.dataframe(df.sort_values(["Place", "Year"]), use_container_width=True, hide_index=True)


def render_museum_multiyear():
    df = L.load_museum_visitors_multiyear()
    _render_visitor_multiyear(df, "Museums")


def render_heritage_multiyear():
    df = L.load_heritage_visitors_multiyear()
    _render_visitor_multiyear(df, "Sites")


# ============================================================
# 3. Museum visitors — monthly
# ============================================================

def render_museum_monthly():
    year = st.selectbox("Year", [2022, 2023, 2024, 2025], key="mm_year")
    df = L.load_museum_monthly(year)
    all_places = sorted(df["Place"].unique().tolist())

    national = df[df["Place"].str.upper() == "PAKISTAN"]
    if national.empty:
        national = df.groupby("Month")[["Foreigner", "National"]].sum().reset_index()
        month_order = df["Month"].unique().tolist()
        national["Month"] = pd.Categorical(national["Month"], categories=month_order, ordered=True)
        national = national.sort_values("Month")
    national = national.copy()
    national["Total"] = national["Foreigner"] + national["National"]
    peak = national.loc[national["Total"].idxmax()]
    low = national.loc[national["Total"].idxmin()]

    kpi_row([
        (f"Total visitors ({year})", f"{int(national['Total'].sum()):,}", None),
        ("Peak month", str(peak["Month"]), f"{int(peak['Total']):,}"),
        ("Quietest month", str(low["Month"]), f"{int(low['Total']):,}"),
        ("Sites tracked", str(df["Place"].nunique()), None),
        ("Foreigner share", f"{national['Foreigner'].sum()/national['Total'].sum()*100:.1f}%", None),
    ])
    st.divider()

    c1, c2 = st.columns(2)
    with c1:
        section("1. Monthly total visitors (with trend line)")
        line(national, "Month", "Total", f"Total museum visitors by month — {year}")
    with c2:
        section("2. Foreigner vs National by month")
        bar(national, "Month", ["Foreigner", "National"], "Visitor type by month", barmode="stack")

    section("3. Select a specific place")
    sel = st.selectbox("Place", all_places, index=all_places.index("PAKISTAN") if "PAKISTAN" in all_places else 0, key="mm_place")
    sub = df[df["Place"] == sel]
    bar(sub, "Month", ["Foreigner", "National"], f"{sel} — visitors by month ({year})", barmode="group")

    c1, c2 = st.columns(2)
    with c1:
        section("4. Cumulative visitors through the year")
        national["Cumulative"] = national["Total"].cumsum()
        line(national, "Month", "Cumulative", "Cumulative visitors", trend=False)
    with c2:
        section("5. Foreigner share of total (%) by month")
        national["Foreigner Share %"] = (national["Foreigner"] / national["Total"] * 100).round(1)
        line(national, "Month", "Foreigner Share %", "Foreigner share by month")

    top_places = df.groupby("Place")[["Foreigner", "National"]].sum()
    top_places["Total"] = top_places["Foreigner"] + top_places["National"]
    top_places = top_places[top_places.index.str.upper() != "PAKISTAN"].sort_values("Total", ascending=False)

    c1, c2 = st.columns(2)
    with c1:
        section("6. Top 10 places (total across the year)")
        bar(top_places.head(10).reset_index(), "Place", "Total", "Top 10 places")
    with c2:
        section("7. Share of annual visitors by month (pie)")
        pie(national["Month"], national["Total"], f"Monthly share of {year} total")

    c1, c2 = st.columns(2)
    with c1:
        section("8. Seasonal index (month vs monthly average)")
        avg = national["Total"].mean()
        national["Index"] = (national["Total"] / avg * 100).round(1)
        bar(national, "Month", "Index", "Seasonal index (100 = average month)",
            color="Index", color_continuous_scale="RdYlGn")
    with c2:
        section("9. Heatmap — top 10 places × month")
        top10_names = top_places.head(10).index.tolist()
        heat = df[df["Place"].isin(top10_names)].copy()
        heat["Total"] = heat["Foreigner"] + heat["National"]
        pivot = heat.pivot_table(index="Place", columns="Month", values="Total", aggfunc="sum")
        month_order = df["Month"].unique().tolist()
        pivot = pivot.reindex(columns=month_order).loc[top10_names]
        fig = px.imshow(pivot, aspect="auto", color_continuous_scale="OrRd", labels=dict(color="Visitors"))
        st.plotly_chart(fig, use_container_width=True)

    section("10. Full data table")
    st.dataframe(df, use_container_width=True, hide_index=True)


# ============================================================
# 4. Zoo statistics
# ============================================================

def render_zoo_statistics():
    zoos = L.load_zoo_statistics()
    zoo_name = st.selectbox("Zoo", list(zoos.keys()), key="zoo_sel")
    df = zoos[zoo_name].copy()
    df["Total Visitors"] = df["Adult Visitors"] + df["Minor Visitors"]
    df["Profit"] = df["Total Income"] - df["Total Expenditure"]
    df["Profit Margin %"] = (df["Profit"] / df["Total Income"].replace(0, np.nan) * 100).round(1)
    latest, prev = df.iloc[-1], df.iloc[-2] if len(df) > 1 else df.iloc[-1]

    kpi_row([
        ("Total visitors (latest)", f"{int(latest['Total Visitors']):,}", str(latest["Year"])),
        ("Total income (latest)", f"PKR {latest['Total Income']:,.0f}", None),
        ("Total expenditure (latest)", f"PKR {latest['Total Expenditure']:,.0f}", None),
        ("Profit margin", f"{latest['Profit Margin %']:.1f}%" if pd.notna(latest['Profit Margin %']) else "N/A", None),
        ("Animals + birds (latest)", f"{int(latest['No. of Animals'] + latest['No. of Birds']):,}", None),
    ])
    st.divider()

    c1, c2 = st.columns(2)
    with c1:
        section("1. Total visitors over time (with trend line)")
        line(df, "Year", "Total Visitors", f"{zoo_name} — total visitors")
    with c2:
        section("2. Adult vs Minor visitors")
        bar(df, "Year", ["Adult Visitors", "Minor Visitors"], "Visitor breakdown", barmode="group")

    c1, c2 = st.columns(2)
    with c1:
        section("3. Income vs Expenditure (with trend lines)")
        line(df, "Year", ["Total Income", "Total Expenditure"], "Income vs Expenditure")
    with c2:
        section("4. Profit margin % over time")
        line(df, "Year", "Profit Margin %", "Profit margin (%)")

    c1, c2 = st.columns(2)
    with c1:
        section("5. Adult vs Minor share (pie, all years)")
        shares = df[["Adult Visitors", "Minor Visitors"]].sum()
        pie(shares.index, shares.values, "Visitor type share")
    with c2:
        section("6. Animals vs Birds over time")
        line(df, "Year", ["No. of Animals", "No. of Birds"], "Collection size over time")

    c1, c2 = st.columns(2)
    with c1:
        section("7. Year-over-year % change in visitors")
        yoy = df.copy()
        yoy["YoY %"] = yoy["Total Visitors"].pct_change() * 100
        bar(yoy, "Year", "YoY %", "YoY change", color="YoY %", color_continuous_scale="RdYlGn")
    with c2:
        section("8. Revenue per visitor")
        df["Revenue/Visitor"] = (df["Total Income"] / df["Total Visitors"]).round(1)
        line(df, "Year", "Revenue/Visitor", "Income per visitor (PKR)")

    section("9. Compare total visitors across all 4 zoos")
    comp = []
    for name, d in zoos.items():
        dd = d.copy()
        dd["Total Visitors"] = dd["Adult Visitors"] + dd["Minor Visitors"]
        dd["Zoo"] = name
        comp.append(dd[["Year", "Zoo", "Total Visitors"]])
    comp_df = pd.concat(comp)
    fig = px.line(comp_df, x="Year", y="Total Visitors", color="Zoo", markers=True, color_discrete_sequence=PALETTE)
    for _tr in fig.data:
        _isp = '%' in str(_tr.name or '') or '%' in (fig.layout.yaxis.title.text or '')
        _tr.update(texttemplate='%{y:,.1f}%' if _isp else '%{y:,.0f}', textposition='top center', mode='lines+markers+text')
    st.plotly_chart(fig, use_container_width=True)

    section("10. Full data table")
    st.dataframe(df, use_container_width=True, hide_index=True)


# ============================================================
# 5. Tourist arrivals by region
# ============================================================

def render_tourist_region():
    df = L.load_tourist_by_region()
    years = [c for c in df.columns if c != "Region"]
    no_total = df[df["Region"] != "Total"].copy()
    total_row = df[df["Region"] == "Total"]

    latest_year, first_year = years[-1], years[0]
    latest_total = total_row[latest_year].iloc[0] if not total_row.empty else no_total[latest_year].sum()
    first_total = total_row[first_year].iloc[0] if not total_row.empty else no_total[first_year].sum()
    top_region = no_total.set_index("Region")[latest_year].idxmax()

    kpi_row([
        (f"Total arrivals ({latest_year})", f"{int(latest_total):,}", None),
        (f"Growth since {first_year}", f"{(latest_total-first_total)/first_total*100:+.1f}%", None),
        ("Top region", top_region, f"{int(no_total.set_index('Region')[latest_year].max()):,}"),
        ("Regions tracked", str(len(no_total)), None),
        ("YoY change (latest)", f"{(total_row[years[-1]].iloc[0]-total_row[years[-2]].iloc[0])/total_row[years[-2]].iloc[0]*100:+.1f}%" if not total_row.empty else "N/A", None),
    ])
    st.divider()

    c1, c2 = st.columns(2)
    with c1:
        section("1. Arrivals by region over time (with trend lines)")
        melt = no_total.melt(id_vars="Region", value_vars=years, var_name="Year", value_name="Arrivals")
        fig = px.line(melt, x="Year", y="Arrivals", color="Region", markers=True, color_discrete_sequence=PALETTE)
        for _tr in fig.data:
            _isp = '%' in str(_tr.name or '') or '%' in (fig.layout.yaxis.title.text or '')
            _tr.update(texttemplate='%{y:,.1f}%' if _isp else '%{y:,.0f}', textposition='top center', mode='lines+markers+text')
        st.plotly_chart(fig, use_container_width=True)
    with c2:
        section(f"2. Region share of arrivals — {latest_year}")
        shares = no_total.set_index("Region")[latest_year]
        pie(shares.index, shares.values, f"Share by region — {latest_year}")

    c1, c2 = st.columns(2)
    with c1:
        section(f"3. Region ranking — {latest_year}")
        bar(no_total.sort_values(latest_year, ascending=False), "Region", latest_year, f"Arrivals by region — {latest_year}")
    with c2:
        section("4. Total arrivals trend (national, with trend line)")
        if not total_row.empty:
            tot_melt = total_row.melt(id_vars="Region", value_vars=years, var_name="Year", value_name="Arrivals")
            line(tot_melt, "Year", "Arrivals", "Total tourist arrivals")

    c1, c2 = st.columns(2)
    with c1:
        section(f"5. Growth % by region ({first_year} → {latest_year})")
        growth = no_total.copy()
        growth["Growth %"] = ((growth[latest_year] - growth[first_year]) / growth[first_year] * 100).round(1)
        bar(growth.sort_values("Growth %"), "Region", "Growth %", "Growth since first year", color="Growth %", color_continuous_scale="RdYlGn")
    with c2:
        section("6. Stacked composition over time")
        melt = no_total.melt(id_vars="Region", value_vars=years, var_name="Year", value_name="Arrivals")
        fig = px.area(melt, x="Year", y="Arrivals", color="Region", color_discrete_sequence=PALETTE)
        for _tr in fig.data:
            _isp = '%' in str(_tr.name or '') or '%' in (fig.layout.yaxis.title.text or '')
            _tr.update(texttemplate='%{y:,.1f}%' if _isp else '%{y:,.0f}', textposition='top center', mode='lines+text')
        st.plotly_chart(fig, use_container_width=True)

    section("7. Heatmap — region × year")
    pivot = no_total.set_index("Region")[years]
    fig = px.imshow(pivot, aspect="auto", color_continuous_scale="OrRd", labels=dict(color="Arrivals"))
    st.plotly_chart(fig, use_container_width=True)

    c1, c2 = st.columns(2)
    with c1:
        section("8. Average annual share by region")
        avg_share = (no_total.set_index("Region")[years].sum(axis=1) / no_total[years].sum().sum() * 100).sort_values(ascending=False)
        bar(x=avg_share.index, y=avg_share.values, title="% of all arrivals (avg across years)")
    with c2:
        section("9. Year-over-year % change (total)")
        if not total_row.empty:
            yoy = pd.DataFrame({"Year": years})
            vals = total_row[years].iloc[0].values
            yoy["YoY %"] = pd.Series(vals).pct_change().values * 100
            bar(yoy, "Year", "YoY %", "YoY change in total arrivals", color="YoY %", color_continuous_scale="RdYlGn")

    section("10. Full data table")
    st.dataframe(df, use_container_width=True, hide_index=True)


# ============================================================
# 6. Tourist arrivals by mode
# ============================================================

def render_tourist_mode():
    df = L.load_tourist_by_mode()
    gdf = L.load_tourist_by_gender()
    modes = ["Air", "Sea", "Land", "Railway"]
    latest, prev = df.iloc[-1], df.iloc[-2]

    kpi_row([
        ("Total arrivals (latest)", f"{int(latest['Total']):,}", str(int(latest["Year"]))),
        ("Air share", f"{latest['Air']/latest['Total']*100:.1f}%", None),
        ("Land share", f"{latest['Land']/latest['Total']*100:.1f}%", None),
        ("YoY change", f"{(latest['Total']-prev['Total'])/prev['Total']*100:+.1f}%", None),
        (f"Growth since {int(df.iloc[0]['Year'])}", f"{(latest['Total']-df.iloc[0]['Total'])/df.iloc[0]['Total']*100:+.1f}%", None),
    ])
    st.divider()

    c1, c2 = st.columns(2)
    with c1:
        section("1. Arrivals by mode over time (stacked)")
        melt = df.melt(id_vars="Year", value_vars=modes, var_name="Mode", value_name="Arrivals")
        bar(melt, "Year", "Arrivals", "Tourist arrivals by mode", color="Mode", barmode="stack")
    with c2:
        section("2. Mode share (all years combined)")
        shares = df[modes].sum()
        pie(shares.index, shares.values, "Mode share — all years")

    c1, c2 = st.columns(2)
    with c1:
        section("3. Total arrivals trend (with trend line)")
        line(df, "Year", "Total", "Total tourist arrivals")
    with c2:
        section("4. Air vs Land arrivals (with trend lines)")
        line(df, "Year", ["Air", "Land"], "Air vs Land arrivals")

    c1, c2 = st.columns(2)
    with c1:
        section("5. Year-over-year % change")
        yoy = df.copy()
        yoy["YoY %"] = df["Total"].pct_change() * 100
        bar(yoy, "Year", "YoY %", "YoY change in total arrivals", color="YoY %", color_continuous_scale="RdYlGn")
    with c2:
        section("6. Air share of total over time (%)")
        df["Air Share %"] = (df["Air"] / df["Total"] * 100).round(1)
        line(df, "Year", "Air Share %", "Air travel share over time")

    c1, c2 = st.columns(2)
    with c1:
        section("7. Gender breakdown over time (thousands)")
        bar(gdf, "Year", ["Male (000s)", "Female (000s)"], "Tourist arrivals by gender", barmode="group")
    with c2:
        section("8. Gender share (all years combined)")
        gshares = gdf[["Male (000s)", "Female (000s)"]].sum()
        pie(gshares.index, gshares.values, "Gender share — all years")

    c1, c2 = st.columns(2)
    with c1:
        section("9. Male share of total over time (%)")
        gdf["Male Share %"] = (gdf["Male (000s)"] / (gdf["Male (000s)"] + gdf["Female (000s)"]) * 100).round(1)
        line(gdf, "Year", "Male Share %", "Male share of tourist arrivals")
    with c2:
        section("10. Full data tables")
        st.caption("Arrivals by mode")
        st.dataframe(df, use_container_width=True, hide_index=True)
        st.caption("Arrivals by gender (thousands)")
        st.dataframe(gdf, use_container_width=True, hide_index=True)