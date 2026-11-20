#!/usr/bin/env python3
"""
enrich_from_dbpedia.py - Step 2 of Intermediate Task
Enriches ontology with DBpedia data for artist relationships and additional metadata
"""

import json
import rdflib
from rdflib import Graph, Namespace, URIRef, Literal, RDF
from SPARQLWrapper import SPARQLWrapper, JSON
from datetime import datetime
import urllib.parse
import ssl
import urllib.request

# Create SSL context that doesn't verify certificates
ssl._create_default_https_context = ssl._create_unverified_context

# Namespaces
LOCAL = Namespace("http://www.semanticweb.org/adinsegall/ontologies/2025/4/music-artist-relationships#")
MO = Namespace("http://purl.org/ontology/mo/")
DBO = Namespace("http://dbpedia.org/ontology/")
DBR = Namespace("http://dbpedia.org/resource/")
FOAF = Namespace("http://xmlns.com/foaf/0.1/")
XSD = Namespace("http://www.w3.org/2001/XMLSchema#")

# DBpedia endpoint
DBPEDIA_ENDPOINT = "http://dbpedia.org/sparql"

def load_mappings(filename="artist_mappings.json"):
    """Load artist mappings from JSON file."""
    with open(filename, 'r') as f:
        return json.load(f)

def create_sparql_wrapper():
    """Create configured SPARQLWrapper instance."""
    sparql = SPARQLWrapper(DBPEDIA_ENDPOINT)
    sparql.setReturnFormat(JSON)
    sparql.addCustomHttpHeader("User-Agent", "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)")
    sparql.addCustomHttpHeader("Accept", "application/sparql-results+json")
    sparql.setTimeout(30)
    return sparql

def query_artist_relationships(dbpedia_uri):
    """Query DBpedia for artist relationships and collaborations."""
    
    query = f"""
    SELECT DISTINCT ?property ?relatedArtist ?relatedName WHERE {{
        {{
            # Associated bands/artists
            <{dbpedia_uri}> dbo:associatedBand ?relatedArtist .
            ?relatedArtist rdfs:label ?relatedName .
            BIND("associatedBand" AS ?property)
        }}
        UNION {{
            # Associated musical artists
            <{dbpedia_uri}> dbo:associatedMusicalArtist ?relatedArtist .
            ?relatedArtist rdfs:label ?relatedName .
            BIND("associatedMusicalArtist" AS ?property)
        }}
        UNION {{
            # Influenced by
            <{dbpedia_uri}> dbo:influencedBy ?relatedArtist .
            ?relatedArtist rdfs:label ?relatedName .
            BIND("influencedBy" AS ?property)
        }}
        UNION {{
            # Influenced (inverse)
            ?relatedArtist dbo:influencedBy <{dbpedia_uri}> .
            ?relatedArtist rdfs:label ?relatedName .
            BIND("influenced" AS ?property)
        }}
        FILTER(LANG(?relatedName) = "en" || LANG(?relatedName) = "")
    }}
    """
    
    sparql = create_sparql_wrapper()
    sparql.setQuery(query)
    
    try:
        results = sparql.query().convert()
        return results['results']['bindings']
    except Exception as e:
        print(f"Error querying relationships: {e}")
        return []

def query_artist_metadata(dbpedia_uri):
    """Query DBpedia for additional artist metadata."""
    
    query = f"""
    SELECT DISTINCT ?property ?value WHERE {{
        {{
            # Genres
            <{dbpedia_uri}> dbo:genre ?genreUri .
            ?genreUri rdfs:label ?value .
            BIND("genre" AS ?property)
        }}
        UNION {{
            # Record labels
            <{dbpedia_uri}> dbo:recordLabel ?labelUri .
            ?labelUri rdfs:label ?value .
            BIND("recordLabel" AS ?property)
        }}
        UNION {{
            # Instruments
            <{dbpedia_uri}> dbo:instrument ?instrumentUri .
            ?instrumentUri rdfs:label ?value .
            BIND("instrument" AS ?property)
        }}
        UNION {{
            # Birth date
            <{dbpedia_uri}> dbo:birthDate ?value .
            BIND("birthDate" AS ?property)
        }}
        UNION {{
            # Active years
            <{dbpedia_uri}> dbo:activeYearsStartYear ?value .
            BIND("activeYearsStart" AS ?property)
        }}
        FILTER(!BOUND(?value) || LANG(?value) = "en" || LANG(?value) = "")
    }}
    """
    
    sparql = create_sparql_wrapper()
    sparql.setQuery(query)
    
    try:
        results = sparql.query().convert()
        return results['results']['bindings']
    except Exception as e:
        print(f"Error querying metadata: {e}")
        return []

