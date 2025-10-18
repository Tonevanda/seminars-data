# Social Media Disinformation

This project converts a low FAIRness dataset from [Kaggle](https://www.kaggle.com/datasets/imaadmahmood/social-media-and-misinformation-dataset-2024) into a 5-star dataset.

There are 3 scripts:

- `map_wikidata.py` which maps each entity in the original CSV dataset to a wikidata entry representing that entity;
- `map_topic_tags.py` which does the same thing but just for the topic tags column, due to the way they are formatted;
- `convert_csv_to_rdf.py` which converts the final, harmonized CSV dataset into an RDF representation, in this case we chose JSON-LD.

Below is an excerpt of an example JSON-LD with the structure we defined:

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

## Developed by

- João Lourenço
- João das Neves