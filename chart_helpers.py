import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

PALETTE = ["#2C5F8A", "#C1440E", "#4C8C4A", "#8A5FC1", "#C19A2C",
           "#3A9BA0", "#B03A5B", "#6B6B6B", "#5B7C99", "#9C6B30"]

_counter = {"n": 0}


def reset_counter():
    """Call once at the top of each full app run so widget keys stay stable
    and collision-free across reruns (module-level state otherwise persists
    between Streamlit reruns since the module is only imported once)."""
    _counter["n"] = 0


def toggle_pct(df, y):
    """Lightweight Count/% toggle for charts that build their figure manually
    (e.g. with a custom trend overlay) and can't go through bar()/line().
    Returns (plot_df, is_pct) — use plot_df (not the original df) for plotting,
    and is_pct to decide the text/axis format."""
    y_cols = y if isinstance(y, list) else [y]
    already_pct = any("%" in str(c) for c in y_cols)
    if already_pct:
        return df, False
    _counter["n"] += 1
    wkey = f"tgl_{_counter['n']}"
    mode = st.radio("View as", ["Count", "%"], horizontal=True, key=wkey,
                     label_visibility="collapsed")
    if mode == "Count":
        return df, False
    plot_df = df.copy()
    if len(y_cols) > 1:
        row_sum = plot_df[y_cols].sum(axis=1).replace(0, float("nan"))
        for c in y_cols:
            plot_df[c] = (plot_df[c].astype(float) / row_sum * 100).round(1)
    else:
        vcol = y_cols[0]
        total = plot_df[vcol].sum()
        plot_df[vcol] = (plot_df[vcol].astype(float) / total * 100).round(1) if total else plot_df[vcol] * 0
    return plot_df, True


def bar(df=None, x=None, y=None, title="", tickangle=None, hline=None, **kw):
    """Bar chart with value labels, consistent everywhere in the dashboard:

    - If the value column is already a percentage/rate (name contains '%')
      it is shown as % — there's no meaningful 'count' version of a rate,
      so no toggle is offered.
    - If the value column is a plain count/magnitude, a Count / % toggle
      appears above the chart. '%' is computed live from the data as each
      bar's share of the chart's total (or, for multi-series bars, each
      series' share within its own category) — never guessed or hardcoded.
    - Correctly handles horizontal bars (orientation='h'), where the VALUE
      column is x and the CATEGORY column is y (reversed vs. vertical bars).
    - hline: optional y-value to draw a reference line at (e.g. 100 for an
      index baseline, 1 for a ratio baseline).
    """
    if df is None:
        df = pd.DataFrame({"_x": x, "_y": y})
        x, y = "_x", "_y"

    is_horizontal = kw.get("orientation") == "h"
    value_ref, cat_ref = (x, y) if is_horizontal else (y, x)

    is_multi = isinstance(value_ref, list)
    val_cols = value_ref if is_multi else [value_ref]
    already_pct = any("%" in str(c) for c in val_cols)
    show_toggle = not already_pct

    mode = "Count"
    if show_toggle:
        _counter["n"] += 1
        wkey = f"tgl_{_counter['n']}"
        mode = st.radio("View as", ["Count", "%"], horizontal=True, key=wkey,
                         label_visibility="collapsed")

    plot_df = df.copy()
    pct_active = False
    if show_toggle and mode == "%":
        pct_active = True
        if is_multi:
            row_sum = plot_df[val_cols].sum(axis=1).replace(0, float("nan"))
            for c in val_cols:
                plot_df[c] = (plot_df[c].astype(float) / row_sum * 100).round(1)
        else:
            vcol = val_cols[0]
            total = plot_df[vcol].sum()
            plot_df[vcol] = (plot_df[vcol].astype(float) / total * 100).round(1) if total else plot_df[vcol] * 0

    seq = kw.pop("color_discrete_sequence", PALETTE)
    fig = px.bar(plot_df, x=x, y=y, title=title, color_discrete_sequence=seq, **kw)
    orient = fig.data[0].orientation if fig.data else "v"
    axis_title = (fig.layout.xaxis.title.text or "") if orient == "h" else (fig.layout.yaxis.title.text or "")
    is_pct = pct_active or already_pct or "%" in axis_title

    n_traces = len(fig.data)
    if 1 < n_traces <= 4:
        for tr in fig.data:
            nm = tr.name or ""
            fmt = f"{nm}: %{{value:,.1f}}%" if is_pct else f"{nm}: %{{value:,.0f}}"
            tr.update(texttemplate=fmt, textposition="outside", cliponaxis=False)
    else:
        fmt = "%{value:,.1f}%" if is_pct else "%{value:,.0f}"
        fig.update_traces(texttemplate=fmt, textposition="outside", cliponaxis=False)

    fig.update_layout(uniformtext_minsize=8, uniformtext_mode="hide",
                       margin=dict(r=70, t=40) if orient == "h" else dict(t=40))
    if tickangle is not None:
        fig.update_xaxes(tickangle=tickangle)
    if hline is not None:
        fig.add_hline(y=hline, line_dash="dot", line_color="gray")
    st.plotly_chart(fig, use_container_width=True)


