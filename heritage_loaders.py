"""Loaders for PBS museum / heritage-site visitor data (2015-2025).

Sources
-------
Annual  : No.-of-Visitor-at-Archaeological-Museum.xlsx
          No.-of-Visitor-of-Heritage-site.xlsx
          Each file holds TWO stacked blocks: 2015-2019 and 2020-2024.
Monthly : web-Data-2022 / Web-data-2023 / Web-Data-2024 / Web-Data-2025 (sheet "Museum")
          Each sheet holds Museums first, then Heritage Sites; 2025 = Jan-Apr only.

Place names are spelled differently from file to file (typos, "Birth House" vs
"House Museum", "Khawara" vs "Khewra" ...), so every name is mapped to ONE
canonical name before anything is ranked or compared.
"""
import re
import pandas as pd
import streamlit as st

DATA_DIR = "data"

ANNUAL_FILES = {
    "museum": f"{DATA_DIR}/No.-of-Visitor-at-Archaeological-Museum.xlsx",
    "heritage": f"{DATA_DIR}/No.-of-Visitor-of-Heritage-site.xlsx",
}
MONTHLY_FILES = {
    2022: f"{DATA_DIR}/web-Data-2022.xlsx",
    2023: f"{DATA_DIR}/Web-data-2023.xlsx",
    2024: f"{DATA_DIR}/Web-Data-2024.xlsx",
    2025: f"{DATA_DIR}/Web-Data-2025.xlsx",
}
MONTHS = ["January", "February", "March", "April", "May", "June", "July",
          "August", "September", "October", "November", "December"]

# The three Lahore sites that PBS stops reporting (blank) from mid-2023.
LAHORE_TRIO = {"Lahore Fort (Shahi Qila)", "Shalamar Garden, Lahore", "Jahangir's Tomb, Lahore"}

REGION_MAP = {
    "pakistan": "Pakistan", "punjab": "Punjab", "sindh": "Sindh",
    "khyber pakhtunkhwa": "Khyber Pakhtunkhwa", "khyber pakthunkhwa": "Khyber Pakhtunkhwa",
    "balochistan": "Balochistan", "islamabad": "Islamabad",
}

# (regex on lower-case name, canonical name) — first match wins
MUSEUM_RULES = [
    (r"natural history", "Pakistan Museum of Natural History"),
    (r"lok virsa", "Lok Virsa Heritage Museum"),
    (r"monument museum", "Pakistan Monument Museum"),
    (r"railway", "Pakistan Railway Heritage Museum"),
    (r"allama iqbal library", "Allama Iqbal Library & Museum, Sialkot"),
    (r"allama iqbal museum", "Allama Iqbal Museum (Javed Manzil), Lahore"),
    (r"lahore museum", "Lahore Museum"),
    (r"lahore fort", "Lahore Fort (Shahi Qila)"),
    (r"taxila", "Taxila Museum"),
    (r"harappa", "Harappa Museum"),
    (r"khaw|khew", "Khewra Mines Museum (PMDC)"),
    (r"national museum", "National Museum of Pakistan, Karachi"),
    (r"sindh provincial", "Sindh Provincial Museum, Hyderabad"),
    (r"bhambore", "Bhambore Museum"),
    (r"moenjodaro|monejodaro|monjodaro|mohenjo", "Moenjodaro Museum"),
    (r"umarkot|umerkot", "Umarkot Museum"),
    (r"azam.*birth place", "Quaid-e-Azam Birth Place, Karachi"),
    (r"azam", "Quaid-e-Azam House Museum, Karachi"),
    (r"peshawar museum", "Peshawar Museum"),
    (r"saidu|sawat|swat", "Swat Museum (Saidu Sharif)"),
    (r"dir museum", "Dir Museum, Chakdara"),
    (r"hund", "Hund Museum, Swabi"),
    (r"kalasha", "Kalasha Dur Museum, Bumburet"),
    (r"chitral", "Chitral Museum"),
    (r"pushkalavati", "Pushkalavati Museum, Charsadda"),
    (r"bannu", "Bannu Museum"),
    (r"city museum", "City Museum (Gor Khatri), Peshawar"),
    (r"mardan museum", "Mardan Museum"),
    (r"balochistan|mehargarh|mehrgarh", "Balochistan Museum, Quetta"),
    (r"turbat", "Turbat Museum"),
    (r"gawader|gwadar", "Gwadar Fort Museum"),
]
HERITAGE_RULES = [
    (r"jahangir|jhangir", "Jahangir's Tomb, Lahore"),
    (r"shalamar", "Shalamar Garden, Lahore"),
    (r"lahore fort|royal fort", "Lahore Fort (Shahi Qila)"),
    (r"hiran|haran", "Hiran Minar & Tank, Sheikhupura"),
    (r"harappa", "Harappa"),
    (r"taxila", "Taxila"),
    (r"wah", "Mughal Garden, Wah Cantt"),
    (r"bhambore", "Bhambore"),
    (r"makli", "Makli Hill Monuments, Thatta"),
    (r"moenjodaro|monejodaro|monjodaro|mohenjo", "Moenjodaro"),
    (r"umarkot|umerkot", "Umarkot Fort"),
    (r"takht", "Takht-e-Bhai, Mardan"),
    (r"bukara|butkara", "Butkara Site, Swat"),
    (r"julian", "Julian Site, Haripur"),
    (r"sethi", "Sethi House, Peshawar"),
    (r"jamal garhi", "Jamal Garhi, Mardan"),
    (r"shehbaz", "Shehbaz Garhi, Mardan"),
    (r"ali mardan", "Ali Mardan Khan Villa, Peshawar"),
    (r"sadio|saido|saidu", "Saidu Sharif Stupa, Swat"),
    (r"mehmood|ghazni", "Mahmud Ghazni Mosque & Raja Gira Fort, Swat"),
    (r"barikot|bazira|bazaira", "Barikot (Bazira), Swat"),
    (r"bhamla", "Bhamla Site, Haripur"),
    (r"ashoka", "Ashoka Rock Edicts, Mansehra"),
    (r"ranigat", "Ranigat, Buner"),
    (r"jina wali", "Jina Wali Dheri, Haripur"),
    (r"jirgha", "Jirgha Hall, Sibi"),
    (r"residency", "Quaid Residency, Ziarat"),
]
RULES = {"museum": MUSEUM_RULES, "heritage": HERITAGE_RULES}


