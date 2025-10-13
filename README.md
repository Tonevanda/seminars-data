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

Example structure of JSON-LD object representing a social media post

```jsonld
  {
    "@context": {
      "schema": "www.schema.org",
      "wd": "www.wikidata.org/entity/"
    },
    "@id": "https://www.kaggle.com/datasets/imaadmahmood/social-media-and-misinformation-dataset-2024/social%20media%20content%20and%20misinformation%20data_qids/row/23",
    "@type": "http://schema.org/SocialMediaPosting",
    "schema:about": [
      { "@id": "wd:Q209330" },
      { "@id": "wd:Q21491634" },
      { "@id": "wd:Q1860" },
      { "@id": "wd:Q16" },
      { "@id": "wd:Q12147" },
      { "@id": "wd:Q7817" }
    ],
    "schema:identifier": "ig_024",
    "schema:datePublished": { "@type": "xsd:dateTime", "@value": "2024-08-14T16:33:27Z" },
    "schema:interactionStatistic": [
      {
        "@type": "schema:InteractionCounter",
        "schema:interactionType": "schema:LikeAction",
        "schema:userInteractionCount": 2345
      },
      {
        "@type": "schema:InteractionCounter",
        "schema:interactionType": "schema:CommentAction",
        "schema:userInteractionCount": 345
      },
      {
        "@type": "schema:InteractionCounter",
        "schema:interactionType": "schema:ShareAction",
        "schema:userInteractionCount": 456
      }
    ],
    "schema:text": "Mental health awareness is so important - sharing resources for anyone struggling",
    "schema:verified": "Verified",
    "schema:language": "en",
    "schema:sentimentScore": 0.94
  }
```