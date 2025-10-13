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

```json
{
    "@context": {
      "schema": "www.schema.org",
      "wd": "www.wikidata.org/entity/",
      "xsd": "http://www.w3.org/2001/XMLSchema#"
    },
    "@id": "https://www.kaggle.com/datasets/imaadmahmood/social-media-and-misinformation-dataset-2024/social%20media%20content%20and%20misinformation%20data_qids/ig_024",

    "@type": "http://schema.org/SocialMediaPosting",

    // Topic Tags
    "schema:about": [
      { "@id": "wd:Q317309" },
      { "@id": "wd:Q4338318" },
      { "@id": "wd:Q1058733" }
    ],

    "schema:identifier": "ig_024",
    "schema:datePublished": { 
      "@type": "xsd:dateTime", 
      "@value": "2024-08-14T16:33:27Z" 
    },
    "my:platform": "Instagram",
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
      },
      {
        "@type": "schema:InteractionCounter",
        "schema:interactionType": "schema:FollowAction",
        "schema:userInteractionCount": 15420
      }
    ],
    "schema:text": "Mental health awareness is so important - sharing resources for anyone struggling",
    "schema:inLanguage": "wd:Q1860",
    "schema:contentLocation": "Q16",
    "schema:contentRating": "Verified",

    "my:engagement": 0.94,
    "my:misinformationFlag": {
      "@type": "xsd:boolean",
      "@value": true
    },

    "my:factCheckSource": {
      "@id": "wd:Q130879"
    },
    
    "my:sentimentScore": {
      "@type": "xsd:float",
      "@value": "0.23"
    },
    
    "my:toxicityScore": {
      "@type": "xsd:float",
      "@value": "0.15"
    },
    
    "my:politicalLeaning": "Conservative",
    "my:hasExternalLink": {
      "@type": "xsd:boolean",
      "@value": false
    },
  
    "my:viralScore": {
      "@type": "xsd:float",
      "@value": "0.68"
    },
    
    "my:moderationAction": "Warning_Label"
}
```