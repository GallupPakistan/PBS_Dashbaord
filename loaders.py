import pandas as pd
import re
import streamlit as st

DATA_DIR = "data"


def _clean_num(x):
    if isinstance(x, str):
        x = x.strip()
        if x in ('.. ', '..', '--', '-', 'Nil', 'NIL', '**', '', 'N/A'):
            return None
        x = x.replace(',', '')
        try:
            return float(x)
        except ValueError:
            return None
    return x


# ---------------- CRIME ----------------

@st.cache_data
def load_crime_annual():
    df = pd.read_excel(f"{DATA_DIR}/Crime-By-Types-annual.xlsx", header=None)
    header_row = 3
    cols = df.iloc[header_row].tolist()
    cols[1] = "Year"
    data = df.iloc[6:].copy()
    data.columns = df.iloc[header_row]
    data = data.iloc[:, 1:]
    data.columns = ["Year", "All Reported", "Murder", "Attempted Murder", "Kidnapping/Abduction",
                     "Dacoity", "Robbery", "Burglary", "Cattle theft", "Other theft", "Others"]
    data = data.dropna(subset=["Year"])
    data["Year"] = pd.to_numeric(data["Year"], errors='coerce')
    data = data.dropna(subset=["Year"])
    for c in data.columns[1:]:
        data[c] = pd.to_numeric(data[c], errors='coerce')
    data["Year"] = data["Year"].astype(int)
    return data.reset_index(drop=True)


@st.cache_data
def load_crime_by_province():
    """Returns dict {year: dataframe}. Crime-By-Types-Yearly.xlsx contains
    3 stacked year-blocks (2022, 2023, 2024). Province-Wise-Crime-data.xlsx
    is a duplicate of the 2022 block and is not used separately."""
    df = pd.read_excel(f"{DATA_DIR}/Crime-By-Types-Yearly.xlsx", header=None)
    year_rows = [i for i in range(len(df))
                 if isinstance(df.iloc[i, 0], (int, float)) and 2000 <= df.iloc[i, 0] <= 2030]
    cols = df.iloc[1].tolist()  # Offence, Punjab, Sindh, KP, Balochistan, Islamabad, Railways, G.B, AJK, Pakistan
    out = {}
    for yr_row in year_rows:
        yr = int(df.iloc[yr_row, 0])
        block = df.iloc[yr_row + 1: yr_row + 11].copy()
        block.columns = cols
        for c in cols[1:]:
            block[c] = pd.to_numeric(block[c], errors='coerce')
        block["Offence"] = block["Offence"].astype(str).str.strip()
        out[yr] = block.reset_index(drop=True)
    return out


@st.cache_data
def load_cyber_crime():
    df = pd.read_excel(f"{DATA_DIR}/Cyber-Crime-data.xlsx", header=None)
    data = df.iloc[3:].copy()
    data.columns = ["No", "Crime Type", "Male", "Female", "Transgender", "Total"]
    data["Crime Type"] = data["Crime Type"].fillna("Uncategorized")
    data = data.dropna(subset=["Total"])
    for c in ["Male", "Female", "Transgender", "Total"]:
        data[c] = pd.to_numeric(data[c], errors='coerce')
    data = data[data["Crime Type"].astype(str).str.strip().str.lower() != "total"]
    return data.reset_index(drop=True)


@st.cache_data
def load_month_wise_crime():
    """Returns dict {year: dataframe}. The source file bundles 3 years
    (2022, 2023, 2024) stacked as separate blocks."""
    df = pd.read_excel(f"{DATA_DIR}/Moth-wise-Crime-data.xlsx", header=None)
    months = ["January", "Feburary", "March", "April", "May", "June", "July",
              "August", "Septempber", "October", "November", "December", "Total"]
    header_rows = df.index[df[1] == "Year/Month"].tolist()
    years = [2022, 2023, 2024]
    out = {}
    for h, yr in zip(header_rows, years):
        block = df.iloc[h + 1: h + 10].copy()
        block = block.iloc[:, 1:]
        block.columns = ["Crime Type"] + months
        for c in months:
            block[c] = pd.to_numeric(block[c], errors='coerce')
        out[yr] = block.reset_index(drop=True)
    return out


