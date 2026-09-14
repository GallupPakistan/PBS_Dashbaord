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


# ============================================================
# 1. Crime by type — annual trend
# ============================================================

def render_crime_annual():
    df = L.load_crime_annual()
    crime_cols = [c for c in df.columns if c not in ("Year", "All Reported")]
    latest, prev = df.iloc[-1], df.iloc[-2]
    first = df.iloc[0]
    cagr = ((latest["All Reported"] / first["All Reported"]) ** (1 / (latest["Year"] - first["Year"])) - 1) * 100

    kpi_row([
        ("Total reported (latest)", f"{int(latest['All Reported']):,}", f"{int(latest['Year'])}"),
        ("YoY change", f"{(latest['All Reported']-prev['All Reported'])/prev['All Reported']*100:+.1f}%", None),
        (f"{int(first['Year'])}\u2013{int(latest['Year'])} CAGR", f"{cagr:.1f}%/yr", None),
        ("Peak year", f"{int(df.loc[df['All Reported'].idxmax(),'Year'])}", f"{int(df['All Reported'].max()):,}"),
        ("Most common category", max(crime_cols, key=lambda c: df[c].sum()), None),
    ])
    st.divider()

    c1, c2 = st.columns(2)
    with c1:
        section("1. Total reported crimes over time")
        fig = px.line(df, x="Year", y="All Reported", markers=True, color_discrete_sequence=[PALETTE[0]])
        for _tr in fig.data:
            if 'lines' in str(_tr.mode or '') and len(_tr.x) <= 12:
                _isp = '%' in str(_tr.name or '') or '%' in (fig.layout.yaxis.title.text or '')
                _tr.update(texttemplate='%{y:,.1f}%' if _isp else '%{y:,.0f}', textposition='top center', mode='lines+markers+text')
        fig.add_scatter(x=df["Year"], y=df["All Reported"].rolling(3).mean(), mode="lines",
                         name="3-yr avg", line=dict(dash="dash", color=PALETTE[1]))
        st.plotly_chart(fig, use_container_width=True)
    with c2:
        section("2. Year-over-year % change")
        yoy = df.copy()
        yoy["YoY %"] = df["All Reported"].pct_change() * 100
        fig = px.bar(yoy, x="Year", y="YoY %", color="YoY %", color_continuous_scale="RdYlGn_r")
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

    c1, c2 = st.columns(2)
    with c1:
        section("3. Composition over time — % of total (stacked area)")
        pct_df = df[crime_cols].div(df["All Reported"], axis=0) * 100
        pct_df["Year"] = df["Year"]
        melt = pct_df.melt(id_vars="Year", value_vars=crime_cols, var_name="Type", value_name="Share %")
        fig = px.area(melt, x="Year", y="Share %", color="Type", color_discrete_sequence=PALETTE)
        fig.update_layout(yaxis=dict(ticksuffix="%"))
        st.plotly_chart(fig, use_container_width=True)
    with c2:
        section(f"4. Share of total — {int(latest['Year'])}")
        shares = latest[crime_cols]
        fig = px.pie(names=shares.index, values=shares.values, hole=0.45, color_discrete_sequence=PALETTE)
        fig.update_traces(textinfo='label+percent', textposition='inside')
        st.plotly_chart(fig, use_container_width=True)

    section("5. Individual crime type trends (select to compare)")
    selected = st.multiselect("Crime types", crime_cols, default=["Murder", "Robbery", "Burglary", "Cattle theft"], key="ca_sel")
    if selected:
        melt = df.melt(id_vars="Year", value_vars=selected, var_name="Type", value_name="Count")
        fig = px.line(melt, x="Year", y="Count", color="Type", markers=True, color_discrete_sequence=PALETTE)
        for _tr in fig.data:
            if 'lines' in str(_tr.mode or '') and len(_tr.x) <= 12:
                _isp = '%' in str(_tr.name or '') or '%' in (fig.layout.yaxis.title.text or '')
                _tr.update(texttemplate='%{y:,.1f}%' if _isp else '%{y:,.0f}', textposition='top center', mode='lines+markers+text')
        st.plotly_chart(fig, use_container_width=True)

    c1, c2 = st.columns(2)
    with c1:
        section("6. Heatmap — crime type × year")
        pivot = df.set_index("Year")[crime_cols].T
        fig = px.imshow(pivot, aspect="auto", color_continuous_scale="OrRd", labels=dict(color="Count"))
        st.plotly_chart(fig, use_container_width=True)
    with c2:
        section("7. Growth since 2000 (indexed, base=100)")
        idx = df[crime_cols].div(df[crime_cols].iloc[0]) * 100
        idx["Year"] = df["Year"]
        melt = idx.melt(id_vars="Year", value_vars=crime_cols, var_name="Type", value_name="Index")
        fig = px.line(melt, x="Year", y="Index", color="Type", color_discrete_sequence=PALETTE)
        for _tr in fig.data:
            if 'lines' in str(_tr.mode or '') and len(_tr.x) <= 12:
                _isp = '%' in str(_tr.name or '') or '%' in (fig.layout.yaxis.title.text or '')
                _tr.update(texttemplate='%{y:,.1f}%' if _isp else '%{y:,.0f}', textposition='top center', mode='lines+markers+text')
        fig.add_hline(y=100, line_dash="dot", line_color="gray")
        st.plotly_chart(fig, use_container_width=True)

    c1, c2 = st.columns(2)
    with c1:
        section("8. Total growth by type (first vs latest year)")
        growth = pd.DataFrame({
            "Type": crime_cols,
            "Growth %": [(df[c].iloc[-1] - df[c].iloc[0]) / df[c].iloc[0] * 100 for c in crime_cols]
        }).sort_values("Growth %")
        fig = px.bar(growth, x="Growth %", y="Type", orientation="h",
                     color="Growth %", color_continuous_scale="RdYlGn_r")
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
    with c2:
        section("9. Ranking — average annual share by type")
        avg_share = (df[crime_cols].sum() / df["All Reported"].sum() * 100).sort_values(ascending=False)
        fig = px.bar(x=avg_share.values, y=avg_share.index, orientation="h",
                     labels={"x": "% of all reported crime (avg)", "y": ""}, color_discrete_sequence=[PALETTE[2]])
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

    section("10. Full data table with computed YoY %")
    show = df.copy()
    show["YoY % (Total)"] = df["All Reported"].pct_change().mul(100).round(1)
    st.dataframe(show, use_container_width=True, hide_index=True)


