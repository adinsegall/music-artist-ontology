#!/usr/bin/env python3
"""
query_local.py - Query the populated Music Artist Relationships Ontology

This script demonstrates various SPARQL queries against the local ontology,
showing how to retrieve artists, their releases, and success metrics.
"""

import rdflib
from rdflib import Graph, Namespace
from tabulate import tabulate

# Namespace definitions
MO = Namespace("http://purl.org/ontology/mo/")
FOAF = Namespace("http://xmlns.com/foaf/0.1/")
SCHEMA = Namespace("http://schema.org/")
LOCAL = Namespace("http://www.semanticweb.org/adinsegall/ontologies/2025/4/music-artist-relationships#")

def load_ontology(filename):
    """Load the populated ontology."""
    g = Graph()
    g.parse(filename, format="turtle")
    
    # Bind namespaces for cleaner queries
    g.bind("mo", MO)
    g.bind("foaf", FOAF)
    g.bind("schema", SCHEMA)
    g.bind("local", LOCAL)
    
    return g

def query_successful_artists(g):
    """Query for successful artists (those with chart positions/certifications)."""
    
    print("\n1. SUCCESSFUL ARTISTS (with Awards/Success Metrics)")
    print("=" * 60)
    
    query = """
    PREFIX local: <http://www.semanticweb.org/adinsegall/ontologies/2025/4/music-artist-relationships#>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    
    SELECT DISTINCT ?artist ?artistName ?artistType (COUNT(DISTINCT ?chart) AS ?metricCount)
    WHERE {
        ?artist a ?artistClass .
        FILTER(?artistClass IN (local:SoloArtist, local:Band))
        
        ?artist local:name ?artistName .
        
        # Get artist type
        BIND(IF(?artistClass = local:SoloArtist, "Solo Artist", "Band") AS ?artistType)
        
        # Get chart positions directly
        ?artist local:hasChartPosition ?chart .
    }
    GROUP BY ?artist ?artistName ?artistType
    ORDER BY DESC(?metricCount) ?artistName
    """
    
    results = g.query(query)
    
    table_data = []
    for row in results:
        table_data.append([
            str(row.artistName),
            str(row.artistType),
            int(row.metricCount) if row.metricCount else 0
        ])
    
    print(tabulate(table_data, 
                   headers=["Artist Name", "Type", "Success Metrics"],
                   tablefmt="grid"))
    
def query_genre_success(g):
    """Query for most successful genres based on certifications."""
    
    print("\n2. GENRE SUCCESS ANALYSIS")
    print("=" * 60)
    
    query = """
    PREFIX local: <http://www.semanticweb.org/adinsegall/ontologies/2025/4/music-artist-relationships#>
    
    SELECT ?genre (COUNT(DISTINCT ?artist) AS ?artistCount) (COUNT(DISTINCT ?chart) AS ?metricCount)
    WHERE {
        ?artist local:genre ?genre .
        ?artist local:hasChartPosition ?chart .
    }
    GROUP BY ?genre
    ORDER BY DESC(?metricCount)
    """
    
    results = g.query(query)
    
    table_data = []
    for row in results:
        table_data.append([
            str(row.genre),
            int(row.artistCount),
            int(row.metricCount)  # Changed from metricCount to metricCount
        ])
    
    print(tabulate(table_data,
                   headers=["Genre", "Artists", "Total Success Metrics"],
                   tablefmt="grid"))

def query_release_types(g):
    """Query for release types and their success."""
    
    print("\n3. RELEASE TYPE DISTRIBUTION")
    print("=" * 60)
    
    query = """
    PREFIX local: <http://www.semanticweb.org/adinsegall/ontologies/2025/4/music-artist-relationships#>
    PREFIX mo: <http://purl.org/ontology/mo/>
    PREFIX schema: <http://schema.org/>
    PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
    
    SELECT ?releaseType (COUNT(DISTINCT ?release) AS ?releaseCount)
    WHERE {
        ?release a ?releaseType .
        FILTER(?releaseType IN (schema:MusicAlbum, local:EP, local:Single))
    }
    GROUP BY ?releaseType
    ORDER BY DESC(?releaseCount)
    """
    
    results = g.query(query)
    
    table_data = []
    for row in results:
        release_type = str(row.releaseType).split("#")[-1].split("/")[-1]
        table_data.append([release_type, int(row.releaseCount)])
    
    print(tabulate(table_data,
                   headers=["Release Type", "Count"],
                   tablefmt="grid"))

