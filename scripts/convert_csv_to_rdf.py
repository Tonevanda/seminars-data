#!/usr/bin/env python3
"""
Convert a CSV with Wikidata QIDs into Turtle and JSON-LD using rdflib.

Usage:
  python3 scripts/convert_csv_to_rdf.py "social media content and misinformation data_qids.csv"

Behavior:
 - If `mappings.json` exists it will use mapped property IDs (P...) for columns when available.
 - For columns with QIDs as values, it will emit triples linking a generated subject URI to the QID (as a wikidata entity URI).
 - Numeric and literal columns are emitted as literals.
 - Writes `<csv>_qids.jsonld` in the same folder.
"""
import json
import sys
import re
from pathlib import Path
from typing import Dict
from urllib.parse import quote

import pandas as pd
from rdflib import Graph, Namespace, URIRef, Literal
from rdflib.namespace import RDF, XSD

WIKIDATA = Namespace("http://www.wikidata.org/entity/")
WD_PROP = Namespace("http://www.wikidata.org/prop/direct/")
SCHEMA = Namespace("http://schema.org/")


def load_mappings(mappings_path: Path) -> Dict[str, str]:
    if not mappings_path.exists():
        return {}
    data = json.loads(mappings_path.read_text(encoding="utf-8"))
    prop_map = {}
    for col, info in data.get("columns", {}).items():
        pm = info.get("property_match")
        if isinstance(pm, dict) and pm.get("id"):
            prop_map[col] = pm.get("id")
    return prop_map


def qid_to_uri(qid: str) -> URIRef:
    return URIRef(WIKIDATA + qid)


def prop_id_to_uri(pid: str) -> URIRef:
    # pid like P123 -> use direct property namespace
    return URIRef(WD_PROP + pid)


def make_subject(base: str, row_idx: int) -> URIRef:
    # Create a subject URI for each row
    return URIRef(f"{base}row/{row_idx}")


def main():
    if len(sys.argv) < 2:
        print("Usage: convert_csv_to_rdf.py <csv_qids>")
        sys.exit(2)

    csv_path = Path(sys.argv[1]).resolve()
    if not csv_path.exists():
        print(f"CSV not found: {csv_path}")
        sys.exit(2)

    # URL-encode the dataset name so the subject URIs are valid
    safe_stem = quote(csv_path.stem, safe="")
    base_uri = f"https://www.kaggle.com/datasets/imaadmahmood/social-media-and-misinformation-dataset-2024/{safe_stem}/"

    df = pd.read_csv(csv_path)

    mappings_path = csv_path.parent / "mappings.json"
    prop_map = load_mappings(mappings_path)

    g = Graph()
    g.bind("wd", WIKIDATA)
    g.bind("wdt", WD_PROP)
    g.bind("schema", SCHEMA)

    for idx, row in df.iterrows():
        subj = make_subject(base_uri, idx)
        g.add((subj, RDF.type, SCHEMA.SocialMediaPosting))
        for col in df.columns:
            val = row[col]
            if pd.isna(val):
                continue
            # if value looks like a QID
            sval = str(val).strip()
            # treat only exact QID tokens (e.g. Q1390577) as entity URIs
            if re.fullmatch(r"Q\d+", sval):
                # If we have a mapped property for the column, use it, else use schema:about
                pid = prop_map.get(col)
                if pid:
                    pred = prop_id_to_uri(pid)
                else:
                    pred = SCHEMA.about
                g.add((subj, pred, qid_to_uri(sval)))
            else:
                # literal property: if mapping suggests a property use it otherwise schema:additionalProperty
                pid = prop_map.get(col)
                pred = prop_id_to_uri(pid) if pid else SCHEMA.additionalProperty
                # try to coerce numeric
                try:
                    if sval.isdigit():
                        lit = Literal(int(sval), datatype=XSD.integer)
                    else:
                        lit = Literal(sval)
                except Exception:
                    lit = Literal(sval)
                g.add((subj, pred, lit))

    out_jsonld = csv_path.parent / (csv_path.stem + ".jsonld")

    # rdflib's json-ld serializer
    g.serialize(destination=str(out_jsonld), format="json-ld", indent=2)

    print(f"Wrote JSON-LD: {out_jsonld}")


if __name__ == '__main__':
    main()