DISTRICT_COLS = ["District", "All Reported", "Murder", "Attempted Murder", "Suicide",
                  "Attempted Suicide", "Gang Rape", "Kidnapping/Abduction", "Dacoity",
                  "Robbery", "Traffic Accident", "Burglary", "Cattle theft",
                  "Motor Vehicle Theft", "Other theft", "Miscellaneous"]


@st.cache_data
def load_district_crime(province):
    files = {
        "Islamabad": (f"{DATA_DIR}/District wise crime data/Islamabad.xlsx", "2024"),
        "Balochistan": (f"{DATA_DIR}/District wise crime data/Baloch.xlsx", "2024"),
        "KP": (f"{DATA_DIR}/District wise crime data/KP.xlsx", "2024"),
        "Punjab": (f"{DATA_DIR}/District wise crime data/Punjab.xlsx", "2024"),
        "Sindh": (f"{DATA_DIR}/District wise crime data/Sindh.xlsx", "2024"),
    }
    path, sheet = files[province]
    df = pd.read_excel(path, sheet_name=sheet, header=None)
    if province == "Islamabad":
        data = df.iloc[4:5, 1:].copy()
        data.columns = ["Year"] + DISTRICT_COLS[1:]
        data.insert(0, "District", "Islamabad")
        data = data.drop(columns=["Year"])
    else:
        data = df.iloc[5:].copy()
        data = data.iloc[:, 1:17]
        data.columns = DISTRICT_COLS
        data = data.dropna(subset=["District"])
        data = data[~data["All Reported"].isna()]
        total_labels = {"total", "grand total", "g total"}
        data = data[~data["District"].astype(str).str.strip().str.lower().isin(total_labels)]
    for c in DISTRICT_COLS[1:]:
        data[c] = pd.to_numeric(data[c], errors='coerce')
    return data.reset_index(drop=True)


@st.cache_data
def load_traffic_accidents_yearly():
    """Returns dict {region: dataframe}. File has 6 stacked blocks
    (PAKISTAN + 5 provinces/territories), each with its own year series."""
    df = pd.read_excel(f"{DATA_DIR}/Traffic-Accident-Yearly.xlsx", header=None)
    region_names = ["PAKISTAN", "PUNJAB", "SINDH", "KHYBER PAKHTUNKHWA", "BALOCHISTAN", "ISLAMABAD"]
    region_rows = df.index[df[0].isin(region_names)].tolist()
    cols = ["Year", "Total Accidents", "Fatal", "Non-Fatal", "Killed", "Injured", "Total Vehicles Involved"]
    out = {}
    for r in region_rows:
        region = df.iloc[r, 0]
        block = df.iloc[r + 1: r + 12].copy()
        block.columns = cols
        block["Year"] = block["Year"].astype(str).str.replace("*", "", regex=False).str.strip()
        block = block[block["Year"].str.match(r"^\d{4}-\d{2,4}$", na=False)]
        for c in cols[1:]:
            block[c] = pd.to_numeric(block[c], errors='coerce')
        block = block.dropna(subset=["Total Accidents"])
        out[region.title().replace("Khyber Pakhtunkhwa", "Khyber Pakhtunkhwa")] = block.reset_index(drop=True)
    return out


@st.cache_data
def load_appeals_petitions():
    df = pd.read_excel(f"{DATA_DIR}/Appeal-and-Petition-Hogh-Courts-1.xls", header=None)
    data = df.iloc[5:].copy()
    data.columns = ["Year", "Last Balance", "Fresh Registered", "Included Remaining Appeals",
                     "Total for Disposal", "Disposed off", "Physical Verification",
                     "Transferred", "Pending"]
    data = data.dropna(subset=["Year"])
    data = data[pd.to_numeric(data["Year"], errors='coerce').notna()]
    for c in data.columns[1:]:
        data[c] = pd.to_numeric(data[c], errors='coerce')
    return data.reset_index(drop=True)


# ---------------- TOURISM / HERITAGE ----------------

