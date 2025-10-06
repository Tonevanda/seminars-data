Wikidata mapping helper
=======================

This small helper maps column headers and cell values from the CSV to Wikidata properties (P...) and items (Q...).

Files
- `scripts/map_wikidata.py` - main script. Usage:

  python3 scripts/map_wikidata.py "social media content and misinformation data.csv"

- `requirements.txt` - Python dependencies

Outputs
- `mappings.json` - JSON with column->property candidate and value->item mappings
- `<csv>_with_qids.csv` - augmented CSV adding `<column>_qid` and `<column>_qid_label` columns where available

Notes
- The script uses the public Wikidata API. Rate limiting may apply. It uses simple heuristics and is intended to bootstrap manual review.