# ============================================================
# 2. Crime by type & province
# ============================================================

def render_crime_province():
    data = L.load_crime_by_province()
    years = sorted(data.keys(), reverse=True)
    year = st.selectbox("Year", years, key="cp_year")
    df = data[year]
    provinces = [c for c in df.columns if c not in ("Offence", "Pakistan")]
    prov_totals = df[provinces].sum().sort_values(ascending=False)
    top_offence = df.loc[df[provinces].sum(axis=1).idxmax(), "Offence"]

    kpi_row([
        ("Provinces/regions covered", str(len(provinces)), None),
        ("Highest-crime region", prov_totals.index[0], f"{int(prov_totals.iloc[0]):,}"),
        ("Lowest-crime region", prov_totals.index[-1], f"{int(prov_totals.iloc[-1]):,}"),
        ("Most reported offence", top_offence, None),
        ("Offence types tracked", str(len(df)), None),
    ])
    st.divider()

    c1, c2 = st.columns(2)
    with c1:
        section("1. Total crimes by province/region (ranked)")
        fig = px.bar(x=prov_totals.index, y=prov_totals.values, color=prov_totals.index,
                     color_discrete_sequence=PALETTE, labels={"x": "", "y": "Total reported"})
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
    with c2:
        section("2. Share of national total by province")
        fig = px.pie(names=prov_totals.index, values=prov_totals.values, hole=0.45, color_discrete_sequence=PALETTE)
        fig.update_traces(textinfo='label+percent', textposition='inside')
        st.plotly_chart(fig, use_container_width=True)

    c1, c2 = st.columns(2)
    with c1:
        section("3. Crime type by province (grouped)")
        fig = px.bar(df, x="Offence", y=provinces, barmode="group", color_discrete_sequence=PALETTE)
        fig.update_xaxes(tickangle=-35)
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
    with c2:
        section("4. Composition (100% stacked) by province")
        share_df = df.set_index("Offence")[provinces]
        share_pct = share_df.div(share_df.sum(axis=0), axis=1) * 100
        melt = share_pct.reset_index().melt(id_vars="Offence", var_name="Province", value_name="Share %")
        fig = px.bar(melt, x="Province", y="Share %", color="Offence", color_discrete_sequence=PALETTE)
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

    section("5. Heatmap — offence type × province")
    pivot = df.set_index("Offence")[provinces]
    fig = px.imshow(pivot, aspect="auto", color_continuous_scale="OrRd", labels=dict(color="Count"))
    st.plotly_chart(fig, use_container_width=True)

    c1, c2 = st.columns(2)
    with c1:
        section("6. Top offence per province")
        top_per_prov = {p: df.loc[df[p].idxmax(), "Offence"] for p in provinces}
        top_df = pd.DataFrame({"Province": top_per_prov.keys(), "Top offence": top_per_prov.values()})
        st.dataframe(top_df, use_container_width=True, hide_index=True)
    with c2:
        section("7. Punjab vs Sindh — direct comparison")
        if "Punjab" in df.columns and "Sindh" in df.columns:
            fig = px.bar(df, x="Offence", y=["Punjab", "Sindh"], barmode="group", color_discrete_sequence=PALETTE)
            fig.update_xaxes(tickangle=-35)
            orient = fig.data[0].orientation if fig.data else 'v'
            tmpl = '%{x:,.0f}' if orient == 'h' else '%{y:,.0f}'
            fig.update_traces(texttemplate=tmpl, textposition='outside')
            fig.update_layout(uniformtext_minsize=8, uniformtext_mode='hide')
            st.plotly_chart(fig, use_container_width=True)

    section("8. Offence mix — treemap (province → offence)")
    tree = df.melt(id_vars="Offence", value_vars=provinces, var_name="Province", value_name="Count")
    tree = tree[tree["Count"] > 0]
    fig = px.treemap(tree, path=["Province", "Offence"], values="Count", color_discrete_sequence=PALETTE)
    st.plotly_chart(fig, use_container_width=True)

    c1, c2 = st.columns(2)
    with c1:
        section("9. Offence type ranking (national total)")
        off_total = df.set_index("Offence")[provinces].sum(axis=1).sort_values(ascending=False)
        fig = px.bar(x=off_total.values, y=off_total.index, orientation="h", color_discrete_sequence=[PALETTE[3]])
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
    with c2:
        section("10. Smaller regions comparison (Islamabad / GB / AJK / Railways)")
        small = [p for p in provinces if p in ("Islamabad", "G.B", "AJK", "Railways")]
        if small:
            fig = px.bar(df, x="Offence", y=small, barmode="group", color_discrete_sequence=PALETTE)
            fig.update_xaxes(tickangle=-35)
            orient = fig.data[0].orientation if fig.data else 'v'
            tmpl = '%{x:,.0f}' if orient == 'h' else '%{y:,.0f}'
            fig.update_traces(texttemplate=tmpl, textposition='outside')
            fig.update_layout(uniformtext_minsize=8, uniformtext_mode='hide')
            st.plotly_chart(fig, use_container_width=True)

    st.dataframe(df, use_container_width=True, hide_index=True)


