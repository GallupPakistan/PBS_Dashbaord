import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import warnings

warnings.filterwarnings("ignore")
import loaders as L
import crime_analytics as CA
import tourism_analytics as TA
import health_analytics as HA
import media_analytics as MA
import education_analytics as EA
import chart_helpers as CH

CH.reset_counter()

st.set_page_config(page_title="PBS Social Statistics Dashboard", layout="wide", page_icon="📊")

st.markdown("""
<style>
  #MainMenu, footer {visibility: hidden;}
  .block-container {padding-top: 1.2rem; padding-bottom: 2rem; max-width: 1320px;}

  .pbs-header {
      background: linear-gradient(120deg, #14532d 0%, #1d6b3f 55%, #2c7a4d 100%);
      border-radius: 14px; padding: 22px 28px; margin-bottom: 1.2rem;
      color: #f5f7f3; box-shadow: 0 2px 10px rgba(20,83,45,0.18);
  }
  .pbs-header h1 {font-size: 22px; margin: 0 0 4px 0; font-weight: 650; color: #ffffff;}
  .pbs-header p {font-size: 13px; margin: 0; color: #dfe9dd; opacity: 0.9;}

  [data-testid="stMetric"] {
      background: #ffffff; border: 1px solid #e5e4e0; border-left: 4px solid #2c7a4d;
      border-radius: 8px; padding: 12px 14px 8px 14px; box-shadow: 0 1px 3px rgba(0,0,0,0.05);
  }
  [data-testid="stMetricLabel"] {font-size: 12.5px; color: #6b6b66;}
  [data-testid="stMetricValue"] {font-size: 21px; color: #1d3a2a;}
  h4 {margin-top: 0.3rem !important; margin-bottom: 0.6rem !important; color: #26362c;
      border-left: 3px solid #2c7a4d; padding-left: 8px;}

  /* Top-level category tabs */
  .stTabs [data-baseweb="tab-list"] {gap: 4px; border-bottom: 2px solid #e5e4e0;}
  .stTabs [data-baseweb="tab"] {
      height: 42px; padding: 0 18px; border-radius: 8px 8px 0 0; font-size: 14.5px; font-weight: 550;
      background: #f1efe8; color: #55534c;
  }
  .stTabs [aria-selected="true"] {background: #2c7a4d !important; color: #ffffff !important;}

  /* Dataset pill selector (radio, horizontal) */
  div[data-testid="stRadio"] > div[role="radiogroup"] {gap: 6px; flex-wrap: wrap;}
  div[data-testid="stRadio"] label {
      background: #f6f7f4; border: 1px solid #dfe0da; border-radius: 20px;
      padding: 5px 14px 5px 10px; font-size: 13px;
  }
  div[data-testid="stRadio"] label:has(input:checked) {
      background: #e4efe6; border-color: #2c7a4d; font-weight: 600;
  }

  .pbs-pagetitle {font-size: 18px; font-weight: 650; color: #1d3a2a; margin: 0.6rem 0 0.8rem 0;}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="pbs-header">
  <h1>📊 Pakistan Bureau of Statistics — Social Statistics Dashboard</h1>
  <p>Source: pbs.gov.pk/social-statistics-2 · data cleaned & consolidated across 31 published files</p>
</div>
""", unsafe_allow_html=True)

CATEGORY_ICONS = {
    "Crime": "🔴",
    "Tourism & Heritage": "🏛️",
    "Health": "🏥",
    "Media & Telecom": "📺",
    "Education": "🎓",
}

CATEGORIES = {
    "Crime": [
        "Crime by type — annual trend",
        "Crime by type & province",
        "Cyber crime",
        "Month-wise crime",
        "District-wise crime",
        "Traffic accidents — yearly",
        "Appeals & petitions (High Courts)",
    ],
    "Tourism & Heritage": [
        "Museum visitors — multi-year (2015-2019)",
        "Heritage site visitors — multi-year (2015-2019)",
        "Museum visitors — monthly",
        "Zoo statistics",
        "Tourist arrivals by region",
        "Tourist arrivals by mode",
    ],
    "Health": [
        "Health institutes & beds",
        "Immunization — yearly",
        "Immunization — monthly",
        "HIV/AIDS treatment centres",
        "Traffic accidents — monthly (Islamabad)",
        "Veterinary registrations — monthly",
        "TB by province",
        "Dental doctors (data note below)",
    ],
    "Media & Telecom": [
        "Documentary films",
        "Dramas & plays",
        "TV sets by province",
        "Telecom subscribers — monthly",
    ],
    "Education": [
        "Schools",
        "Colleges",
        "Universities",
    ],
}