def canon(name, kind):
    """Return ('region', canonical_region) or ('site', canonical_site) or (None, None)."""
    s = re.sub(r"\s+", " ", str(name)).strip().strip(".").strip()
    low = s.lower()
    if low in REGION_MAP:
        return "region", REGION_MAP[low]
    for pat, nm in RULES[kind]:
        if re.search(pat, low):
            return "site", nm
    return None, None


def _num_pair(f_raw, n_raw):
    """Clean one Foreigner/National pair. '-'/'Nil' next to a real number = 0;
    '-', '…', 'Nil', '**' on both sides = not reported (NaN)."""
    f = pd.to_numeric(f_raw, errors="coerce")
    n = pd.to_numeric(n_raw, errors="coerce")
    dash = lambda v: isinstance(v, str) and v.strip() in {"-", "Nil", "nil"}
    if pd.isna(f) and dash(f_raw) and not pd.isna(n):
        f = 0.0
    if pd.isna(n) and dash(n_raw) and not pd.isna(f):
        n = 0.0
    return f, n


def _is_year(v):
    try:
        return 2000 <= int(float(v)) <= 2035
    except (TypeError, ValueError):
        return False


def _finish(sites, agg):
    sites = pd.DataFrame(sites)
    agg = pd.DataFrame(agg)
    for d in (sites, agg):
        d["Total"] = d[["Foreigner", "National"]].sum(axis=1, min_count=1)
    return sites, agg


# ---------------------------------------------------------------- annual
def _parse_annual(kind):
    df = pd.read_excel(ANNUAL_FILES[kind], header=None)
    header_rows = [i for i in range(len(df)) if _is_year(df.iloc[i, 1]) and not _is_year(df.iloc[i, 0])]
    sites, agg = [], []
    for h in header_rows:
        years, cols = [], []
        for c in range(1, df.shape[1], 2):
            if _is_year(df.iloc[h, c]):
                years.append(int(float(df.iloc[h, c])))
                cols.append(c)
        province = None
        for i in range(h + 3, len(df)):
            name = df.iloc[i, 0]
            vals = df.iloc[i, 1:1 + 2 * len(years)]
            if pd.isna(name) or vals.isna().all():
                break
            if i > h + 3 and _is_year(df.iloc[i, 1]):
                break
            typ, cn = canon(name, kind)
            if typ is None:
                raise ValueError(f"Unmapped place name in {kind} annual file: {name!r}")
            if typ == "region" and cn != "Pakistan":
                province = cn
            for yr, c in zip(years, cols):
                f, n = _num_pair(df.iloc[i, c], df.iloc[i, c + 1])
                if typ == "region":
                    agg.append({"Kind": kind, "Year": yr, "Region": cn, "Foreigner": f, "National": n})
                else:
                    sites.append({"Kind": kind, "Year": yr, "Province": province, "Place": cn,
                                  "Foreigner": f, "National": n})
    sites, agg = _finish(sites, agg)
    return sites, agg