def _parse_multi_year_visitor_block(path):
    df = pd.read_excel(path, header=None)
    years = [int(y) for y in df.iloc[2].dropna().tolist() if str(y).replace('.0', '').isdigit()]
    records = []
    body = df.iloc[5:].reset_index(drop=True)
    for i, row in body.iterrows():
        place = row[0]
        if pd.isna(place):
            continue
        for j, yr in enumerate(years):
            fcol = 1 + j * 2
            ncol = 2 + j * 2
            if fcol >= len(row):
                continue
            records.append({
                "Place": str(place).strip(), "Year": yr,
                "Foreigner": pd.to_numeric(row[fcol], errors='coerce'),
                "National": pd.to_numeric(row[ncol], errors='coerce'),
            })
    out = pd.DataFrame(records)
    # drop footer/note/source rows: these have no numeric data in ANY year for that place
    valid_places = out.groupby("Place")[["Foreigner", "National"]].apply(
        lambda g: g.notna().any().any())
    out = out[out["Place"].isin(valid_places[valid_places].index)]
    return out.reset_index(drop=True)


@st.cache_data
def load_museum_visitors_multiyear():
    return _parse_multi_year_visitor_block(f"{DATA_DIR}/No.-of-Visitor-at-Archaeological-Museum.xlsx")


@st.cache_data
def load_heritage_visitors_multiyear():
    return _parse_multi_year_visitor_block(f"{DATA_DIR}/No.-of-Visitor-of-Heritage-site.xlsx")


def _parse_monthly_section(df, header_rows, section_end):
    """header_rows: row indices where col0 starts a new month-block header
    ('Area/ attraction' + month names, e.g. Jan-Jun block, then Jul-Dec block).
    Merges all blocks into one long Place/Month/Foreigner/National table."""
    records = []
    for idx, h in enumerate(header_rows):
        months = [str(m).strip() for m in df.iloc[h, 1:].dropna().tolist()]
        data_start = h + 2
        data_end = header_rows[idx + 1] if idx + 1 < len(header_rows) else section_end
        block = df.iloc[data_start:data_end]
        for _, row in block.iterrows():
            place = row[0]
            if pd.isna(place):
                continue
            place_str = str(place).strip()
            if not place_str or "note" in place_str.lower() or "source" in place_str.lower() or place_str.startswith("."):
                continue
            for j, m in enumerate(months):
                fcol, ncol = 1 + j * 2, 2 + j * 2
                if ncol >= len(row):
                    continue
                f = pd.to_numeric(row[fcol], errors='coerce')
                n = pd.to_numeric(row[ncol], errors='coerce')
                if pd.isna(f) and pd.isna(n):
                    continue
                records.append({"Place": place_str, "Month": m, "Foreigner": f, "National": n})
    return pd.DataFrame(records)


def _load_monthly_topic(year, topic):
    """topic: 'museum' or 'heritage'. The 'Museum' sheet in each Web-Data file
    actually contains TWO stacked topics (Museums, then Heritage Sites) —
    this splits them apart correctly."""
    files = {
        2022: f"{DATA_DIR}/web-Data-2022.xlsx",
        2023: f"{DATA_DIR}/Web-data-2023.xlsx",
        2024: f"{DATA_DIR}/Web-Data-2024.xlsx",
        2025: f"{DATA_DIR}/Web-Data-2025.xlsx",
    }
    df = pd.read_excel(files[year], sheet_name="Museum", header=None)
    marker_rows = df.index[df[0].astype(str).str.contains("Heritage Site", na=False)].tolist()
    boundary = marker_rows[0] if marker_rows else len(df)

    def is_header(i):
        return str(df.iloc[i, 0]).strip().lower().startswith("area")

    if topic == "museum":
        header_rows = [i for i in range(0, boundary) if is_header(i)]
        section_end = boundary
    else:
        header_rows = [i for i in range(boundary, len(df)) if is_header(i)]
        section_end = len(df)

    out = _parse_monthly_section(df, header_rows, section_end)
    valid_places = out.groupby("Place")[["Foreigner", "National"]].apply(lambda g: g.notna().any().any())
    out = out[out["Place"].isin(valid_places[valid_places].index)]
    return out.reset_index(drop=True)