def query_label_roster(g):
    """Query for record labels and their artists."""
    
    print("\n4. RECORD LABEL ANALYSIS")
    print("=" * 60)
    
    query = """
    PREFIX local: <http://www.semanticweb.org/adinsegall/ontologies/2025/4/music-artist-relationships#>
    PREFIX mo: <http://purl.org/ontology/mo/>
    
    SELECT ?label ?labelName (COUNT(DISTINCT ?artist) AS ?artistCount) (COUNT(DISTINCT ?release) AS ?releaseCount)
    WHERE {
        ?label a mo:Label .
        ?label local:name ?labelName .
        ?release local:publishedBy ?label .
        ?release local:performedBy ?artist .
    }
    GROUP BY ?label ?labelName
    ORDER BY DESC(?artistCount)
    LIMIT 10
    """
    
    results = g.query(query)
    
    table_data = []
    for row in results:
        table_data.append([
            str(row.labelName),
            int(row.artistCount),
            int(row.releaseCount)
        ])
    
    print(tabulate(table_data,
                   headers=["Label Name", "Artists", "Releases"],
                   tablefmt="grid"))

def query_artist_details(g, artist_name):
    """Query detailed information about a specific artist."""
    
    print(f"\n5. ARTIST DETAILS: {artist_name}")
    print("=" * 60)
    
    query = """
    PREFIX local: <http://www.semanticweb.org/adinsegall/ontologies/2025/4/music-artist-relationships#>
    PREFIX mo: <http://purl.org/ontology/mo/>
    
    SELECT ?artist ?genre ?release ?releaseName ?releaseDate
    WHERE {
        ?artist local:name ?name .
        FILTER(CONTAINS(LCASE(?name), LCASE("%s")))
        
        ?artist local:genre ?genre .
        OPTIONAL {
            ?release local:performedBy ?artist .
            ?release local:name ?releaseName .
            OPTIONAL { ?release local:releaseDate ?releaseDate }
        }
    }
    LIMIT 20
    """ % artist_name
    
    results = list(g.query(query))
    
    if results:
        # Get basic info from first result
        first = results[0]
        print(f"Artist: {artist_name}")
        if first.genre:
            print(f"Genre: {first.genre}")
        
        # Collect unique releases
        releases = set()
        for row in results:
            if row.releaseName:
                date_str = f" ({row.releaseDate})" if row.releaseDate else ""
                releases.add(f"{row.releaseName}{date_str}")
        
        if releases:
            print(f"\nReleases ({len(releases)}):")
            for release in sorted(releases)[:10]:  # Show max 10
                print(f"  - {release}")
    else:
        print(f"No artist found matching '{artist_name}'")

def custom_query(g):
    """Allow user to run custom SPARQL queries."""
    
    print("\n6. CUSTOM QUERY INTERFACE")
    print("=" * 60)
    print("Enter a SPARQL query (or 'exit' to quit):")
    print("Available prefixes: local:, mo:, schema:, foaf:")
    print()
    
    query_lines = []
    while True:
        line = input()
        if line.lower() == 'exit':
            return
        if line.strip() == '':
            break
        query_lines.append(line)
    
    if query_lines:
        query = '\n'.join(query_lines)
        try:
            results = g.query(query)
            
            # Get variable names from results
            if results and len(results) > 0:
                vars = results.vars if hasattr(results, 'vars') else []
                table_data = []
                for row in results:
                    table_data.append([str(getattr(row, str(var))) for var in vars])
                
                print("\nResults:")
                print(tabulate(table_data, headers=[str(v) for v in vars], tablefmt="grid"))
            else:
                print("No results found.")
        except Exception as e:
            print(f"Query error: {e}")

def main():
    """Main execution function."""
    
    print("ECS7028P - Music Artist Relationships Ontology")
    print("Local Ontology Query Demonstration")
    print("=" * 60)
    
    # Load the populated ontology
    ontology_file = "music-artist-relationships-populated.ttl"
    
    try:
        g = load_ontology(ontology_file)
        print(f"\nLoaded ontology with {len(g)} triples")
    except Exception as e:
        print(f"Error loading ontology: {e}")
        print("Make sure to run populate_basic.py first!")
        return
    
    # Run demonstration queries
    query_successful_artists(g)
    query_genre_success(g)
    query_release_types(g)
    query_label_roster(g)
    
    # Example specific artist query
    query_artist_details(g, "Taylor Swift")
    
    # Custom query interface
    print("\nWould you like to run custom queries? (y/n)")
    if input().lower() == 'y':
        custom_query(g)
    
    print("\nQuery demonstration completed!")

if __name__ == "__main__":
    main()