# ============================================================
# 3. Cyber crime
# ============================================================

def render_cyber_crime():
    df = L.load_cyber_crime()
    df_sorted = df.sort_values("Total", ascending=False)
    total = int(df["Total"].sum())
    male_pct = df["Male"].sum() / (df["Male"].sum() + df["Female"].sum() + df["Transgender"].sum()) * 100

    kpi_row([
        ("Total complaints (2018\u2013Aug 2025)", f"{total:,}", None),
        ("Top category", df_sorted.iloc[0]["Crime Type"], f"{int(df_sorted.iloc[0]['Total']):,}"),
        ("Male share", f"{male_pct:.0f}%", None),
        ("Female share", f"{df['Female'].sum()/(df['Male'].sum()+df['Female'].sum()+df['Transgender'].sum())*100:.0f}%", None),
        ("Categories tracked", str(len(df)), None),
    ])
    st.divider()

    c1, c2 = st.columns(2)
    with c1:
        section("1. Complaints by type (ranked)")
        fig = px.bar(df_sorted, x="Total", y="Crime Type", orientation="h", color_discrete_sequence=[PALETTE[0]])
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
    with c2:
        section("2. Share of total complaints")
        fig = px.pie(df, names="Crime Type", values="Total", hole=0.45, color_discrete_sequence=PALETTE)
        fig.update_traces(textinfo='label+percent', textposition='inside')
        st.plotly_chart(fig, use_container_width=True)

    c1, c2 = st.columns(2)
    with c1:
        section("3. Gender breakdown by type (stacked)")
        melt = df.melt(id_vars="Crime Type", value_vars=["Male", "Female", "Transgender"], var_name="Gender", value_name="Count")
        fig = px.bar(melt, x="Crime Type", y="Count", color="Gender", color_discrete_sequence=PALETTE)
        fig.update_xaxes(tickangle=-35)
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
    with c2:
        section("4. Gender composition (100% stacked)")
        gdf = df.set_index("Crime Type")[["Male", "Female", "Transgender"]]
        gpct = gdf.div(gdf.sum(axis=1), axis=0) * 100
        melt = gpct.reset_index().melt(id_vars="Crime Type", var_name="Gender", value_name="Share %")
        fig = px.bar(melt, x="Crime Type", y="Share %", color="Gender", color_discrete_sequence=PALETTE)
        fig.update_xaxes(tickangle=-35)
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

    c1, c2 = st.columns(2)
    with c1:
        section("5. Male vs Female — direct comparison")
        fig = px.bar(df_sorted, x="Crime Type", y=["Male", "Female"], barmode="group", color_discrete_sequence=PALETTE)
        fig.update_xaxes(tickangle=-35)
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
    with c2:
        section("6. Treemap of all complaint categories")
        fig = px.treemap(df, path=["Crime Type"], values="Total", color_discrete_sequence=PALETTE)
        st.plotly_chart(fig, use_container_width=True)

    c1, c2 = st.columns(2)
    with c1:
        section("7. Top 5 categories — cumulative % of total")
        cum = df_sorted.head(8).copy()
        cum["Cumulative %"] = cum["Total"].cumsum() / total * 100
        fig = go.Figure()
        fig.add_bar(x=cum["Crime Type"], y=cum["Total"], name="Total", marker_color=PALETTE[0],
                    texttemplate="%{y:,.0f}", textposition="outside")
        fig.add_scatter(x=cum["Crime Type"], y=cum["Cumulative %"], name="Cumulative %", yaxis="y2",
                         line=dict(color=PALETTE[1]), mode="lines+markers+text",
                         texttemplate="%{y:,.1f}%", textposition="top center")
        fig.update_layout(yaxis2=dict(overlaying="y", side="right", range=[0, 100]))
        fig.update_xaxes(tickangle=-35)
        st.plotly_chart(fig, use_container_width=True)
    with c2:
        section("8. Male-to-Female ratio by type")
        ratio = df.copy()
        ratio["Female_safe"] = ratio["Female"].replace(0, float("nan"))
        ratio["M:F ratio"] = (ratio["Male"] / ratio["Female_safe"]).round(1)
        fig = px.bar(ratio.sort_values("M:F ratio", ascending=False), x="Crime Type", y="M:F ratio", color_discrete_sequence=[PALETTE[4]])
        fig.update_xaxes(tickangle=-35)
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

    section("9. Transgender complaints — where they occur")
    tg = df[df["Transgender"] > 0].sort_values("Transgender", ascending=False)
    if len(tg):
        fig = px.bar(tg, x="Crime Type", y="Transgender", color_discrete_sequence=[PALETTE[5]])
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
    else:
        st.info("No transgender-attributed complaints recorded in this dataset.")

    section("10. Full data table")
    st.dataframe(df, use_container_width=True, hide_index=True)


