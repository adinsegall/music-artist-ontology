#!/usr/bin/env python3
"""
fusion_queries.py - Intermediate Task
Demonstrates data fusion value through queries that require both data sources
"""

import rdflib
from rdflib import Graph, Namespace
from tabulate import tabulate
from collections import defaultdict

# Namespaces
LOCAL = Namespace("http://www.semanticweb.org/adinsegall/ontologies/2025/4/music-artist-relationships#")
MO = Namespace("http://purl.org/ontology/mo/")
XSD = Namespace("http://www.w3.org/2001/XMLSchema#")


def load_ontology(filename):
    """Load the enriched ontology."""
    g = Graph()
    g.parse(filename, format="turtle")
    return g


def run_fusion_query_1(g):
    """Artists with genres from DBpedia + release data from Wikidata"""
    g.bind("", LOCAL)
    query = """
    PREFIX : <http://www.semanticweb.org/adinsegall/ontologies/2025/4/music-artist-relationships#>
    SELECT ?name (COUNT(DISTINCT ?genre) AS ?genreCount) ?hasReleases ?hasAwards
    WHERE {
        ?artist :name ?name ;
                :genre ?genre .
        OPTIONAL { ?artist :performed ?release }
        OPTIONAL { ?artist :hasChartPosition ?chart }
        BIND(BOUND(?release) AS ?hasReleases)
        BIND(BOUND(?chart) AS ?hasAwards)
    }
    GROUP BY ?name ?hasReleases ?hasAwards
    HAVING (COUNT(DISTINCT ?genre) > 2)
    ORDER BY DESC(?genreCount)
    """
    
    print("\n" + "="*80)
    print("FUSION QUERY 1: Genre-Rich Artists (DBpedia) with Commercial Data (Wikidata)")
    print("="*80)
    
    results = g.query(query)
    table_data = [[str(row.name), int(row.genreCount), 
                   "Yes" if row.hasReleases else "No",
                   "Yes" if row.hasAwards else "No"] for row in results]
    
    if table_data:
        print(tabulate(table_data, headers=["Artist", "# Genres", "Has Releases?", "Has Awards?"], tablefmt="grid"))
    
    return len(table_data)

def run_fusion_query_2(g):
    """Artists with birth dates from DBpedia and career milestones from Wikidata"""
    g.bind("", LOCAL)
    query = """
    PREFIX : <http://www.semanticweb.org/adinsegall/ontologies/2025/4/music-artist-relationships#>
    SELECT DISTINCT ?name ?birthDate ?dataType ?dataValue
    WHERE {
        ?artist :name ?name ;
                :birthDate ?birthDate .
        {
            ?artist :hasChartPosition ?chart .
            ?chart :chartName ?dataValue .
            BIND("Award/Chart" AS ?dataType)
        } UNION {
            ?artist :performed ?release .
            ?release :name ?dataValue .
            BIND("Release" AS ?dataType)
        }
    }
    ORDER BY ?name
    LIMIT 20
    """
    
    print("\n" + "="*80)
    print("FUSION QUERY 2: Artist Timeline - Birth Dates (DBpedia) + Career Data (Wikidata)")
    print("="*80)
    
    results = g.query(query)
    table_data = [[str(row.name), str(row.birthDate)[:10], str(row.dataType), str(row.dataValue)[:40]] for row in results]
    
    if table_data:
        print(tabulate(table_data, headers=["Artist", "Birth Date", "Type", "Achievement"], tablefmt="grid"))
    
    return len(table_data)

def run_fusion_query_3(g):
    """Label presence across both data sources"""
    g.bind("", LOCAL)
    query = """
    PREFIX : <http://www.semanticweb.org/adinsegall/ontologies/2025/4/music-artist-relationships#>
    PREFIX mo: <http://purl.org/ontology/mo/>
    
    SELECT ?labelName 
           (SUM(?hasArtist) AS ?dbpediaArtists)
           (SUM(?hasRelease) AS ?wikidataReleases)
    WHERE {
        ?label a mo:Label ;
               :name ?labelName .
        
        OPTIONAL {
            ?artist :hasRecordLabel ?label .
            BIND(1 AS ?hasArtist)
        }
        
        OPTIONAL {
            ?release :publishedBy ?label .
            BIND(1 AS ?hasRelease)
        }
    }
    GROUP BY ?labelName
    HAVING (?dbpediaArtists > 0 || ?wikidataReleases > 0)
    ORDER BY DESC(?dbpediaArtists + ?wikidataReleases)
    """
    
    print("\n" + "="*80)
    print("FUSION QUERY 3: Record Label Analysis - Artists (DBpedia) vs Releases (Wikidata)")
    print("="*80)
    print("Shows label coverage across both data sources")
    print("-"*80)
    
    results = g.query(query)
    table_data = []
    
    for row in results:
        label_source = ""
        if row.dbpediaArtists > 0 and row.wikidataReleases > 0:
            label_source = "Both"
        elif row.dbpediaArtists > 0:
            label_source = "DBpedia only"
        else:
            label_source = "Wikidata only"
            
        table_data.append([
            str(row.labelName), 
            int(row.dbpediaArtists) if row.dbpediaArtists else 0,
            int(row.wikidataReleases) if row.wikidataReleases else 0,
            int(row.totalConnections),
            label_source
        ])
    
    if table_data:
        print(tabulate(table_data, 
                      headers=["Label", "Artists (DBP)", "Releases (WD)", "Total", "Source"], 
                      tablefmt="grid"))
    
    return len(table_data)

