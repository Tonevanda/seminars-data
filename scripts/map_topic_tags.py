#!/usr/bin/env python3
"""
Map semicolon-separated tokens in `Topic_Tags` to Wikidata QIDs using pywikibot.

Writes a new CSV with the `Topic_Tags` column replaced by semicolon-joined QIDs when available.
"""
import sys
from pathlib import Path
from typing import Dict

import pandas as pd
import pywikibot
from pywikibot.data.api import Request


def load_mappings(mappings_path: Path) -> Dict[str, Dict[str, str]]:
    if not mappings_path.exists():
        return {}
    import json
    data = json.loads(mappings_path.read_text(encoding='utf-8'))
    return data.get('values', {})


def create_site():
    return pywikibot.Site('wikidata', 'wikidata')


def wbsearch(site, term: str, limit: int = 5):
    params = {
        'action': 'wbsearchentities',
        'format': 'json',
        'language': 'en',
        'search': term,
        'limit': limit,
        'type': 'item'
    }
    req = Request(site=site, **params)
    data = req.submit()
    return data.get('search', [])


def choose_best(term: str, results: list):
    t = term.strip().lower()
    if not results:
        return None
    for r in results:
        if (r.get('label') or '').strip().lower() == t:
            return r.get('id')
    for r in results:
        lbl = (r.get('label') or '').strip().lower()
        if lbl.startswith(t) or t.startswith(lbl):
            return r.get('id')
    return results[0].get('id')


def map_tag(tag: str, cache_values: dict, site) -> str:
    tag_clean = tag.strip()
    if not tag_clean:
        return ''
    # try cache from mappings.json
    # mappings.json structure under 'values' keyed by column name then value
    col_cache = cache_values.get('Topic_Tags', {})
    entry = col_cache.get(tag_clean)
    if entry and entry.get('qid'):
        return entry.get('qid')
    # fallback to pywikibot search
    try:
        res = wbsearch(site, tag_clean, limit=5)
        q = choose_best(tag_clean, res)
        return q or ''
    except Exception:
        return ''


def main():
    if len(sys.argv) < 2:
        print('Usage: map_topic_tags.py <csv_qids>')
        sys.exit(2)

    csv_path = Path(sys.argv[1]).resolve()
    if not csv_path.exists():
        print(f'CSV not found: {csv_path}')
        sys.exit(2)

    df = pd.read_csv(csv_path)
    mappings = load_mappings(csv_path.parent / 'mappings.json')
    site = create_site()

    mapped = df.copy()
    mapped_count = 0
    total_tokens = 0
    unmapped = set()

    for idx, row in df.iterrows():
        val = row.get('Topic_Tags')
        if pd.isna(val) or str(val).strip() == '':
            continue
        parts = [p.strip() for p in str(val).split(';') if p.strip()]
        total_tokens += len(parts)
        qids = []
        for p in parts:
            q = map_tag(p, mappings, site)
            if q:
                qids.append(q)
                mapped_count += 1
            else:
                unmapped.add(p)
        mapped.at[idx, 'Topic_Tags'] = ';'.join(qids)

    out_csv = csv_path.parent / (csv_path.stem + '_topic_qids' + csv_path.suffix)
    mapped.to_csv(out_csv, index=False)

    print(f'Wrote: {out_csv}')
    print(f'Tokens total: {total_tokens}, mapped: {mapped_count}, unmapped examples: {list(unmapped)[:20]}')


if __name__ == '__main__':
    main()