# ============================================================
# 4. Month-wise crime (2022)
# ============================================================

def render_month_wise():
    data = L.load_month_wise_crime()
    year = st.selectbox("Year", sorted(data.keys(), reverse=True), key="mw_year")
    df = data[year]
    months = [c for c in df.columns if c not in ("Crime Type", "Total")]
    total_by_month = df[months].sum()
    peak_month = total_by_month.idxmax()
    top_type = df.loc[df["Total"].idxmax(), "Crime Type"]

    kpi_row([
        (f"Total crimes ({year})", f"{int(df['Total'].sum()):,}", None),
        ("Peak month", peak_month, f"{int(total_by_month.max()):,}"),
        ("Quietest month", total_by_month.idxmin(), f"{int(total_by_month.min()):,}"),
        ("Top crime type", top_type, f"{int(df['Total'].max()):,}"),
        ("Categories tracked", str(len(df)), None),
    ])
    st.divider()

    c1, c2 = st.columns(2)
    with c1:
        section("1. Total crimes by month (seasonality)")
        fig = px.bar(x=months, y=total_by_month.values, color=total_by_month.values,
                     color_continuous_scale="OrRd", labels={"x": "", "y": "Count"})
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
    with c2:
        section("2. Cumulative crimes through the year")
        fig = px.line(x=months, y=total_by_month.cumsum().values, markers=True, color_discrete_sequence=[PALETTE[0]])
        for _tr in fig.data:
            if 'lines' in str(_tr.mode or '') and len(_tr.x) <= 12:
                _isp = '%' in str(_tr.name or '') or '%' in (fig.layout.yaxis.title.text or '')
                _tr.update(texttemplate='%{y:,.1f}%' if _isp else '%{y:,.0f}', textposition='top center', mode='lines+markers+text')
        st.plotly_chart(fig, use_container_width=True)

    section("3. Compare specific crime types across months")
    selected = st.multiselect("Crime types", df["Crime Type"].tolist(), default=df["Crime Type"].tolist()[:3], key="mw_sel")
    if selected:
        sub = df[df["Crime Type"].isin(selected)]
        melt = sub.melt(id_vars="Crime Type", value_vars=months, var_name="Month", value_name="Count")
        fig = px.line(melt, x="Month", y="Count", color="Crime Type", markers=True, color_discrete_sequence=PALETTE)
        for _tr in fig.data:
            if 'lines' in str(_tr.mode or '') and len(_tr.x) <= 12:
                _isp = '%' in str(_tr.name or '') or '%' in (fig.layout.yaxis.title.text or '')
                _tr.update(texttemplate='%{y:,.1f}%' if _isp else '%{y:,.0f}', textposition='top center', mode='lines+markers+text')
        st.plotly_chart(fig, use_container_width=True)

    c1, c2 = st.columns(2)
    with c1:
        section("4. Heatmap — crime type × month")
        pivot = df.set_index("Crime Type")[months]
        fig = px.imshow(pivot, aspect="auto", color_continuous_scale="OrRd")
        st.plotly_chart(fig, use_container_width=True)
    with c2:
        section("5. Total for the year by crime type")
        fig = px.bar(df.sort_values("Total", ascending=False), x="Crime Type", y="Total", color_discrete_sequence=[PALETTE[1]])
        fig.update_xaxes(tickangle=-35)
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

    c1, c2 = st.columns(2)
    with c1:
        section("6. Share of annual total by month")
        fig = px.pie(names=months, values=total_by_month.values, hole=0.45, color_discrete_sequence=PALETTE)
        fig.update_traces(textinfo='label+percent', textposition='inside')
        st.plotly_chart(fig, use_container_width=True)
    with c2:
        section("7. Seasonal index (month value vs monthly average)")
        avg = total_by_month.mean()
        idx = (total_by_month / avg * 100).round(1)
        fig = px.bar(x=months, y=idx.values, color=idx.values, color_continuous_scale="RdYlGn_r",
                     labels={"x": "", "y": "Index (100 = avg)"})
        fig.add_hline(y=100, line_dash="dot")
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

    c1, c2 = st.columns(2)
    with c1:
        section("8. Volatility — which crime types swing most month to month")
        vol = df.set_index("Crime Type")[months].std(axis=1).sort_values(ascending=False)
        fig = px.bar(x=vol.values, y=vol.index, orientation="h", color_discrete_sequence=[PALETTE[2]])
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
    with c2:
        section("9. Peak month per crime type")
        peak = df.set_index("Crime Type")[months].idxmax(axis=1)
        st.dataframe(peak.reset_index().rename(columns={0: "Peak month"}), use_container_width=True, hide_index=True)

    section("10. Full monthly data table")
    st.dataframe(df, use_container_width=True, hide_index=True)


