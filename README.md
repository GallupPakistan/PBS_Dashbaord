# PBS Social Statistics Dashboard

Streamlit dashboard covering 26 datasets from the Pakistan Bureau of Statistics
"Social Statistics" publication (pbs.gov.pk/social-statistics-2), organized into
4 categories: Crime, Tourism & Heritage, Health, and Media/Telecom/Education.

## Run locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Deploy (Streamlit Community Cloud, via GitHub)

1. Push this folder to a GitHub repo (keep the `data/` folder — it holds all
   source Excel files the app reads from).
2. Go to https://share.streamlit.io, connect the repo, set main file to `app.py`.
3. Deploy. You'll get a live URL to share.

## Updating data later

Replace the relevant file inside `data/` (keep the exact same filename), commit
and push. If deployed on Streamlit Cloud, the app auto-redeploys and the
dashboard reflects the new numbers — no code changes needed for routine
year-over-year updates, as long as the new file keeps the same sheet
names/layout as the original.

If PBS changes a file's internal structure (renames a sheet, adds/removes
columns), the matching loader function in `loaders.py` will need a small
update — see the function for that dataset.

## Known data quality notes (from source files, not introduced during build)

- `Crime-By-Types-Yearly.xlsx` actually contains **3 stacked years** (2022,
  2023, 2024) in one file — parsed as one tab with a year selector.
  `Province-Wise-Crime-data.xlsx` is an exact duplicate of just the 2022
  block from that file, so it is not loaded separately (kept in `data/` for
  reference only).
- `Moth-wise-Crime-data.xlsx` similarly contains **3 stacked years** (2022,
  2023, 2024), not just one — parsed as one tab with a year selector.
- `Health-Institure-and-Personnels-1.xls` and `Health-Institute-Beds-1-1.xls`
  contain identical data — only one is used.
- `No.-of-Dental-Doctors.xls` is mislabeled: its actual content is
  hospitals/dispensaries/beds, not dental doctor counts. Shown as-is with a
  warning in the dashboard.
- `Web-Data-2022/2023/2024/2025.xlsx` each bundle six unrelated topics
  (Accidents, Veterinary, T.B, Telecom, Immunization, Museum) inside one
  file — split out into their respective category tabs rather than kept as
  one "museum" tab.
- District-wise crime files (Islamabad/Balochistan/KP/Punjab/Sindh) only have
  a single year (2024) of data at the time of writing.

## Project structure

```
app.py                Streamlit app — sidebar navigation + tab routing
crime_analytics.py     Analyst-grade rendering (10+ visuals/KPIs per Crime tab)
loaders.py             One function per dataset — reads + cleans the raw Excel
data/                   Source Excel files (as downloaded from PBS)
requirements.txt
```

Crime category (7 tabs) currently has full analyst-depth treatment (KPI
cards, 10 visuals per tab: trends, YoY change, composition, rankings,
heatmaps, correlations). Other categories (Tourism & Heritage, Health,
Media/Telecom/Education) still use the simpler single-chart view from the
first build pass — same pattern can be extended to them next.
