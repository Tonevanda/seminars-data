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

    # Build JSON-LD per README example: top-level @context and @graph array
    values_map = {}
    # load values mapping (if mappings.json has 'values' section)
    mappings_values_path = csv_path.parent / "mappings.json"
    if mappings_values_path.exists():
        try:
            mv = json.loads(mappings_values_path.read_text(encoding="utf-8"))
            values_map = mv.get("values", {})
        except Exception:
            values_map = {}

    context = {
        "schema": "http://schema.org/",
        "wd": "http://www.wikidata.org/entity/",
        "xsd": "http://www.w3.org/2001/XMLSchema#"
    }

    graph = []

    def qid_label(col: str, qid: str):
        colvals = values_map.get(col, {})
        for orig, info in colvals.items():
            if info.get("qid") == qid:
                return info.get("label")
        return None

    for idx, row in df.iterrows():
        post_id = row.get("Post_ID") if not pd.isna(row.get("Post_ID")) else f"row/{idx}"
        subj_id = f"{base_uri}{quote(str(post_id), safe='') }"
        obj = {"@id": subj_id, "@type": "http://schema.org/SocialMediaPosting"}

        # schema:about from Topic_Tags
        topic = row.get("Topic_Tags")
        if not pd.isna(topic) and str(topic).strip():
            parts = [p.strip() for p in str(topic).split(";") if p.strip()]
            about = [{"@id": f"wd:{p}"} for p in parts if re.fullmatch(r"Q\d+", p)]
            if about:
                obj["schema:about"] = about

        # identifier
        if post_id:
            obj["schema:identifier"] = str(post_id)

        # datePublished
        ts = row.get("Timestamp")
        if not pd.isna(ts) and str(ts).strip():
            obj["schema:datePublished"] = {"@type": "xsd:dateTime", "@value": str(ts)}

        # platform (label preferred)
        platform = row.get("Platform")
        if not pd.isna(platform):
            s = str(platform).strip()
            if re.fullmatch(r"Q\d+", s):
                lbl = qid_label("Platform", s)
                obj["my:platform"] = lbl if lbl else s
            else:
                obj["my:platform"] = s

        # interactionStatistic
        interactions = []
        like = row.get("Like_Count")
        if not pd.isna(like):
            interactions.append({"@type": "schema:InteractionCounter", "schema:interactionType": "schema:LikeAction", "schema:userInteractionCount": int(like)})
        comment = row.get("Comment_Count")
        if not pd.isna(comment):
            interactions.append({"@type": "schema:InteractionCounter", "schema:interactionType": "schema:CommentAction", "schema:userInteractionCount": int(comment)})
        share = row.get("Share_Count")
        if not pd.isna(share):
            interactions.append({"@type": "schema:InteractionCounter", "schema:interactionType": "schema:ShareAction", "schema:userInteractionCount": int(share)})
        followers = row.get("User_Followers")
        if not pd.isna(followers):
            try:
                interactions.append({"@type": "schema:InteractionCounter", "schema:interactionType": "schema:FollowAction", "schema:userInteractionCount": int(followers)})
            except Exception:
                pass
        if interactions:
            obj["schema:interactionStatistic"] = interactions

        # text
        text = row.get("Content_Text")
        if not pd.isna(text):
            obj["schema:text"] = str(text)

        # language
        lang = row.get("Language")
        if not pd.isna(lang) and re.fullmatch(r"Q\d+", str(lang)):
            obj["schema:inLanguage"] = f"wd:{lang}"

        # contentLocation
        country = row.get("Country")
        if not pd.isna(country) and re.fullmatch(r"Q\d+", str(country)):
            obj["schema:contentLocation"] = f"wd:{country}"

        # contentRating / verification
        ver = row.get("Verification_Status")
        if not pd.isna(ver):
            obj["schema:contentRating"] = str(ver)

        # engagement
        eng = row.get("Engagement_Score")
        if not pd.isna(eng):
            try:
                obj["my:engagement"] = float(eng)
            except Exception:
                obj["my:engagement"] = eng

        # misinformation flag
        mis = row.get("Misinformation_Flag")
        if not pd.isna(mis):
            mstr = str(mis).strip()
            if mstr.lower() in ("true", "false"):
                obj["my:misinformationFlag"] = {"@type": "xsd:boolean", "@value": mstr.lower() == "true"}
            else:
                obj["my:misinformationFlag"] = str(mis)

        # fact check source
        fcs = row.get("Fact_Check_Source")
        if not pd.isna(fcs):
            s = str(fcs).strip()
            if re.fullmatch(r"Q\d+", s):
                obj["my:factCheckSource"] = {"@id": f"wd:{s}"}
            else:
                obj["my:factCheckSource"] = {"@id": s}

        # sentiment and toxicity
        sent = row.get("Sentiment_Score")
        if not pd.isna(sent):
            obj["my:sentimentScore"] = {"@type": "xsd:float", "@value": str(sent)}
        tox = row.get("Toxicity_Score")
        if not pd.isna(tox):
            obj["my:toxicityScore"] = {"@type": "xsd:float", "@value": str(tox)}

        # political leaning
        pl = row.get("Political_Leaning")
        if not pd.isna(pl):
            obj["my:politicalLeaning"] = str(pl)

        # hasExternalLink
        hel = row.get("Has_External_Link")
        if not pd.isna(hel):
            hstr = str(hel).strip()
            if hstr.lower() in ("true", "false"):
                obj["my:hasExternalLink"] = {"@type": "xsd:boolean", "@value": hstr.lower() == "true"}
            else:
                obj["my:hasExternalLink"] = str(hel)

        # viralScore
        vs = row.get("Viral_Score")
        if not pd.isna(vs):
            obj["my:viralScore"] = {"@type": "xsd:float", "@value": str(vs)}

        # moderationAction
        ma = row.get("Moderation_Action")
        if not pd.isna(ma):
            obj["my:moderationAction"] = str(ma)

        graph.append(obj)

    out_jsonld = csv_path.parent / (csv_path.stem + ".jsonld")

    jsonld_doc = {"@context": context, "@graph": graph}
    out_jsonld.write_text(json.dumps(jsonld_doc, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"Wrote JSON-LD: {out_jsonld}")


if __name__ == '__main__':
    main()