# ============================================================
# 5. District-wise crime
# ============================================================

def render_district():
    province = st.selectbox("Province / territory", ["Islamabad", "Balochistan", "KP", "Punjab", "Sindh"], key="dc_prov")
    df = L.load_district_crime(province)
    metrics = [c for c in df.columns if c != "District"]

    if len(df) <= 1:
        st.info(f"{province} has a single reporting unit (city-level total) in this dataset — district breakdown not applicable.")
        st.dataframe(df, use_container_width=True, hide_index=True)
        row = df.iloc[0]
        section("Crime type breakdown")
        fig = px.bar(x=metrics, y=[row[m] for m in metrics], color_discrete_sequence=[PALETTE[0]])
        fig.update_xaxes(tickangle=-35)
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
        return

    top10 = df.sort_values("All Reported", ascending=False).head(10)
    bottom10 = df.sort_values("All Reported", ascending=True).head(10)

    kpi_row([
        ("Districts covered", str(len(df)), None),
        ("Highest-crime district", top10.iloc[0]["District"], f"{int(top10.iloc[0]['All Reported']):,}"),
        ("Lowest-crime district", bottom10.iloc[0]["District"], f"{int(bottom10.iloc[0]['All Reported']):,}"),
        ("Province total", f"{int(df['All Reported'].sum()):,}", None),
        ("Average per district", f"{int(df['All Reported'].mean()):,}", None),
    ])
    st.divider()

    c1, c2 = st.columns(2)
    with c1:
        section("1. Top 10 districts by total reported crime")
        fig = px.bar(top10, x="All Reported", y="District", orientation="h", color_discrete_sequence=[PALETTE[1]])
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
    with c2:
        section("2. Bottom 10 districts by total reported crime")
        fig = px.bar(bottom10, x="All Reported", y="District", orientation="h", color_discrete_sequence=[PALETTE[2]])
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

    c1, c2 = st.columns(2)
    with c1:
        section("3. Share of provincial total (top 10 districts)")
        fig = px.pie(top10, names="District", values="All Reported", hole=0.45, color_discrete_sequence=PALETTE)
        fig.update_traces(textinfo='label+percent', textposition='inside')
        st.plotly_chart(fig, use_container_width=True)
    with c2:
        section("4. Distribution of crime totals across districts")
        fig = px.histogram(df, x="All Reported", nbins=15, color_discrete_sequence=[PALETTE[3]])
        st.plotly_chart(fig, use_container_width=True)

    section("5. Crime-type breakdown for a selected district")
    dsel = st.selectbox("District", df["District"].tolist(), key="dc_district")
    row = df[df["District"] == dsel].iloc[0]
    other_metrics = [m for m in metrics if m != "All Reported"]
    fig = px.bar(x=other_metrics, y=[row[m] for m in other_metrics], color_discrete_sequence=[PALETTE[4]])
    fig.update_xaxes(tickangle=-35)
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

    c1, c2 = st.columns(2)
    with c1:
        section("6. Composition — top 10 districts (100% stacked)")
        comp_cols = [m for m in other_metrics if df[m].sum() > 0][:6]
        share_df = top10.set_index("District")[comp_cols]
        share_pct = share_df.div(share_df.sum(axis=1), axis=0) * 100
        melt = share_pct.reset_index().melt(id_vars="District", var_name="Type", value_name="Share %")
        fig = px.bar(melt, x="District", y="Share %", color="Type", color_discrete_sequence=PALETTE)
        fig.update_xaxes(tickangle=-35)
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
    with c2:
        section("7. Murder vs Robbery across districts (scatter)")
        if "Murder" in df.columns and "Robbery" in df.columns:
            fig = px.scatter(df, x="Murder", y="Robbery", hover_name="District", color_discrete_sequence=[PALETTE[5]], size="All Reported")
            st.plotly_chart(fig, use_container_width=True)

    section("8. Heatmap — top 15 districts × crime type")
    heat_cols = [m for m in other_metrics if df[m].sum() > 0][:8]
    heat = df.sort_values("All Reported", ascending=False).head(15).set_index("District")[heat_cols]
    fig = px.imshow(heat, aspect="auto", color_continuous_scale="OrRd")
    st.plotly_chart(fig, use_container_width=True)

    c1, c2 = st.columns(2)
    with c1:
        section("9. Full district ranking")
        rank = df.sort_values("All Reported", ascending=False).reset_index(drop=True)
        rank.index += 1
        st.dataframe(rank[["District", "All Reported"]], use_container_width=True)
    with c2:
        section("10. Full data table (all crime types)")
        st.dataframe(df, use_container_width=True, hide_index=True)


