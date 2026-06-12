# San Diego Governance Charts

Data-driven charts tracking how the City of San Diego is performing over time.

**Live site:** [your GitHub Pages URL once deployed]

---

## What this is

A static website hosting governance charts built from public San Diego data.
The data pipeline runs automatically every week via GitHub Actions, checks for
new data, and redeploys the site if anything changed.

**Cost: ~$0/year** (GitHub + GitHub Pages are free for public repos)

---

## Charts

| Chart | Data Sources | Update Frequency |
|---|---|---|
| Personnel vs. Population Growth | City Adopted Budget PDFs + FRED (BEA population) | Annual (new budget each August) |
| City Expenditures vs. Regional GDP | SD Open Data Operating Actuals + FRED (BEA GDP) | Annual |

---

## Repo Structure

```
site/                  Static website files (deployed via GitHub Pages)
  index.html           Chart gallery with search and filter
  style.css            Shared styles
  charts/              One HTML file per chart
  data/                JSON data files (auto-generated, do not hand-edit)
  charts_registry.json Chart metadata for the gallery
scripts/               Data pipeline
  chart_*.py           One script per chart
  update_all.py        Orchestrator (runs all chart scripts)
.github/workflows/
  update.yml           GitHub Actions scheduler (runs weekly)
```

---

## Setup

### 1. Fork / clone this repo

```bash
git clone https://github.com/YOUR_USERNAME/sd-governance-charts
cd sd-governance-charts
```

### 2. Enable GitHub Pages

In your GitHub repo settings → Pages → Source: **Deploy from branch** → branch: `main`, folder: `/site`

### 3. Run the data pipeline locally (first time)

```bash
pip install requests pandas
python scripts/update_all.py
```

Commit the generated `site/data/*.json` files.

### 4. Push — the site is live

The GitHub Actions workflow runs automatically every Monday. You can also
trigger it manually from the Actions tab.

---

## Adding a new chart

1. Write `scripts/chart_yourname.py` — must expose a `build_json()` function
   that writes a JSON file to `site/data/yourname.json`
2. Write `site/charts/yourname.html` that reads that JSON and renders a chart
3. Add an entry to `site/charts_registry.json`
4. Commit and push

The automation will keep it updated from that point forward.

---

## Updating FTE data

The FTE series in `scripts/chart_fte_vs_population.py` requires a one-time
manual update each year when the new Adopted Budget is published (~August):

1. Find the new budget PDF at sandiego.gov
2. Search for "Full-Time Equivalent" in the executive summary
3. Add the new `{"fiscal_year": YYYY, "total_fte": NNNNN}` entry to `FTE_DATA`
4. Commit — everything else is automatic

---

## Data Sources

- **City of San Diego Open Data Portal:** data.sandiego.gov
- **SD Adopted Budget PDFs:** sandiego.gov (published annually)
- **FRED (Federal Reserve Bank of St. Louis):** fred.stlouisfed.org
  - POPSAND — MSA population
  - NGMP41740 — MSA nominal GDP
