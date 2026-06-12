"""
chart_fte_vs_population.py

Builds site/data/fte_vs_population.json from:
  - A manually-maintained FTE series (updated once/year from the adopted budget PDF)
  - FRED series POPSAND: Resident Population in San Diego-Carlsbad, CA (MSA)

The FRED population series updates annually, so this script auto-fetches the
latest population data and merges it with the FTE series.

FTE SOURCE: City of San Diego Adopted Budget, Volume 1 Executive Summary.
Published each August at sandiego.gov. The total citywide FTE count is listed
near the top of the executive summary.

To update FTE for a new fiscal year:
  1. Find the new Adopted Budget PDF at sandiego.gov
  2. Search for "Full-Time Equivalent" or "FTE positions"
  3. Add the new fiscal_year and total_fte entry to FTE_DATA below
  4. Commit — the GitHub Action will handle the rest
"""

import json
import requests
from pathlib import Path

OUTPUT_PATH = Path(__file__).parent.parent / "site" / "data" / "fte_vs_population.json"

# ── Manually maintained FTE series ──────────────────────────────────────────
# Source: City of San Diego Adopted Budget, Volume 1 Executive Summary
# fiscal_year = the FY label (e.g. 2024 = FY2024, which runs July 2023–June 2024)
# total_fte   = total citywide budgeted FTE positions (all funds)
FTE_DATA = [
    # Earlier years require pulling older budget PDFs; extend backward as needed
    {"fiscal_year": 2019, "total_fte": 11_193},  # FY2019 Adopted Budget
    {"fiscal_year": 2020, "total_fte": 11_455},  # FY2020 Adopted Budget
    {"fiscal_year": 2021, "total_fte": 11_616},  # FY2021 Adopted Budget
    {"fiscal_year": 2022, "total_fte": 11_900},  # FY2022 Adopted Budget (approx)
    {"fiscal_year": 2023, "total_fte": 12_505},  # FY2023 Adopted Budget
    {"fiscal_year": 2024, "total_fte": 13_030},  # FY2024 Adopted Budget
    {"fiscal_year": 2025, "total_fte": 13_352},  # FY2025 Adopted Budget
    # FY2026: General Fund only = 8,261 (total citywide ~12,880 est.)
    # Update when FY2026 Adopted Budget Volume 1 is published
]

# ── FRED population data ─────────────────────────────────────────────────────
# Series: POPSAND — Resident Population in San Diego-Carlsbad, CA (MSA)
# Units: thousands of persons, annual, not seasonally adjusted
# Vintage aligns with calendar year (Jan 1 observation = that calendar year)
FRED_SERIES = "POPSAND"
FRED_URL = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={FRED_SERIES}"


def fetch_population():
    """Returns dict of {calendar_year: population_thousands}"""
    print(f"Fetching FRED {FRED_SERIES}...")
    r = requests.get(FRED_URL, timeout=30)
    r.raise_for_status()
    pop = {}
    for line in r.text.strip().split("\n")[1:]:  # skip header
        date, value = line.split(",")
        year = int(date[:4])
        if value.strip() != ".":
            pop[year] = float(value)
    print(f"  Got {len(pop)} years of population data ({min(pop)}-{max(pop)})")
    return pop


def build_json():
    pop = fetch_population()

    rows = []
    for entry in FTE_DATA:
        fy = entry["fiscal_year"]
        # FY2024 (July 2023–June 2024) → align to calendar year FY-1
        # We use the prior calendar year as the reference population midpoint
        cal_year = fy - 1
        if cal_year not in pop:
            print(f"  WARNING: no population data for calendar year {cal_year}, skipping FY{fy}")
            continue
        rows.append({
            "fiscal_year": fy,
            "label": f"FY{fy}",
            "total_fte": entry["total_fte"],
            "population_thousands": pop[cal_year],
            "population": round(pop[cal_year] * 1000),
            "fte_per_1000_residents": round(entry["total_fte"] / pop[cal_year], 2),
        })

    # Index to first year for growth calculations
    if rows:
        base_fte = rows[0]["total_fte"]
        base_pop = rows[0]["population"]
        for row in rows:
            row["fte_index"] = round(row["total_fte"] / base_fte * 100, 1)
            row["pop_index"] = round(row["population"] / base_pop * 100, 1)

    output = {
        "title": "City of San Diego: Personnel vs. Population Growth",
        "description": (
            "Compares growth in total citywide budgeted FTE positions against "
            "MSA resident population. Both series indexed to 100 at the first year. "
            "A rising FTE index relative to the population index means the city "
            "is adding staff faster than it is gaining residents."
        ),
        "sources": {
            "fte": "City of San Diego Adopted Budget, Volume 1 Executive Summary (annual)",
            "population": f"FRED series {FRED_SERIES} — Resident Population, San Diego-Carlsbad MSA",
        },
        "base_year": rows[0]["fiscal_year"] if rows else None,
        "data": rows,
    }

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(output, indent=2))
    print(f"Wrote {len(rows)} rows → {OUTPUT_PATH}")


if __name__ == "__main__":
    build_json()