# ============================================================
# 6. Traffic accidents — yearly
# ============================================================

def render_traffic_yearly():
    data = L.load_traffic_accidents_yearly()
    region = st.selectbox("Region", list(data.keys()), key="ty_region")
    df = data[region].copy()
    df["Fatality Rate %"] = (df["Killed"] / df["Total Accidents"] * 100).round(2)
    df["Trend (linear)"] = np.poly1d(np.polyfit(range(len(df)), df["Total Accidents"], 1))(range(len(df)))
    latest, prev = df.iloc[-1], df.iloc[-2]

    kpi_row([
        (f"Total accidents ({region}, latest)", f"{int(latest['Total Accidents']):,}", str(latest["Year"])),
        ("Killed (latest)", f"{int(latest['Killed']):,}", None),
        ("Injured (latest)", f"{int(latest['Injured']):,}", None),
        ("Fatality rate", f"{latest['Fatality Rate %']:.1f}%", None),
        ("YoY change (accidents)", f"{(latest['Total Accidents']-prev['Total Accidents'])/prev['Total Accidents']*100:+.1f}%", None),
    ])
    st.divider()

    c1, c2 = st.columns(2)
    with c1:
        section("1. Total accidents over time (with trend line)")
        fig = px.line(df, x="Year", y="Total Accidents", markers=True, color_discrete_sequence=[PALETTE[0]])
        for _tr in fig.data:
            if 'lines' in str(_tr.mode or '') and len(_tr.x) <= 12:
                _isp = '%' in str(_tr.name or '') or '%' in (fig.layout.yaxis.title.text or '')
                _tr.update(texttemplate='%{y:,.1f}%' if _isp else '%{y:,.0f}', textposition='top center', mode='lines+markers+text')
        fig.add_scatter(x=df["Year"], y=df["Trend (linear)"], mode="lines", name="Trend",
                         line=dict(dash="dash", color=PALETTE[1]))
        st.plotly_chart(fig, use_container_width=True)
    with c2:
        section("2. Fatal vs Non-fatal accidents")
        melt = df.melt(id_vars="Year", value_vars=["Fatal", "Non-Fatal"], var_name="Type", value_name="Count")
        fig = px.bar(melt, x="Year", y="Count", color="Type", color_discrete_sequence=PALETTE)
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

    c1, c2 = st.columns(2)
    with c1:
        section("3. Killed vs Injured over time (with trend lines)")
        fig = px.line(df, x="Year", y=["Killed", "Injured"], markers=True, color_discrete_sequence=PALETTE)
        for _tr in fig.data:
            if 'lines' in str(_tr.mode or '') and len(_tr.x) <= 12:
                _isp = '%' in str(_tr.name or '') or '%' in (fig.layout.yaxis.title.text or '')
                _tr.update(texttemplate='%{y:,.1f}%' if _isp else '%{y:,.0f}', textposition='top center', mode='lines+markers+text')
        for col, color in zip(["Killed", "Injured"], PALETTE[2:4]):
            tr = np.poly1d(np.polyfit(range(len(df)), df[col], 1))(range(len(df)))
            fig.add_scatter(x=df["Year"], y=tr, mode="lines", name=f"{col} trend",
                             line=dict(dash="dot", color=color), showlegend=True)
        st.plotly_chart(fig, use_container_width=True)
    with c2:
        section("4. Fatality rate trend (Killed / Total accidents)")
        fig = px.line(df, x="Year", y="Fatality Rate %", markers=True, color_discrete_sequence=[PALETTE[1]])
        for _tr in fig.data:
            if 'lines' in str(_tr.mode or '') and len(_tr.x) <= 12:
                _isp = '%' in str(_tr.name or '') or '%' in (fig.layout.yaxis.title.text or '')
                _tr.update(texttemplate='%{y:,.1f}%' if _isp else '%{y:,.0f}', textposition='top center', mode='lines+markers+text')
        tr = np.poly1d(np.polyfit(range(len(df)), df["Fatality Rate %"], 1))(range(len(df)))
        fig.add_scatter(x=df["Year"], y=tr, mode="lines", name="Trend", line=dict(dash="dash", color=PALETTE[4]))
        st.plotly_chart(fig, use_container_width=True)

    c1, c2 = st.columns(2)
    with c1:
        section("5. Year-over-year % change in accidents")
        yoy = df.copy()
        yoy["YoY %"] = df["Total Accidents"].pct_change() * 100
        fig = px.bar(yoy, x="Year", y="YoY %", color="YoY %", color_continuous_scale="RdYlGn_r")
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
    with c2:
        section("6. Vehicles involved over time (with trend line)")
        fig = px.area(df, x="Year", y="Total Vehicles Involved", color_discrete_sequence=[PALETTE[2]])
        for _tr in fig.data:
            if len(_tr.x) <= 12:
                _isp = '%' in str(_tr.name or '') or '%' in (fig.layout.yaxis.title.text or '')
                _tr.update(texttemplate='%{y:,.1f}%' if _isp else '%{y:,.0f}', textposition='top center', mode='lines+text')
        tr = np.poly1d(np.polyfit(range(len(df)), df["Total Vehicles Involved"], 1))(range(len(df)))
        fig.add_scatter(x=df["Year"], y=tr, mode="lines", name="Trend", line=dict(dash="dash", color=PALETTE[1]))
        st.plotly_chart(fig, use_container_width=True)

    c1, c2 = st.columns(2)
    with c1:
        section("7. Injured-per-accident ratio (with trend line)")
        df["Injured/Accident"] = (df["Injured"] / df["Total Accidents"]).round(2)
        fig = px.line(df, x="Year", y="Injured/Accident", markers=True, color_discrete_sequence=[PALETTE[3]])
        for _tr in fig.data:
            if 'lines' in str(_tr.mode or '') and len(_tr.x) <= 12:
                _isp = '%' in str(_tr.name or '') or '%' in (fig.layout.yaxis.title.text or '')
                _tr.update(texttemplate='%{y:,.1f}%' if _isp else '%{y:,.0f}', textposition='top center', mode='lines+markers+text')
        tr = np.poly1d(np.polyfit(range(len(df)), df["Injured/Accident"], 1))(range(len(df)))
        fig.add_scatter(x=df["Year"], y=tr, mode="lines", name="Trend", line=dict(dash="dash", color=PALETTE[5]))
        st.plotly_chart(fig, use_container_width=True)
    with c2:
        section("8. Accidents vs Vehicles involved (correlation)")
        fig = px.scatter(df, x="Total Vehicles Involved", y="Total Accidents", trendline="ols",
                          hover_data=["Year"], color_discrete_sequence=[PALETTE[4]])
        st.plotly_chart(fig, use_container_width=True)

    c1, c2 = st.columns(2)
    with c1:
        section("9. 3-year moving average — total accidents")
        df["3yr MA"] = df["Total Accidents"].rolling(3).mean()
        fig = go.Figure()
        fig.add_bar(x=df["Year"], y=df["Total Accidents"], name="Actual", marker_color=PALETTE[0],
                    texttemplate="%{y:,.0f}", textposition="outside")
        fig.add_scatter(x=df["Year"], y=df["3yr MA"], name="3-yr MA", line=dict(color=PALETTE[1]))
        fig.add_scatter(x=df["Year"], y=df["Trend (linear)"], name="Linear trend", line=dict(dash="dash", color=PALETTE[3]))
        st.plotly_chart(fig, use_container_width=True)
    with c2:
        section("10. Full data table")
        st.dataframe(df.drop(columns=["Trend (linear)"]), use_container_width=True, hide_index=True)