def create_local_uri_from_name(name):
    """Create local URI from artist name."""
    # Replace spaces with underscores, remove special characters
    uri_name = name.replace(' ', '_').replace("'", "")
    return LOCAL[uri_name]

def enrich_ontology(ontology_file, mappings, output_file):
    """Enrich ontology with DBpedia data."""
    
    # Load existing ontology
    g = Graph()
    g.parse(ontology_file, format="turtle")
    
    # Bind namespaces
    g.bind("", LOCAL)
    g.bind("mo", MO)
    g.bind("dbo", DBO)
    g.bind("foaf", FOAF)
    
    # Statistics
    stats = {
        'relationships_added': 0,
        'genres_added': 0,
        'labels_added': 0,
        'metadata_added': 0,
        'artists_enriched': 0
    }
    
    print("\nEnriching artists from DBpedia...")
    print("-" * 80)
    
    for mapping in mappings:
        if mapping['exists'] and mapping['needs_enrichment']:
            artist_name = mapping['name']
            local_uri = LOCAL[mapping['local_uri']]
            dbpedia_uri = mapping['dbpedia_uri']
            
            print(f"\n{artist_name}:")
            artist_enriched = False
            
            # Query relationships
            relationships = query_artist_relationships(dbpedia_uri)
            for rel in relationships:
                prop = rel['property']['value']
                related_uri = rel['relatedArtist']['value']
                related_name = rel['relatedName']['value']
                
                # Create local URI for related artist
                related_local_uri = create_local_uri_from_name(related_name)
                
                # Add related artist if not exists
                if (related_local_uri, RDF.type, MO.MusicArtist) not in g:
                    g.add((related_local_uri, RDF.type, MO.MusicArtist))
                    g.add((related_local_uri, LOCAL.name, Literal(related_name, datatype=XSD.string)))
                    g.add((related_local_uri, LOCAL.dbpediaUri, Literal(related_uri, datatype=XSD.anyURI)))
                
                # Add relationship
                if prop == "associatedBand" or prop == "associatedMusicalArtist":
                    g.add((local_uri, LOCAL.collaboratedWith, related_local_uri))
                    g.add((related_local_uri, LOCAL.collaboratedWith, local_uri))  # Symmetric
                    print(f"  + Collaborated with: {related_name}")
                    stats['relationships_added'] += 2
                    artist_enriched = True
                elif prop == "influencedBy":
                    g.add((local_uri, LOCAL.influencedBy, related_local_uri))
                    print(f"  + Influenced by: {related_name}")
                    stats['relationships_added'] += 1
                    artist_enriched = True
                elif prop == "influenced":
                    g.add((related_local_uri, LOCAL.influencedBy, local_uri))
                    print(f"  + Influenced: {related_name}")
                    stats['relationships_added'] += 1
                    artist_enriched = True
            
            # Query metadata
            metadata = query_artist_metadata(dbpedia_uri)
            for data in metadata:
                prop = data['property']['value']
                value = data['value']['value']
                
                if prop == "genre":
                    # Extract genre name from URI or use label
                    if value.startswith("http://"):
                        genre_name = value.split('/')[-1].replace('_', ' ')
                    else:
                        genre_name = value
                    
                    # Check if genre already exists
                    existing_genres = list(g.objects(local_uri, LOCAL.genre))
                    if not any(str(g) == genre_name for g in existing_genres):
                        g.add((local_uri, LOCAL.genre, Literal(genre_name, datatype=XSD.string)))
                        print(f"  + Genre: {genre_name}")
                        stats['genres_added'] += 1
                        artist_enriched = True
                
                elif prop == "recordLabel":
                    # Create label URI
                    label_name = value.split('/')[-1].replace('_', ' ') if value.startswith("http://") else value
                    label_uri = LOCAL[label_name.replace(' ', '_')]
                    
                    # Add label if not exists
                    if (label_uri, RDF.type, MO.Label) not in g:
                        g.add((label_uri, RDF.type, MO.Label))
                        g.add((label_uri, LOCAL.name, Literal(label_name, datatype=XSD.string)))
                    
                    # Add artist-label relationship
                    g.add((local_uri, LOCAL.hasRecordLabel, label_uri))
                    print(f"  + Record Label: {label_name}")
                    stats['labels_added'] += 1
                    artist_enriched = True
                
                elif prop == "instrument":
                    instrument_name = value.split('/')[-1].replace('_', ' ') if value.startswith("http://") else value
                    g.add((local_uri, LOCAL.playsInstrument, Literal(instrument_name, datatype=XSD.string)))
                    print(f"  + Instrument: {instrument_name}")
                    stats['metadata_added'] += 1
                    artist_enriched = True
                
                elif prop == "birthDate":
                    g.add((local_uri, LOCAL.birthDate, Literal(value, datatype=XSD.date)))
                    print(f"  + Birth Date: {value}")
                    stats['metadata_added'] += 1
                    artist_enriched = True
                
                elif prop == "activeYearsStart":
                    g.add((local_uri, LOCAL.activeYearsStart, Literal(value, datatype=XSD.gYear)))
                    print(f"  + Active Since: {value}")
                    stats['metadata_added'] += 1
                    artist_enriched = True
            
            if artist_enriched:
                stats['artists_enriched'] += 1
            else:
                print("  (No additional data found)")
    
    # Save enriched ontology
    g.serialize(destination=output_file, format="turtle")
    


    # Print summary
    print("\n" + "="*80)
    print("ENRICHMENT SUMMARY")
    print("="*80)
    print(f"Artists enriched: {stats['artists_enriched']}")
    print(f"Relationships added: {stats['relationships_added']}")
    print(f"Genres added: {stats['genres_added']}")
    print(f"Record labels added: {stats['labels_added']}")
    print(f"Other metadata added: {stats['metadata_added']}")
    print(f"\nEnriched ontology saved to: {output_file}")