def run_fusion_query_4(g):
    """Artists with both collaborations AND releases"""
    query = """
    SELECT ?name 
           (COUNT(DISTINCT ?collab) AS ?collabs)
           (COUNT(DISTINCT ?release) AS ?releases)
           (COUNT(DISTINCT ?genre) AS ?genres)
    WHERE {
        ?artist :name ?name ;
                :collaboratedWith ?collab ;
                :performed ?release .
        OPTIONAL { ?artist :genre ?genre }
    }
    GROUP BY ?name
    HAVING (?releases > 0 && ?collabs > 0)
    """
    
    print("\n" + "="*80)
    print("FUSION QUERY 4: Collaboration Networks (DBpedia) + Commercial Success (Wikidata)")
    print("="*80)
    
    results = g.query(query)
    table_data = []
    
    for row in results:
        table_data.append([
            str(row.artistName),
            str(row.collabName),
            int(row.artistReleases) if row.artistReleases else 0,
            int(row.collabReleases) if row.collabReleases else 0,
            int(row.artistAwards) if row.artistAwards else 0
        ])
    
    if table_data:
        print(tabulate(table_data, 
                      headers=["Artist", "Collaborator", "Artist Rels", "Collab Rels", "Awards"],
                      tablefmt="grid"))
    else:
        print("No commercially successful collaborations found")
    
    return len(table_data)

def run_fusion_query_5(g):
    """Multi-instrumentalists (DBpedia) with prolific output (Wikidata)"""
    g.bind("", LOCAL)
    query = """
    PREFIX : <http://www.semanticweb.org/adinsegall/ontologies/2025/4/music-artist-relationships#>
    PREFIX mo: <http://purl.org/ontology/mo/>
    
    SELECT ?name 
           (COUNT(DISTINCT ?instrument) AS ?instrumentCount)
           (COUNT(DISTINCT ?release) AS ?releaseCount)
           (GROUP_CONCAT(DISTINCT ?instrument; separator=", ") AS ?instruments)
    WHERE {
        ?artist :name ?name ;
                :playsInstrument ?instrument .
        OPTIONAL { ?artist :performed ?release }
    }
    GROUP BY ?name
    ORDER BY DESC(?instrumentCount) DESC(?releaseCount)
    """
    
    print("\n" + "="*80)
    print("FUSION QUERY 5: Multi-Instrumentalists (DBpedia) and Their Output (Wikidata)")
    print("="*80)
    
    results = g.query(query)
    table_data = []
    
    for row in results:
        instruments = str(row.instruments) if row.instruments else ""
        if len(instruments) > 40:
            instruments = instruments[:37] + "..."
            
        table_data.append([
            str(row.name),
            int(row.instrumentCount),
            int(row.releaseCount) if row.releaseCount else 0,
            instruments
        ])
    
    if table_data:
        print(tabulate(table_data, 
                      headers=["Artist", "# Instruments", "# Releases", "Instruments"],
                      tablefmt="grid"))
    
    return len(table_data)

def print_fusion_summary(results_count):
    """Print summary of fusion query results."""
    
    print("\n" + "="*80)
    print("DATA FUSION SUMMARY")
    print("="*80)
    
    total_results = sum(results_count)
    print(f"\nTotal fusion query results: {total_results}")
    print("\nThese queries demonstrate that the integrated ontology can answer questions")
    print("that neither Wikidata nor DBpedia alone could answer:")
    
    print("\n1. Genre Diversity vs Commercial Success:")
    print("   - DBpedia provides detailed genre classifications")
    print("   - Wikidata provides release and award data")
    print("   - Combined: Analyze if genre-diverse artists are commercially successful")
    
    print("\n2. Artist Timeline Analysis:")
    print("   - DBpedia provides birth dates and biographical data")
    print("   - Wikidata provides career milestones (releases, awards)")
    print("   - Combined: Create complete artist timelines from birth to achievements")
    
    print("\n3. Record Label Coverage:")
    print("   - DBpedia provides artist-label relationships")
    print("   - Wikidata provides release-label relationships")
    print("   - Combined: Understand label representation across both artist rosters and catalogs")
    
    print("\n4. Collaboration Impact:")
    print("   - DBpedia provides collaboration networks")
    print("   - Wikidata provides commercial performance data")
    print("   - Combined: Analyze if collaborations correlate with commercial success")
    
    print("\n5. Musical Versatility:")
    print("   - DBpedia provides instrument proficiency data")
    print("   - Wikidata provides discography information")
    print("   - Combined: Explore if multi-instrumentalists are more prolific")

def main():
    """Execute all fusion queries and demonstrate integration value."""
    
    print("INTERMEDIATE TASK - FUSION QUERIES")
    print("Demonstrating the value of integrating Wikidata and DBpedia")
    
    # Load enriched ontology
    ontology_file = "music-artist-relationships-enriched.ttl"
    print(f"\nLoading enriched ontology from: {ontology_file}")
    g = load_ontology(ontology_file)
    
    # Count triples
    print(f"Total triples in enriched ontology: {len(g)}")
    
    # Run fusion queries
    results_count = []
    results_count.append(run_fusion_query_1(g))
    results_count.append(run_fusion_query_2(g))
    results_count.append(run_fusion_query_3(g))
    results_count.append(run_fusion_query_4(g))
    results_count.append(run_fusion_query_5(g))
    
    # Print summary
    print_fusion_summary(results_count)
    
    print("\n Intermediate Task Complete!")
    print("   These queries prove that data fusion enables new insights")
    print("   that neither source alone could provide.")

if __name__ == "__main__":
    main()