PALETTE = CA.PALETTE


import chart_helpers as CH
bar = CH.bar


line = CH.line


def pie(df=None, names=None, values=None, title="", hole=0.45):
    if df is not None:
        fig = px.pie(df, names=names, values=values, title=title, hole=hole, color_discrete_sequence=PALETTE)
    else:
        fig = px.pie(names=names, values=values, title=title, hole=hole, color_discrete_sequence=PALETTE)
    fig.update_traces(textinfo="label+percent", textposition="inside")
    st.plotly_chart(fig, use_container_width=True)


def render_dataset(dataset):
    # ============ CRIME ============
    if dataset == "Crime by type — annual trend":
        CA.render_crime_annual()
    elif dataset == "Crime by type & province":
        CA.render_crime_province()
    elif dataset == "Cyber crime":
        CA.render_cyber_crime()
    elif dataset == "Month-wise crime":
        CA.render_month_wise()
    elif dataset == "District-wise crime":
        CA.render_district()
    elif dataset == "Traffic accidents — yearly":
        CA.render_traffic_yearly()
    elif dataset == "Appeals & petitions (High Courts)":
        CA.render_appeals()

    # ============ TOURISM & HERITAGE ============
    elif dataset == "Museum visitors — multi-year (2015-2019)":
        TA.render_museum_multiyear()

    elif dataset == "Heritage site visitors — multi-year (2015-2019)":
        TA.render_heritage_multiyear()

    elif dataset == "Museum visitors — monthly":
        TA.render_museum_monthly()

    elif dataset == "Zoo statistics":
        TA.render_zoo_statistics()

    elif dataset == "Tourist arrivals by region":
        TA.render_tourist_region()

    elif dataset == "Tourist arrivals by mode":
        TA.render_tourist_mode()

    # ============ HEALTH ============
    elif dataset == "Health institutes & beds":
        HA.render_health_institutes()

    elif dataset == "Immunization — yearly":
        HA.render_immunization_yearly()

    elif dataset == "Immunization — monthly":
        HA.render_immunization_monthly()

    elif dataset == "HIV/AIDS treatment centres":
        HA.render_hiv()

    elif dataset == "Traffic accidents — monthly (Islamabad)":
        HA.render_traffic_monthly()

    elif dataset == "Veterinary registrations — monthly":
        HA.render_veterinary_monthly()

    elif dataset == "TB by province":
        HA.render_tb()

    elif dataset == "Dental doctors (data note below)":
        HA.render_hospitals_by_province()

    # ============ MEDIA & TELECOM ============
    elif dataset == "Documentary films":
        MA.render_documentary_films()

    elif dataset == "Dramas & plays":
        MA.render_dramas_plays()

    elif dataset == "TV sets by province":
        MA.render_tv_sets()

    elif dataset == "Telecom subscribers — monthly":
        MA.render_telecom_monthly()

    # ============ EDUCATION ============
    elif dataset == "Schools":
        EA.render_schools()

    elif dataset == "Colleges":
        EA.render_colleges()

    elif dataset == "Universities":
        EA.render_universities()


tabs = st.tabs([f"{CATEGORY_ICONS[c]}  {c}" for c in CATEGORIES])
for tab, category in zip(tabs, CATEGORIES.keys()):
    with tab:
        dataset = st.radio(
            f"nav_{category}", CATEGORIES[category],
            horizontal=True, label_visibility="collapsed", key=f"radio_{category}",
        )
        st.markdown(f'<div class="pbs-pagetitle">{dataset}</div>', unsafe_allow_html=True)
        render_dataset(dataset)

st.divider()
st.caption("Built for internal use — data cleaned from PBS published Excel files. Some files had inconsistent "
           "formats, single-year snapshots, or mislabeled content; see notes on individual tabs where relevant.")