def enrich_contemporary_artists():
    """Quick enrichment for artists that have Wikidata releases"""
    g = Graph()
    g.parse("music-artist-relationships-enriched.ttl", format="turtle")
    g.bind("", LOCAL)
    g.bind("mo", MO)
    
    # Artists that ALREADY have releases from Wikidata
    contemporary_artists = [
        ("Taylor_Swift", "http://dbpedia.org/resource/Taylor_Swift"),
        ("Justin_Bieber", "http://dbpedia.org/resource/Justin_Bieber"),
        ("Bob_Dylan", "http://dbpedia.org/resource/Bob_Dylan"),
        ("Paul_McCartney", "http://dbpedia.org/resource/Paul_McCartney")
    ]
    
    sparql = create_sparql_wrapper()
    
    for local_name, dbpedia_uri in contemporary_artists:
        local_uri = LOCAL[local_name]
        print(f"\nEnriching {local_name} with DBpedia data...")
        
        # Get everything we can
        query = f"""
        SELECT DISTINCT ?prop ?value WHERE {{
            {{
                <{dbpedia_uri}> dbo:associatedMusicalArtist ?value .
                BIND("collab" AS ?prop)
            }} UNION {{
                <{dbpedia_uri}> dbo:associatedBand ?value .
                BIND("collab" AS ?prop)
            }} UNION {{
                <{dbpedia_uri}> dbo:genre ?value .
                BIND("genre" AS ?prop)
            }} UNION {{
                <{dbpedia_uri}> dbo:recordLabel ?value .
                BIND("label" AS ?prop)
            }} UNION {{
                <{dbpedia_uri}> dbo:birthDate ?value .
                BIND("birthDate" AS ?prop)
            }} UNION {{
                <{dbpedia_uri}> dbo:activeYearsStartYear ?value .
                BIND("activeStart" AS ?prop)
            }}
        }}
        """
        
        sparql.setQuery(query)
        try:
            results = sparql.query().convert()
            for result in results['results']['bindings']:
                prop = result['prop']['value']
                value = result['value']['value']
                
                if prop == "collab":
                    collab_name = value.split('/')[-1].replace('_', ' ')
                    collab_uri = LOCAL[collab_name.replace(' ', '_')]
                    if (collab_uri, RDF.type, MO.MusicArtist) not in g:
                        g.add((collab_uri, RDF.type, MO.MusicArtist))
                        g.add((collab_uri, LOCAL.name, Literal(collab_name, datatype=XSD.string)))
                    g.add((local_uri, LOCAL.collaboratedWith, collab_uri))
                    print(f"  + Collab: {collab_name}")
                    
                elif prop == "genre":
                    genre_name = value.split('/')[-1].replace('_', ' ')
                    g.add((local_uri, LOCAL.genre, Literal(genre_name, datatype=XSD.string)))
                    print(f"  + Genre: {genre_name}")
                    
                elif prop == "label":
                    label_name = value.split('/')[-1].replace('_', ' ')
                    label_uri = LOCAL[label_name.replace(' ', '_')]
                    if (label_uri, RDF.type, MO.Label) not in g:
                        g.add((label_uri, RDF.type, MO.Label))
                        g.add((label_uri, LOCAL.name, Literal(label_name, datatype=XSD.string)))
                    g.add((local_uri, LOCAL.hasRecordLabel, label_uri))
                    print(f"  + Label: {label_name}")
                    
                elif prop == "birthDate":
                    g.add((local_uri, LOCAL.birthDate, Literal(value, datatype=XSD.date)))
                    print(f"  + Birth: {value}")
                    
                elif prop == "activeStart":
                    g.add((local_uri, LOCAL.activeYearsStart, Literal(value, datatype=XSD.gYear)))
                    print(f"  + Active: {value}")
                    
        except Exception as e:
            print(f"  Error: {e}")
    
    g.serialize("music-artist-relationships-enriched.ttl", format="turtle")
    print(f"\nTotal triples: {len(g)}")

