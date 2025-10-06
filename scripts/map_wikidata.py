#!/usr/bin/env python3
"""
Map values from a CSV to Wikidata QIDs and column headers to Wikidata properties.

Outputs:
 - mappings.json : mapping for columns -> property and values -> item matches
 - <original_csv_basename>_with_qids.csv : augmented CSV with extra _qid/_label columns

Usage: python3 scripts/map_wikidata.py ../"social media content and misinformation data.csv"
"""
import sys
import time
import json
from pathlib import Path
from typing import Dict, List, Any

import pandas as pd
import requests
from requests.adapters import HTTPAdapter, Retry
from tqdm import tqdm

WIKIDATA_API = "https://www.wikidata.org/w/api.php"


def create_session() -> requests.Session:
    session = requests.Session()
    retries = Retry(total=3, backoff_factor=0.3, status_forcelist=(429, 500, 502, 503, 504))
    session.mount("https://", HTTPAdapter(max_retries=retries))
    # Set a descriptive user-agent to comply with Wikimedia policy
    session.headers.update({"User-Agent": "seminars-wikidata-mapper/1.0 (contact: dev@example.com)"})
    return session


_SESSION = create_session()


def wbsearch_entities(search: str, language: str = "en", limit: int = 5, entity_type: str = "item") -> List[Dict[str, Any]]:
    params = {
        "action": "wbsearchentities",
        "format": "json",
        "language": language,
        "search": search,
        "limit": limit,
        "type": entity_type,
    }
    r = _SESSION.get(WIKIDATA_API, params=params, timeout=30)
    r.raise_for_status()
    data = r.json()
    return data.get("search", [])


def choose_best_match(term: str, results: List[Dict[str, Any]]) -> Dict[str, Any]:
    term_lower = str(term).strip().lower()
    if not results:
        return {}
    # Prefer exact label matches
    for res in results:
        label = (res.get("label") or "").strip().lower()
        if label == term_lower:
            return {"id": res.get("id"), "label": res.get("label"), "description": res.get("description"), "match_type": "exact"}
    # Prefer label startswith
    for res in results:
        label = (res.get("label") or "").strip().lower()
        if label.startswith(term_lower) or term_lower.startswith(label):
            return {"id": res.get("id"), "label": res.get("label"), "description": res.get("description"), "match_type": "prefix"}
    # fallback to first
    res = results[0]
    return {"id": res.get("id"), "label": res.get("label"), "description": res.get("description"), "match_type": "first"}


def is_probably_numeric_series(s: pd.Series) -> bool:
    try:
        _ = pd.to_numeric(s.dropna())
        return True
    except Exception:
        return False


def should_map_column(col: str, series: pd.Series) -> bool:
    """Heuristics: map columns that are categorical/short strings with limited unique values."""
    if series.dropna().empty:
        return False
    # skip numeric and datetime-like
    if is_probably_numeric_series(series):
        return False
    # skip very high cardinality free text
    unique = series.dropna().unique()
    if len(unique) > 500:
        return False
    # skip columns where average length is very long
    avg_len = series.dropna().astype(str).map(len).mean()
    if avg_len > 300:
        return False
    return True


def map_column_property(col_name: str) -> Dict[str, Any]:
    """Try to find a matching Wikidata property for a column header."""
    try:
        results = wbsearch_entities(col_name, entity_type="property", limit=5)
        best = choose_best_match(col_name, results)
        if best:
            best["source_search"] = col_name
        return best
    except Exception as e:
        return {"error": str(e)}