@st.cache_data
def load_museum_monthly(year):
    return _load_monthly_topic(year, "museum")


@st.cache_data
def load_heritage_monthly(year):
    return _load_monthly_topic(year, "heritage")


@st.cache_data
def load_zoo_statistics():
    """Returns dict {zoo_name: dataframe}. File has 4 stacked zoo blocks."""
    df = pd.read_excel(f"{DATA_DIR}/Zoo-Statistics.xlsx", header=None)
    zoo_names = ["Karachi Zoo", "Bahawalpur Zoo", "Lahore Zoo", "Islamabad Zoo"]
    zoo_rows = df.index[df[0].isin(zoo_names)].tolist()
    zoo_rows.append(len(df))
    cols = ["Year", "Adult Visitors", "Minor Visitors", "No. of Animals", "No. of Birds",
            "Total Expenditure", "Total Income"]
    out = {}
    for i in range(len(zoo_names)):
        start, stop = zoo_rows[i] + 1, zoo_rows[i + 1]
        block = df.iloc[start:stop].copy()
        block.columns = cols
        block["Year"] = block["Year"].astype(str).str.strip()
        block = block[block["Year"].str.match(r"^\d{4}-\d{2,4}", na=False)]
        for c in cols[1:]:
            block[c] = pd.to_numeric(block[c], errors='coerce')
        block = block.dropna(subset=["Adult Visitors"], how="all")
        out[zoo_names[i]] = block.reset_index(drop=True)
    return out


@st.cache_data
def load_tourist_by_region():
    df = pd.read_excel(f"{DATA_DIR}/No.-of-Tourist-by-Region.xlsx", header=None)
    years = [int(y) for y in df.iloc[2, 2:].dropna().tolist()]
    data = df.iloc[3:11].copy()
    data = data.iloc[:, 1:2 + len(years)]
    data.columns = ["Region"] + years
    data = data.dropna(subset=["Region"])
    for c in years:
        data[c] = pd.to_numeric(data[c], errors='coerce')
    return data.reset_index(drop=True)


@st.cache_data
def load_tourist_by_mode():
    df = pd.read_excel(f"{DATA_DIR}/No.-of-Tourist-arrive-by-Mode-and-Gender.xlsx", header=None)
    data = df.iloc[4:13, 1:].copy()
    data.columns = ["Year", "Air", "Sea", "Land", "Railway", "Total"]
    data = data.dropna(subset=["Year"])
    for c in data.columns[1:]:
        data[c] = pd.to_numeric(data[c], errors='coerce')
    return data.reset_index(drop=True)


@st.cache_data
def load_tourist_by_gender():
    """Second table in the same file: tourist arrivals by sex, in thousands."""
    df = pd.read_excel(f"{DATA_DIR}/No.-of-Tourist-arrive-by-Mode-and-Gender.xlsx", header=None)
    data = df.iloc[19:28, 1:4].copy()
    data.columns = ["Year", "Male (000s)", "Female (000s)"]
    data = data.dropna(subset=["Year"])
    for c in ["Male (000s)", "Female (000s)"]:
        data[c] = pd.to_numeric(data[c], errors='coerce')
    return data.reset_index(drop=True)


# ---------------- HEALTH ----------------

