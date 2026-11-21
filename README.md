# music-artist-ontology

An OWL ontology of music artists, releases, and professional relationships, populated live from Wikidata and enriched from DBpedia. SPARQL fusion queries pull answers that need both sources at once, and SWRL rules classify artists through a reasoner. Built for the Data Semantics module of my MSc at Queen Mary University of London.

The populated graph: 25 artists (15 solo, 10 bands), 36 releases, 60 record labels, and 87 collaboration relationships, 1,096 triples in total.

## Pipeline

| Step | Script | Produces |
|---|---|---|
| 1. Populate from Wikidata | `populate_basic.py` | `music-artist-relationships-populated.ttl` |
| 2. Enrich from DBpedia | `enrich_from_dbpedia.py` | `music-artist-relationships-enriched.ttl` |
| 3. Query the local graph | `query_local.py` | console tables (discography, genres, labels) |
| 4. Fusion queries | `fusion_queries.py` | 5 queries that require both sources |
| 5. Add SWRL rules | `add_swrl_rules.py` | `music-artist-relationships-advanced.ttl` |

`music-artist-relationships.ttl` is the finished ontology with the SWRL rules already included. Open it directly in Protégé and run Pellet to see the inferred classes light up (ProlificArtist, AwardWinner, CollaborativeArtist).

## Run it

```bash
pip install -r requirements.txt
python populate_basic.py        # hits the Wikidata SPARQL endpoint, ~2-3 min
python enrich_from_dbpedia.py
python query_local.py
python fusion_queries.py
```

Artist selection is seeded by RIAA certification level (Gold / Platinum / Diamond) queried from Wikidata, which gives an objective notability threshold. `artist_mappings.json` maps local artist URIs to their DBpedia resources for the enrichment step.

## What the fusion shows

The two sources complement rather than duplicate: Wikidata is strong on commercial metadata (certifications, chart positions, labels), DBpedia on historical and biographical context (collaborations, genres, instruments). Only 4 of the 25 artists have rich data in both, which is exactly what makes the fusion queries informative.

Known limitation, documented in the report: two of the five SWRL rules (VeteranArtist, MultiGenreArtist) fail to infer under Pellet due to xsd:gYear datatype handling and differentFrom timeout issues.

## Report

`report.pdf` covers the ontology design, the population and enrichment pipeline, the fusion analysis, and the reasoning results with Protégé screenshots.