def map_values(values: List[str], limit: int = 5) -> Dict[str, Any]:
    mapping = {}
    for v in tqdm(sorted(values), desc="values"):
        v_str = str(v).strip()
        if v_str == "" or v_str.lower() in {"none", "nan"}:
            mapping[v] = {"qid": None, "label": None, "confidence": "empty"}
            continue
        try:
            results = wbsearch_entities(v_str, entity_type="item", limit=limit)
            best = choose_best_match(v_str, results)
            if best:
                # assign simple confidence metric
                conf = "high" if best.get("match_type") == "exact" else "medium"
                mapping[v] = {"qid": best.get("id"), "label": best.get("label"), "description": best.get("description"), "confidence": conf}
            else:
                mapping[v] = {"qid": None, "label": None, "confidence": "none"}
        except Exception as e:
            mapping[v] = {"qid": None, "label": None, "confidence": "error", "error": str(e)}
        time.sleep(0.08)
    return mapping


def main():
    if len(sys.argv) < 2:
        print("Usage: map_wikidata.py <path-to-csv>")
        sys.exit(2)

    csv_path = Path(sys.argv[1]).resolve()
    if not csv_path.exists():
        print(f"CSV not found: {csv_path}")
        sys.exit(2)

    df = pd.read_csv(csv_path)

    mappings = {"columns": {}, "values": {}}

    # Process columns one by one
    for col in df.columns:
        series = df[col]
        col_entry = {"should_map": False}
        if should_map_column(col, series):
            col_entry["should_map"] = True
            prop = map_column_property(col)
            col_entry["property_match"] = prop
            # special handling for tag-like columns
            if col.lower() in {"topic_tags", "topic_tags", "tags"}:
                # collect tokenized tags
                tokens = set()
                for cell in series.dropna().astype(str):
                    for t in [x.strip() for x in cell.split(";") if x.strip()]:
                        tokens.add(t)
                mappings["values"][col] = map_values(list(tokens))
            else:
                unique_vals = set(series.dropna().astype(str).unique())
                # if boolean-like
                if all(s.lower() in {"true", "false", "yes", "no", "none", "nan"} for s in unique_vals):
                    # map simple boolean labels to wikidata items True/False? leave as labels
                    mappings["values"][col] = {v: {"qid": None, "label": v, "confidence": "boolean_or_literal"} for v in unique_vals}
                else:
                    mappings["values"][col] = map_values(list(unique_vals))
        else:
            col_entry["should_map"] = False
            col_entry["reason_skipped"] = "heuristic_skip_numeric_or_high_cardinality_or_long_text"
        mappings["columns"][col] = col_entry

    # Save mappings
    out_dir = csv_path.parent
    mappings_path = out_dir / "mappings.json"
    with mappings_path.open("w", encoding="utf-8") as fh:
        json.dump(mappings, fh, indent=2, ensure_ascii=False)

    # Create augmented CSV
    out_df = df.copy()
    for col, valmap in mappings.get("values", {}).items():
        # Add qid and label columns
        qid_col = f"{col}_qid"
        label_col = f"{col}_qid_label"
        out_df[qid_col] = None
        out_df[label_col] = None
        series = df[col].astype(str)
        for idx, cell in series.items():
            if pd.isna(cell) or str(cell).strip() == "":
                continue
            if col.lower() in {"topic_tags", "topic_tags", "tags"}:
                parts = [p.strip() for p in str(cell).split(";") if p.strip()]
                qids = []
                labels = []
                for p in parts:
                    m = valmap.get(p)
                    if m and m.get("qid"):
                        qids.append(m.get("qid"))
                        labels.append(m.get("label"))
                out_df.at[idx, qid_col] = ";".join(qids) if qids else None
                out_df.at[idx, label_col] = ";".join(labels) if labels else None
            else:
                m = valmap.get(str(cell))
                if not m:
                    # try matching lowercase key
                    m = valmap.get(str(cell).strip()) or valmap.get(str(cell).lower())
                if m and m.get("qid"):
                    out_df.at[idx, qid_col] = m.get("qid")
                    out_df.at[idx, label_col] = m.get("label")

    out_csv = out_dir / (csv_path.stem + "_with_qids" + csv_path.suffix)
    out_df.to_csv(out_csv, index=False)

    print(f"Wrote mappings to: {mappings_path}")
    print(f"Wrote augmented CSV to: {out_csv}")


if __name__ == "__main__":
    main()