@st.cache_data
def load_health_institutes_beds():
    df = pd.read_excel(f"{DATA_DIR}/Health-Institure-and-Personnels-1.xls", sheet_name="10-2", header=None)
    header_rows = df.index[df[0].astype(str).str.strip().str.lower().str.startswith("year")].tolist()
    header_rows.append(len(df))
    blocks = []
    for i in range(len(header_rows) - 1):
        h, next_h = header_rows[i], header_rows[i + 1]
        years = [int(y) for y in df.iloc[h, 1:6].dropna().tolist()]
        block = df.iloc[h + 1:next_h, 0:6].copy()
        block.columns = ["Indicator"] + years
        block = block.dropna(subset=["Indicator"])
        block = block[~block["Indicator"].astype(str).str.contains("Source|Provisional", na=False)]
        block["Indicator"] = (block["Indicator"].astype(str)
                               .str.replace("*", "", regex=False)
                               .str.replace("/ ", "/", regex=False)
                               .str.strip()
                               .str.replace(r"\s+", " ", regex=True))
        last_label = None
        new_labels = []
        for lbl in block["Indicator"]:
            if lbl.lower() == "no. of beds" and last_label:
                new_labels.append(f"{last_label} — No. of beds")
            else:
                new_labels.append(lbl)
                last_label = lbl
        block["Indicator"] = new_labels
        for c in years:
            block[c] = pd.to_numeric(block[c].astype(str).str.replace("*", "", regex=False), errors='coerce')
        blocks.append(block.set_index("Indicator"))
    merged = pd.concat(blocks, axis=1)
    merged = merged.loc[:, ~merged.columns.duplicated()] if merged.columns.duplicated().any() else merged
    result = merged.reset_index()
    for c in result.columns:
        if c != "Indicator":
            result[c] = result[c].astype(float)
    return result


@st.cache_data
def load_immunization_yearly():
    df = pd.read_excel(f"{DATA_DIR}/Immunization-Coverage-Yearly-1.xls", sheet_name="10.4(Final)", header=None)

    block1 = df.iloc[6:19, 0:9].copy()
    block1.columns = ["Year", "Polio (0+1)", "Polio II", "Polio III",
                       "TT I", "TT II", "TT III", "TT IV", "TT V"]

    block2 = df.iloc[24:37, 0:9].copy()
    block2.columns = ["Year", "Measles", "BCG", "Pentavalent I",
                       "Pentavalent II", "Pentavalent III",
                       "Pneumococcal I", "Pneumococcal II", "Pneumococcal III"]

    for b in (block1, block2):
        b["Year"] = pd.to_numeric(b["Year"], errors='coerce')
        b.dropna(subset=["Year"], inplace=True)
        b["Year"] = b["Year"].astype(int)
        for c in b.columns[1:]:
            b[c] = pd.to_numeric(b[c].astype(str).str.replace("**", "", regex=False), errors='coerce')

    merged = pd.merge(block1, block2, on="Year", how="outer").sort_values("Year")
    return merged.reset_index(drop=True)


@st.cache_data
def load_immunization_monthly(year, topic="0-11 months"):
    """topic: '0-11 months', '12-23 months', or 'TT (women)'.
    The sheet has 3 stacked topic blocks, each with its own months+columns."""
    files = {
        2022: f"{DATA_DIR}/web-Data-2022.xlsx",
        2023: f"{DATA_DIR}/Web-data-2023.xlsx",
        2024: f"{DATA_DIR}/Web-Data-2024.xlsx",
        2025: f"{DATA_DIR}/Web-Data-2025.xlsx",
    }
    if year not in files:
        return pd.DataFrame()
    df = pd.read_excel(files[year], sheet_name="Immunization", header=None)
    marker_rows = df.index[df[0].astype(str).str.contains("Monthly Immunization Coverage", na=False)].tolist()
    marker_rows.append(len(df))
    topic_idx = {"0-11 months": 0, "12-23 months": 1, "TT (women)": 2}.get(topic, 0)
    if topic_idx >= len(marker_rows) - 1:
        return pd.DataFrame()
    h = marker_rows[topic_idx] + 2
    section_end = marker_rows[topic_idx + 1]
    header = df.iloc[h].tolist()
    # forward-fill blank header cells (merged-cell columns) and build unique names
    clean_header = ["Month"]
    last = None
    for v in header[1:]:
        name = str(v).strip() if pd.notna(v) else (last or "col")
        if pd.notna(v):
            last = str(v).strip()
        clean_header.append(name)
    data = df.iloc[h + 1:section_end].copy()
    data.columns = clean_header[:data.shape[1]]
    # de-duplicate column names (e.g. repeated 'Pneumo' from merged header cells)
    seen = {}
    uniq_cols = []
    for c in data.columns:
        if c in seen:
            seen[c] += 1
            uniq_cols.append(f"{c}-{seen[c]}")
        else:
            seen[c] = 0
            uniq_cols.append(c)
    data.columns = uniq_cols
    data = data[data["Month"].astype(str).str.strip().str.lower() != "total"]
    data = data.dropna(subset=["Month"])
    data = data[data["Month"].astype(str).str.match(r"^[A-Za-z]+$", na=False)]
    for c in data.columns[1:]:
        data[c] = pd.to_numeric(data[c], errors='coerce')
    return data.reset_index(drop=True)