# ============================================================
# 7. Appeals & petitions (High Courts)
# ============================================================

def render_appeals():
    df = L.load_appeals_petitions()
    df["Disposal Rate %"] = (df["Disposed off"] / df["Total for Disposal"] * 100).round(1)
    df["Clearance Ratio"] = (df["Disposed off"] / df["Fresh Registered"]).round(2)
    latest, prev = df.iloc[-1], df.iloc[-2]

    kpi_row([
        ("Pending (latest)", f"{int(latest['Pending']):,}", str(int(latest["Year"]))),
        ("Fresh registered (latest)", f"{int(latest['Fresh Registered']):,}", None),
        ("Disposed off (latest)", f"{int(latest['Disposed off']):,}", None),
        ("Disposal rate", f"{latest['Disposal Rate %']:.1f}%", None),
        ("YoY change (pending)", f"{(latest['Pending']-prev['Pending'])/prev['Pending']*100:+.1f}%", None),
    ])
    st.divider()

    c1, c2 = st.columns(2)
    with c1:
        section("1. Pending appeals/petitions over time (with trend line)")
        fig = px.line(df, x="Year", y="Pending", markers=True, color_discrete_sequence=[PALETTE[0]])
        for _tr in fig.data:
            if 'lines' in str(_tr.mode or '') and len(_tr.x) <= 12:
                _isp = '%' in str(_tr.name or '') or '%' in (fig.layout.yaxis.title.text or '')
                _tr.update(texttemplate='%{y:,.1f}%' if _isp else '%{y:,.0f}', textposition='top center', mode='lines+markers+text')
        tr = np.poly1d(np.polyfit(range(len(df)), df["Pending"], 1))(range(len(df)))
        fig.add_scatter(x=df["Year"], y=tr, mode="lines", name="Trend", line=dict(dash="dash", color=PALETTE[1]))
        st.plotly_chart(fig, use_container_width=True)
    with c2:
        section("2. Fresh registered vs Disposed off (with trend lines)")
        fig = px.line(df, x="Year", y=["Fresh Registered", "Disposed off"], markers=True, color_discrete_sequence=PALETTE)
        for _tr in fig.data:
            if 'lines' in str(_tr.mode or '') and len(_tr.x) <= 12:
                _isp = '%' in str(_tr.name or '') or '%' in (fig.layout.yaxis.title.text or '')
                _tr.update(texttemplate='%{y:,.1f}%' if _isp else '%{y:,.0f}', textposition='top center', mode='lines+markers+text')
        for col, color in zip(["Fresh Registered", "Disposed off"], PALETTE[2:4]):
            tr = np.poly1d(np.polyfit(range(len(df)), df[col], 1))(range(len(df)))
            fig.add_scatter(x=df["Year"], y=tr, mode="lines", name=f"{col} trend", line=dict(dash="dot", color=color))
        st.plotly_chart(fig, use_container_width=True)

    c1, c2 = st.columns(2)
    with c1:
        section("3. Disposal rate trend (%)")
        fig = px.line(df, x="Year", y="Disposal Rate %", markers=True, color_discrete_sequence=[PALETTE[1]])
        for _tr in fig.data:
            if 'lines' in str(_tr.mode or '') and len(_tr.x) <= 12:
                _isp = '%' in str(_tr.name or '') or '%' in (fig.layout.yaxis.title.text or '')
                _tr.update(texttemplate='%{y:,.1f}%' if _isp else '%{y:,.0f}', textposition='top center', mode='lines+markers+text')
        fig.add_hline(y=100, line_dash="dot", line_color="gray")
        st.plotly_chart(fig, use_container_width=True)
    with c2:
        section("4. Clearance ratio (Disposed / Fresh registered)")
        fig = px.bar(df, x="Year", y="Clearance Ratio", color="Clearance Ratio", color_continuous_scale="RdYlGn")
        fig.add_hline(y=1, line_dash="dot", line_color="gray")
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

    c1, c2 = st.columns(2)
    with c1:
        section("5. Case flow composition (stacked area)")
        melt = df.melt(id_vars="Year", value_vars=["Disposed off", "Pending", "Transferred"], var_name="Status", value_name="Count")
        fig = px.area(melt, x="Year", y="Count", color="Status", color_discrete_sequence=PALETTE)
        for _tr in fig.data:
            if len(_tr.x) <= 12:
                _isp = '%' in str(_tr.name or '') or '%' in (fig.layout.yaxis.title.text or '')
                _tr.update(texttemplate='%{y:,.1f}%' if _isp else '%{y:,.0f}', textposition='top center', mode='lines+text')
        st.plotly_chart(fig, use_container_width=True)
    with c2:
        section("6. Year-over-year change in backlog (Pending)")
        yoy = df.copy()
        yoy["YoY %"] = df["Pending"].pct_change() * 100
        fig = px.bar(yoy, x="Year", y="YoY %", color="YoY %", color_continuous_scale="RdYlGn_r")
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

    c1, c2 = st.columns(2)
    with c1:
        section("7. Fresh registered vs Disposed (scatter)")
        fig = px.scatter(df, x="Fresh Registered", y="Disposed off", hover_data=["Year"],
                          trendline="ols", color_discrete_sequence=[PALETTE[2]])
        st.plotly_chart(fig, use_container_width=True)
    with c2:
        section("8. Total for disposal over time")
        fig = px.area(df, x="Year", y="Total for Disposal", color_discrete_sequence=[PALETTE[3]])
        for _tr in fig.data:
            if len(_tr.x) <= 12:
                _isp = '%' in str(_tr.name or '') or '%' in (fig.layout.yaxis.title.text or '')
                _tr.update(texttemplate='%{y:,.1f}%' if _isp else '%{y:,.0f}', textposition='top center', mode='lines+text')
        st.plotly_chart(fig, use_container_width=True)

    c1, c2 = st.columns(2)
    with c1:
        section("9. Cumulative pending trend")
        df["Cumulative Pending Change"] = df["Pending"].diff().cumsum()
        fig = px.line(df, x="Year", y="Cumulative Pending Change", markers=True, color_discrete_sequence=[PALETTE[4]])
        for _tr in fig.data:
            if 'lines' in str(_tr.mode or '') and len(_tr.x) <= 12:
                _isp = '%' in str(_tr.name or '') or '%' in (fig.layout.yaxis.title.text or '')
                _tr.update(texttemplate='%{y:,.1f}%' if _isp else '%{y:,.0f}', textposition='top center', mode='lines+markers+text')
        st.plotly_chart(fig, use_container_width=True)
    with c2:
        section("10. Full data table")
        st.dataframe(df, use_container_width=True, hide_index=True)