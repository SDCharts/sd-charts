"""
chart_expenditures_vs_gdp.py

Builds site/data/expenditures_vs_gdp.json from:
  - SD Open Data: Operating Actuals CSV (expense rows only, all funds)
  - FRED series NGMP41740: Total Nominal GDP for San Diego-Carlsbad MSA
    (discontinued but still updated through 2023; we supplement with BEA
     county-level data when available)

SD fiscal years run July 1 – June 30.
FY2024 = July 2023 – June 2024.
We align GDP to the calendar year that ends within the fiscal year (FY2024 → CY2023).
"""

import io
import json
import requests
from pathlib import Path

OUTPUT_PATH = Path(__file__).parent.parent / "site" / "data" / "expenditures_vs_gdp.json"

SD_ACTUALS_URL = "https://seshat.datasd.org/operating_actuals/actuals_operating_datasd.csv"
FRED_GDP_URL   = "https://fred.stlouisfed.org/graph/fredgraph.csv?id=NGMP41740"


def fetch_sd_expenditures():
    """
    Fetches the SD operating actuals CSV and returns total expense actuals by fiscal year.
    Filters to account_type == 'Expense' to exclude revenue rows.
    """
    print("Fetching SD Operating Actuals (65 MB — may take a moment)...")
    r = requests.get(SD_ACTUALS_URL, timeout=120)
    r.raise_for_status()

    import pandas as pd
    df = pd.read_csv(io.StringIO(r.text))
    print(f"  Loaded {len(df):,} rows, columns: {list(df.columns)}")

    # Normalize column names to lowercase
    df.columns = [c.lower().strip() for c in df.columns]

    # Filter to expense rows only
    if "account_type" in df.columns:
        df = df[df["account_type"].str.lower() == "expense"]

    # Identify the fiscal year column
    fy_col = next((c for c in df.columns if "fiscal_year" in c), None)
    amt_col = next((c for c in df.columns if "amount" in c or "actual" in c.lower()), None)

    if not fy_col or not amt_col:
        raise ValueError(f"Could not find expected columns. Got: {list(df.columns)}")

    print(f"  Using columns: fiscal_year='{fy_col}', amount='{amt_col}'")
    df[amt_col] = pd.to_numeric(df[amt_col], errors="coerce").fillna(0)

    by_year = (
        df.groupby(fy_col)[amt_col]
        .sum()
        .reset_index()
        .rename(columns={fy_col: "fiscal_year", amt_col: "total_expenditures"})
        .sort_values("fiscal_year")
    )

    # Convert to dict keyed by fiscal year integer
    result = {
        int(row["fiscal_year"]): round(row["total_expenditures"])
        for _, row in by_year.iterrows()
        if row["total_expenditures"] > 0
    }
    print(f"  Expenditure years: {sorted(result.keys())}")
    return result


def fetch_gdp():
    """Returns dict of {calendar_year: nominal_gdp_millions}"""
    print(f"Fetching FRED NGMP41740 (SD Nominal GDP)...")
    r = requests.get(FRED_GDP_URL, timeout=30)
    r.raise_for_status()
    gdp = {}
    for line in r.text.strip().split("\n")[1:]:
        date, value = line.split(",")
        year = int(date[:4])
        if value.strip() != ".":
            gdp[year] = float(value)
    print(f"  Got {len(gdp)} years of GDP data ({min(gdp)}-{max(gdp)})")
    return gdp


def build_json():
    expenditures = fetch_sd_expenditures()
    gdp = fetch_gdp()

    rows = []
    for fy, exp in sorted(expenditures.items()):
        # Align: FY2024 (ends June 2024) → GDP CY2023
        cal_year = fy - 1
        if cal_year not in gdp:
            print(f"  No GDP data for CY{cal_year} (FY{fy}), skipping")
            continue
        gdp_millions = gdp[cal_year]
        exp_millions = exp / 1_000_000
        rows.append({
            "fiscal_year": fy,
            "label": f"FY{fy}",
            "total_expenditures": exp,
            "expenditures_millions": round(exp_millions, 1),
            "gdp_millions": round(gdp_millions, 1),
            # City spending as % of MSA GDP
            "expenditures_pct_gdp": round(exp_millions / gdp_millions * 100, 2),
        })

    # Index both series to first year
    if rows:
        base_exp = rows[0]["expenditures_millions"]
        base_gdp = rows[0]["gdp_millions"]
        for row in rows:
            row["exp_index"] = round(row["expenditures_millions"] / base_exp * 100, 1)
            row["gdp_index"] = round(row["gdp_millions"] / base_gdp * 100, 1)

    output = {
        "title": "City of San Diego: Expenditures vs. Regional GDP",
        "description": (
            "Compares total city operating expenditures against San Diego MSA nominal GDP. "
            "Both series indexed to 100 at the first year. City expenditures growing faster "
            "than GDP indicates the city is consuming a larger share of the regional economy. "
            "The 'expenditures as % of GDP' line shows this ratio directly."
        ),
        "sources": {
            "expenditures": "City of San Diego Open Data Portal — Operating Actuals (all funds, expense accounts)",
            "gdp": "FRED NGMP41740 — Total Nominal GDP, San Diego-Carlsbad MSA (Bureau of Economic Analysis)",
        },
        "base_year": rows[0]["fiscal_year"] if rows else None,
        "data": rows,
    }

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(output, indent=2))
    print(f"Wrote {len(rows)} rows → {OUTPUT_PATH}")


if __name__ == "__main__":
    build_json()