@st.cache_data
def load_hiv_data():
    """Returns dict {month_label: dataframe}. Each 'quarter' sheet actually
    contains 3 separate monthly reports stacked (e.g. 'Jan-March2023' sheet
    has Jan, Feb AND March blocks) — this splits them into true months."""
    xl = pd.ExcelFile(f"{DATA_DIR}/HIV-2024.xlsx")
    cols = ["Centre", "Male Total", "Male On ART", "Female Total", "Female On ART",
            "Children Total", "Children On ART", "Transgender Total", "Transgender On ART",
            "TOTAL", "TOTAL on ART"]
    frames = {}
    for sn in xl.sheet_names:
        df = xl.parse(sn, header=None)
        marker_rows = df.index[df[0].astype(str).str.contains("Monthly Report", na=False)].tolist()
        for mi, marker in enumerate(marker_rows):
            month_label = str(df.iloc[marker, 0]).replace(" Monthly Report", "").strip()
            data_start = marker + 1
            total_rows = df.index[(df[0].astype(str).str.strip() == "Total") & (df.index > marker)].tolist()
            data_end = next((t for t in total_rows if t > data_start), len(df))
            block = df.iloc[data_start:data_end].copy()
            block = block[pd.to_numeric(block[0], errors='coerce').notna()]
            if block.empty:
                continue
            block = block.iloc[:, 1:12]
            block.columns = cols
            for c in cols[1:]:
                block[c] = pd.to_numeric(block[c], errors='coerce')
            frames[month_label] = block.reset_index(drop=True)
    return frames


@st.cache_data
def load_traffic_monthly(year):
    """Returns dict {region: dataframe}. The Accidents sheet stacks 6 regions
    (Islamabad, Punjab, Sindh, KP, Balochistan, Pakistan), each 12 months + Total."""
    files = {
        2022: f"{DATA_DIR}/web-Data-2022.xlsx",
        2023: f"{DATA_DIR}/Web-data-2023.xlsx",
        2024: f"{DATA_DIR}/Web-Data-2024.xlsx",
        2025: f"{DATA_DIR}/Web-Data-2025.xlsx",
    }
    df = pd.read_excel(files[year], sheet_name="Accidents", header=None)
    region_rows = df.index[pd.to_numeric(df[0], errors='coerce').notna() & df[1].notna()
                            & (df[1].astype(str).str.strip() != "")].tolist()
    # region marker rows are where col0 is a year number and col1 is the region name
    region_rows = [r for r in region_rows if str(df.iloc[r, 1]).strip()
                    in ("Islamabad", "Punjab", "Sindh", "KP", "Balochistan", "Pakistan")]
    region_rows.append(len(df))
    cols = ["Month", "Total", "Fatal", "Non-Fatal", "Killed", "Injured", "Total Vehicles"]
    out = {}
    for i in range(len(region_rows) - 1):
        h, next_h = region_rows[i], region_rows[i + 1]
        total_after = df.index[(df[0].astype(str).str.strip().str.lower() == "total") & (df.index > h)]
        total_after = [t for t in total_after if t < next_h]
        if total_after:
            next_h = total_after[0] + 1
        region = str(df.iloc[h, 1]).strip()
        block = df.iloc[h + 1:next_h].copy()
        block.columns = cols
        block = block.dropna(subset=["Month"])
        block = block[block["Month"].astype(str).str.strip().str.lower() != "total"]
        for c in cols[1:]:
            block[c] = pd.to_numeric(block[c], errors='coerce')
        out[region] = block.reset_index(drop=True)
    return out