def line(df, x, y, title="", trend=True, **kw):
    """Line chart with the same Count/% toggle rule as bar():
    - Already-% columns are shown as % with no toggle.
    - Plain count columns (single series, or a list of series) get a
      Count/% toggle; % is each series' share within its own x-category.
    - Per-point data labels are only drawn when the chart is simple enough
      to stay readable (<=2 series and <=12 points) — dense multi-series
      trends rely on hover instead of cluttering the chart with text.
    - color-grouped charts (many categories) keep count-only, unlabeled-dense
      lines by design, since a per-row % split isn't well-defined there.
    """
    is_list = isinstance(y, list)
    y_cols = y if is_list else [y]
    already_pct = any("%" in str(c) for c in y_cols)
    has_color = "color" in kw
    show_toggle = not already_pct and not has_color

    mode = "Count"
    if show_toggle:
        _counter["n"] += 1
        wkey = f"tgl_{_counter['n']}"
        mode = st.radio("View as", ["Count", "%"], horizontal=True, key=wkey,
                         label_visibility="collapsed")

    plot_df = df.copy()
    pct_active = False
    if show_toggle and mode == "%":
        pct_active = True
        if is_list and len(y_cols) > 1:
            row_sum = plot_df[y_cols].sum(axis=1).replace(0, float("nan"))
            for c in y_cols:
                plot_df[c] = (plot_df[c].astype(float) / row_sum * 100).round(1)
        else:
            vcol = y_cols[0]
            total = plot_df[vcol].sum()
            plot_df[vcol] = (plot_df[vcol].astype(float) / total * 100).round(1) if total else plot_df[vcol] * 0

    seq = kw.pop("color_discrete_sequence", PALETTE)
    fig = px.line(plot_df, x=x, y=y, title=title, markers=True, color_discrete_sequence=seq, **kw)

    n_traces = len(fig.data)
    max_points = max((len(tr.x) for tr in fig.data), default=0)
    if n_traces <= 2 and max_points <= 12:
        for tr in fig.data:
            if "lines" in str(tr.mode or ""):
                is_pct = pct_active or already_pct or "%" in str(tr.name or "")
                tr.update(texttemplate="%{y:,.1f}%" if is_pct else "%{y:,.0f}",
                           textposition="top center", mode="lines+markers+text")

    if trend and not has_color:
        for i, col in enumerate(y_cols):
            yv = pd.to_numeric(plot_df[col], errors="coerce")
            if yv.notna().sum() >= 3:
                idx = list(range(len(plot_df)))
                coeffs = np.polyfit(idx, yv.fillna(yv.mean()), 1)
                tr_y = np.poly1d(coeffs)(idx)
                fig.add_scatter(x=plot_df[x], y=tr_y, mode="lines", name=f"{col} trend",
                                 line=dict(dash="dash", color=PALETTE[(i + 5) % len(PALETTE)]))

    fig.update_layout(uniformtext_minsize=7, uniformtext_mode="hide")
    st.plotly_chart(fig, use_container_width=True)