def quick_dylan_enhancement():
    g = Graph()
    g.parse("music-artist-relationships-enriched.ttl", format="turtle")
    
    # Add more genres and collaborations for Bob Dylan
    dylan = LOCAL.Bob_Dylan
    g.add((dylan, LOCAL.genre, Literal("Folk music", datatype=XSD.string)))
    g.add((dylan, LOCAL.genre, Literal("Country music", datatype=XSD.string)))
    g.add((dylan, LOCAL.genre, Literal("Blues", datatype=XSD.string)))
    
    # Add Neil Young as collaborator (he's already in the data)
    neil = LOCAL.Neil_Young
    g.add((dylan, LOCAL.collaboratedWith, neil))
    g.add((neil, LOCAL.collaboratedWith, dylan))
    
    g.serialize("music-artist-relationships-enriched.ttl", format="turtle")

def main():
    """Main execution."""
    
    print("INTERMEDIATE TASK - STEP 2: DBpedia Enrichment")
    print("="*80)
    
    # Load mappings
    mappings = load_mappings("artist_mappings.json")
    print(f"Loaded {len(mappings)} artist mappings")
    
    # Enrich ontology
    input_file = "music-artist-relationships-populated.ttl"
    output_file = "music-artist-relationships-enriched.ttl"
    
    enrich_ontology(input_file, mappings, output_file)
    
    # NEW CALLS HERE:
    print("\n\nSTEP 3: Enriching contemporary artists...")
    enrich_contemporary_artists()
    
    print("\n\nSTEP 4: Final Dylan enhancement...")
    quick_dylan_enhancement()
    
    print("\n All enrichment complete!")
if __name__ == "__main__":
    main()