@st.cache_data
def load_veterinary_monthly(year, topic="Veterinary Practitioners"):
    """topic: 'Veterinary Practitioners' or 'Animal Husbandry Graduates'.
    The sheet stacks both topics — this splits them apart."""
    files = {
        2022: f"{DATA_DIR}/web-Data-2022.xlsx",
        2023: f"{DATA_DIR}/Web-data-2023.xlsx",
        2024: f"{DATA_DIR}/Web-Data-2024.xlsx",
        2025: f"{DATA_DIR}/Web-Data-2025.xlsx",
    }
    sheet = "Veterinary" if year != 2022 else "Veternary"
    df = pd.read_excel(files[year], sheet_name=sheet, header=None)
    ah_marker = df.index[df[0].astype(str).str.contains("Animal Husbandry", na=False)].tolist()
    ah_start = ah_marker[0] if ah_marker else len(df)

    if "Animal" in topic:
        block = df.iloc[ah_start + 4: ah_start + 16, 1:8].copy()
        block.columns = ["Month", "Male", "Female", "B.Sc.(Hons) A.H.", "M.Sc.", "Ph.D.", "Total"]
    else:
        block = df.iloc[3:15, 1:9].copy()
        block.columns = ["Month", "Male", "Female", "D.V.M.", "M.Sc.", "M.Phil.", "Ph.D.", "Total"]

    for c in block.columns[1:]:
        block[c] = pd.to_numeric(block[c], errors='coerce')
    return block.reset_index(drop=True)


@st.cache_data
def load_tb_by_province(year):
    """Returns dict {quarter_label: dataframe}. The T.B sheet stacks 4 quarters."""
    files = {2022: f"{DATA_DIR}/web-Data-2022.xlsx", 2024: f"{DATA_DIR}/Web-Data-2024.xlsx"}
    if year not in files:
        return {}
    df = pd.read_excel(files[year], sheet_name="T.B", header=None)
    marker_rows = df.index[df[0].astype(str).str.contains("Period:", na=False)].tolist()
    marker_rows.append(len(df))
    cols = ["Province/Region", "TB Cases B+", "CNR B+", "Male", "Female", "Total", "CDR", "% Treatment Success"]
    out = {}
    for i in range(len(marker_rows) - 1):
        h, next_h = marker_rows[i], marker_rows[i + 1]
        label = str(df.iloc[h, 0]).replace("Period:", "").strip()
        block = df.iloc[h + 3:h + 11].copy()
        block.columns = cols
        block = block.dropna(subset=["Province/Region"])
        for c in cols[1:]:
            block[c] = pd.to_numeric(block[c], errors='coerce')
        out[label] = block.reset_index(drop=True)
    return out


@st.cache_data
def load_dental_doctors():
    """Note: file is mislabeled — actual content is hospitals/dispensaries/beds
    by PROVINCE (Federal, Punjab, Sindh, KP, Balochistan), not dental doctor counts.
    Returns dict {province: dataframe}."""
    df = pd.read_excel(f"{DATA_DIR}/No.-of-Dental-Doctors.xls", sheet_name="10-1", header=None)
    province_names = ["Federal", "Punjab", "Sindh", "Khyber Pakhtunnkhwa/ FATA", "Balochistan"]
    header_rows = df.index[df[0].astype(str).str.strip().isin(province_names)].tolist()
    header_rows.append(len(df))
    cols = ["Year", "Hospitals", "Dispensaries", "Maternity & Child Centres", "Beds"]
    out = {}
    for i in range(len(header_rows) - 1):
        h, next_h = header_rows[i], header_rows[i + 1]
        province = str(df.iloc[h, 0]).strip()
        block = df.iloc[h + 1:next_h, 0:5].copy()
        block.columns = cols
        block["Year"] = block["Year"].astype(str).str.replace("*", "", regex=False).str.strip()
        block = block[block["Year"].str.match(r"^\d{4}$", na=False)]
        block["Year"] = block["Year"].astype(int)
        for c in cols[1:]:
            block[c] = pd.to_numeric(block[c], errors='coerce')
        out[province.replace("Khyber Pakhtunnkhwa/ FATA", "KP / FATA")] = block.reset_index(drop=True)
    return out