# ---------------------------------------------------------------- monthly
def _parse_monthly_year(year):
    df = pd.read_excel(MONTHLY_FILES[year], sheet_name="Museum", header=None)
    kind = "museum"
    sites, agg = [], []
    i = 0
    while i < len(df):
        c0 = str(df.iloc[i, 0]).strip() if not pd.isna(df.iloc[i, 0]) else ""
        low = c0.lower()
        if low.startswith("visitors at"):
            kind = "heritage" if "heritage" in low else "museum"
        if low.startswith("area"):
            months = [str(m).strip() for m in df.iloc[i, 1:].tolist() if not pd.isna(m)]
            province = None
            j = i + 2
            while j < len(df):
                nm = df.iloc[j, 0]
                if pd.isna(nm):
                    break
                nm_s = str(nm).strip()
                if nm_s.lower().startswith(("note", "visitors at", "area", ".", "*", "source")):
                    break
                typ, cn = canon(nm_s, kind)
                if typ is None:
                    raise ValueError(f"Unmapped place name in {year} {kind}: {nm_s!r}")
                if typ == "region" and cn != "Pakistan":
                    province = cn
                for k, m in enumerate(months):
                    f, n = _num_pair(df.iloc[j, 1 + 2 * k], df.iloc[j, 2 + 2 * k])
                    if typ == "region":
                        agg.append({"Kind": kind, "Year": year, "Month": m, "Region": cn,
                                    "Foreigner": f, "National": n})
                    else:
                        sites.append({"Kind": kind, "Year": year, "Month": m, "Province": province,
                                      "Place": cn, "Foreigner": f, "National": n})
                j += 1
            i = j
        i += 1
    return _finish(sites, agg)


@st.cache_data
def load_annual(kind):
    """Annual visitors 2015-2024. Returns (sites_df, aggregates_df)."""
    sites, agg = _parse_annual(kind)
    # 2024 heritage: Lahore Fort / Shalamar / Jahangir are printed as 0 but the
    # monthly sheet shows them blank -> they were NOT REPORTED, not zero.
    if kind == "heritage":
        m = (sites["Year"] == 2024) & sites["Place"].isin(LAHORE_TRIO)
        sites.loc[m, ["Foreigner", "National", "Total"]] = float("nan")
    return sites, agg


@st.cache_data
def load_monthly():
    """Monthly visitors 2022-2025 (2025 = Jan-Apr). Returns (sites_df, aggregates_df)."""
    parts = [_parse_monthly_year(y) for y in MONTHLY_FILES]
    sites = pd.concat([p[0] for p in parts], ignore_index=True)
    agg = pd.concat([p[1] for p in parts], ignore_index=True)
    sites["Month"] = pd.Categorical(sites["Month"], categories=MONTHS, ordered=True)
    agg["Month"] = pd.Categorical(agg["Month"], categories=MONTHS, ordered=True)
    return sites, agg


@st.cache_data
def load_place_year(kind):
    """ONE place x year table, 2015 -> 2025, ready for trends and rankings.

    2015-2021 : PBS annual table.
    2022-2024 : sum of the 12 monthly sheets (the monthly sheets tie to the
                annual table for all but 3 place/year pairs where the annual
                table mis-splits Taxila / Lahore Fort / Wah Garden between
                two neighbouring rows).
    2025      : Jan-Apr only (the only months published so far).
    'Months' = months with a published figure (12 for annual-table years).
    """
    annual, _ = load_annual(kind)
    a = annual[annual["Year"] <= 2021][["Year", "Province", "Place", "Foreigner", "National"]].copy()
    a["Months"] = 12
    a["Basis"] = "Annual table"

    ms, _ = load_monthly()
    m = ms[ms["Kind"] == kind].copy()
    m["_rep"] = m["Total"].notna().astype(int)
    g = m.groupby(["Year", "Province", "Place"], observed=True).agg(
        Foreigner=("Foreigner", lambda s: s.sum(min_count=1)),
        National=("National", lambda s: s.sum(min_count=1)),
        Months=("_rep", "sum")).reset_index()
    g["Basis"] = g["Year"].map(lambda y: "Sum of months (Jan-Apr only)" if y == 2025 else "Sum of months")

    out = pd.concat([a, g], ignore_index=True)
    out["Total"] = out[["Foreigner", "National"]].sum(axis=1, min_count=1)
    out = out[out["Total"].notna() & (out["Months"] > 0)]
    return out.sort_values(["Year", "Total"], ascending=[True, False]).reset_index(drop=True)
