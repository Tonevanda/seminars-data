#!/usr/bin/env python3
"""
Map CSV values to Wikidata QIDs using pywikibot and write a new CSV where values are replaced by QIDs.

Usage:
  python3 scripts/map_wikidata.py "social media content and misinformation data.csv"
"""
import sys
from pathlib import Path
from typing import Dict, Any

import pandas as pd
import pywikibot
from pywikibot.data.api import Request


def create_site():
    # Connect to the Wikidata site
    site = pywikibot.Site("wikidata", "wikidata")
    return site


def wbsearch(site, term: str, language: str = "en", limit: int = 5) -> list:
    params = {
        'action': 'wbsearchentities',
        'format': 'json',
        'language': language,
        'search': term,
        'limit': limit,
        'type': 'item'
    }
    req = Request(site=site, **params)
    data = req.submit()
    return data.get('search', [])


def choose_best(term: str, results: list) -> Dict[str, Any]:
    t = str(term).strip().lower()
    if not results:
        return {}
    for r in results:
        if (r.get('label') or '').strip().lower() == t:
            return r
    for r in results:
        lbl = (r.get('label') or '').strip().lower()
        if lbl.startswith(t) or t.startswith(lbl):
            return r
    return results[0]


def is_numeric_series(s: pd.Series) -> bool:
    try:
        pd.to_numeric(s.dropna())
        return True
    except Exception:
        return False


def should_map_column(name: str, series: pd.Series) -> bool:
    if series.dropna().empty:
        return False
    if is_numeric_series(series):
        return False
    # skip long free text
    avg_len = series.dropna().astype(str).map(len).mean()
    if avg_len > 300:
        return False
    # reasonable cardinality
    if len(series.dropna().unique()) > 1000:
        return False
    return True


def main():
    if len(sys.argv) < 2:
        print("Usage: map_wikidata.py <csv>")
        sys.exit(2)

    csv_path = Path(sys.argv[1]).resolve()
    if not csv_path.exists():
        print(f"CSV file not found: {csv_path}")
        sys.exit(2)

    print(f"Reading CSV: {csv_path}")
    df = pd.read_csv(csv_path)

    site = create_site()

    cache: Dict[str, Any] = {}

    mapped_df = df.copy()

    for col in df.columns:
        series = df[col]
        if not should_map_column(col, series):
            print(f"Skipping column (heuristic): {col}")
            continue
        print(f"Mapping column: {col}")
        unique_vals = sorted([v for v in series.dropna().astype(str).unique()])
        for val in unique_vals:
            key = (col, val)
            if key in cache:
                continue
            term = val.strip()
            if term == "":
                cache[key] = None
                continue
            try:
                results = wbsearch(site, term, language='en', limit=5)
                best = choose_best(term, results)
                if best and best.get('id'):
                    cache[key] = best.get('id')
                else:
                    cache[key] = None
            except Exception as e:
                print(f"Error searching for '{term}' in column '{col}': {e}")
                cache[key] = None

        # Replace values in-place with QIDs where found
        for idx, cell in series.items():
            if pd.isna(cell):
                continue
            key = (col, str(cell))
            qid = cache.get(key)
            if qid:
                mapped_df.at[idx, col] = qid

    out_csv = csv_path.parent / (csv_path.stem + "_qids" + csv_path.suffix)
    mapped_df.to_csv(out_csv, index=False)
    print(f"Wrote mapped CSV to: {out_csv}")


if __name__ == '__main__':
    main()