# ---------------- EDUCATION ----------------

@st.cache_data
def load_education():
    df = pd.read_excel(f"{DATA_DIR}/Education.xls", sheet_name="cs", header=None)
    years = df.iloc[3, 1:].tolist()
    level_names = {"Primary Schools", "Middle Schools", "High Schools"}
    records = []
    current_level, current_metric = None, None
    for i in range(3, len(df)):
        label = df.iloc[i, 0]
        if pd.isna(label):
            continue
        label = str(label).strip()
        row_vals = df.iloc[i, 1:].tolist()
        all_num = all(pd.to_numeric(pd.Series(row_vals), errors='coerce').notna())
        if label in level_names:
            current_level = label
            continue
        if not all_num:
            current_metric = label
            continue
        if label in ("Total", "Female"):
            for yr, val in zip(years, row_vals):
                v = pd.to_numeric(val, errors='coerce')
                if pd.notna(v):
                    records.append({"Level": current_level, "Metric": current_metric,
                                     "Stat": label, "Year": yr, "Value": v})
        else:
            # single-row ratio metrics (no Total/Female split)
            for yr, val in zip(years, row_vals):
                v = pd.to_numeric(val, errors='coerce')
                if pd.notna(v):
                    records.append({"Level": current_level, "Metric": label,
                                     "Stat": "Value", "Year": yr, "Value": v})
    return pd.DataFrame(records)


# ---------------- MEDIA & TELECOM ----------------

@st.cache_data
def load_documentary_films():
    df = pd.read_excel(f"{DATA_DIR}/Documentry-Film-produce.xlsx", header=None)
    data = df.iloc[4:].copy()
    data = data.iloc[:, 1:]
    data.columns = ["Year", "Federal Produced", "Federal Released", "Punjab Produced", "Punjab Released",
                     "Sindh Produced", "Sindh Released", "KP Produced", "KP Released"]
    data = data.dropna(subset=["Year"])
    for c in data.columns[1:]:
        data[c] = pd.to_numeric(data[c].replace("--", None), errors='coerce')
    return data.reset_index(drop=True)


@st.cache_data
def load_dramas_plays():
    df = pd.read_excel(f"{DATA_DIR}/No.-of-Dramas-Produce-Telcast.xlsx", header=None)
    data = df.iloc[4:].copy()
    data = data.iloc[:, 1:]
    data.columns = ["Year", "TV Produced", "TV Telecasted", "Radio Produced", "Radio Broadcasted"]
    data = data.dropna(subset=["Year"])
    for c in data.columns[1:]:
        data[c] = pd.to_numeric(data[c].replace({"Nil": 0}), errors='coerce')
    return data.reset_index(drop=True)


@st.cache_data
def load_tv_sets():
    df = pd.read_excel(f"{DATA_DIR}/No.-of-T.V-Sect.xlsx", header=None)
    data = df.iloc[4:].copy()
    data = data.iloc[:, 1:]
    data.columns = ["Year", "Punjab", "Sindh", "KP", "Balochistan", "Total"]
    data = data.dropna(subset=["Year"])
    data = data[pd.to_numeric(data["Year"], errors='coerce').notna()]
    for c in data.columns[1:]:
        data[c] = pd.to_numeric(data[c], errors='coerce')
    return data.reset_index(drop=True)


@st.cache_data
def load_telecom_monthly(year):
    files = {
        2022: f"{DATA_DIR}/web-Data-2022.xlsx",
        2023: f"{DATA_DIR}/Web-data-2023.xlsx",
        2024: f"{DATA_DIR}/Web-Data-2024.xlsx",
        2025: f"{DATA_DIR}/Web-Data-2025.xlsx",
    }
    df = pd.read_excel(files[year], sheet_name="Telecom", header=None)
    data = df.iloc[5:].copy()
    data.columns = ["Month", "Total", "PMCL (Jazz)", "CM Pak", "PTML Ufone", "Telenor", "SCO"]
    data = data.dropna(subset=["Month"])
    for c in data.columns[1:]:
        data[c] = pd.to_numeric(data[c], errors='coerce')
    return data.reset_index(drop=True)