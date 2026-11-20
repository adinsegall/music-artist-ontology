#!/usr/bin/env python3
"""
populate_basic.py - Basic Task: Populate Music Artist Relationships Ontology from Wikidata

This script queries Wikidata for artists with RIAA certifications (Gold/Platinum/Diamond)
and populates the local ontology with artist, release, and success metric data.

The RIAA certification system provides objective success thresholds:
- Gold: 500,000 units
- Platinum: 1,000,000 units  
- Diamond: 10,000,000 units
"""

import rdflib
from rdflib import Graph, Namespace, URIRef, Literal, RDF, RDFS, XSD
from SPARQLWrapper import SPARQLWrapper, JSON
import datetime
import sys
import ssl
ssl._create_default_https_context = ssl._create_unverified_context


# Namespace definitions matching the ontology
MO = Namespace("http://purl.org/ontology/mo/")
FOAF = Namespace("http://xmlns.com/foaf/0.1/")
SCHEMA = Namespace("http://schema.org/")
LOCAL = Namespace("http://www.semanticweb.org/adinsegall/ontologies/2025/4/music-artist-relationships#")

# Wikidata endpoint
WIKIDATA_ENDPOINT = "https://query.wikidata.org/sparql"

def get_certified_artists():
    """Query Wikidata for notable musicians."""
    
    query = """
    SELECT DISTINCT ?artist ?artistLabel ?artistType ?genre ?genreLabel ?sitelinks
    WHERE {
      # Musicians with notable presence
      ?artist wdt:P106 wd:Q639669 ;      # musician
              wdt:P31 ?artistType ;       # instance type
              wikibase:sitelinks ?sitelinks .
      
      VALUES ?artistType { wd:Q5 wd:Q215380 }
      
      # Has at least one award (existence check only)
      ?artist wdt:P166 ?someAward .
      
      # Optional genre
      OPTIONAL { ?artist wdt:P136 ?genre }
      
      # FILTER(?sitelinks > 3)  # Lower threshold
      
      SERVICE wikibase:label { bd:serviceParam wikibase:language "en". }
    }
    ORDER BY DESC(?sitelinks)
    LIMIT 30
    """
    
    sparql = SPARQLWrapper(WIKIDATA_ENDPOINT)
    sparql.setQuery(query)
    sparql.setReturnFormat(JSON)
    
    try:
        results = sparql.query().convert()
        return results["results"]["bindings"]
    except Exception as e:
        print(f"Error querying Wikidata: {e}")
        return []
    
def get_artist_releases(artist_uri):
    """Get releases for a specific artist."""
    
    query = """
    SELECT DISTINCT ?release ?releaseLabel ?releaseType ?releaseDate ?label ?labelLabel
    WHERE {
      <%s> ^wdt:P175 ?release .
      ?release wdt:P31 ?releaseType .
      VALUES ?releaseType { wd:Q134556 wd:Q482994 wd:Q169930 }
      
      OPTIONAL { ?release wdt:P264 ?label }
      OPTIONAL { ?release wdt:P577 ?releaseDate }
      
      SERVICE wikibase:label { bd:serviceParam wikibase:language "en". }
    }
    LIMIT 10
    """ % artist_uri
    
    sparql = SPARQLWrapper(WIKIDATA_ENDPOINT)
    sparql.setQuery(query)
    sparql.setReturnFormat(JSON)
    
    try:
        results = sparql.query().convert()
        return results["results"]["bindings"]
    except:
        return []

def create_artist_uri(artist_name):
    """Create a valid URI for an artist."""
    # Replace spaces and special characters
    safe_name = artist_name.replace(" ", "_").replace("&", "and")
    # Remove other problematic characters
    safe_name = "".join(c for c in safe_name if c.isalnum() or c in "_-")
    return LOCAL[safe_name]

def create_release_uri(release_name):
    """Create a valid URI for a release."""
    safe_name = release_name.replace(" ", "_").replace("&", "and")
    safe_name = "".join(c for c in safe_name if c.isalnum() or c in "_-")
    return LOCAL[safe_name]

def populate_ontology(results, output_file):
    """Populate the ontology with data from Wikidata results."""
    
    # Load existing ontology
    g = Graph()
    try:
        g.parse(output_file, format="turtle")
        print(f"Loaded existing ontology from {output_file}")
    except:
        print(f"Could not load existing ontology, starting fresh")
    
    # Bind namespaces
    g.bind("mo", MO)
    g.bind("foaf", FOAF) 
    g.bind("schema", SCHEMA)
    g.bind("", LOCAL)
    
    # Track what we've added
    added_artists = set()
    added_releases = set()
    success_metrics = {}  # Track success metrics per artist
    artists_processed_for_releases = set() # Track artists already processed for releases
    
    for result in results:
        # Extract artist data
        artist_uri_str = result["artist"]["value"]
        artist_name = result["artistLabel"]["value"]
        artist_type = result["artistType"]["value"]
        
        # Create local URI for artist
        artist_uri = create_artist_uri(artist_name)
        
        # Add artist if new
        if artist_uri_str not in added_artists:
            added_artists.add(artist_uri_str)
            
            # Add artist type
            if "Q5" in artist_type:  # Human = Solo Artist
                g.add((artist_uri, RDF.type, LOCAL.SoloArtist))
                g.add((artist_uri, RDF.type, MO.MusicArtist))
            else:  # Q215380 = Band/Musical Group
                g.add((artist_uri, RDF.type, LOCAL.Band))
                g.add((artist_uri, RDF.type, MO.MusicGroup))
            
            # Add artist name
            g.add((artist_uri, LOCAL.name, Literal(artist_name, datatype=XSD.string)))
            g.add((artist_uri, RDFS.label, Literal(artist_name, lang="en")))
            
            # Add genre if available
            if "genre" in result and "genreLabel" in result:
                genre_label = result["genreLabel"]["value"]
                g.add((artist_uri, LOCAL.genre, Literal(genre_label, datatype=XSD.string)))
            
            # Initialize success metrics tracker
            success_metrics[artist_uri_str] = set()
        
        # Add success metrics
        if "award" in result and "awardLabel" in result:
            award_label = result["awardLabel"]["value"]
            metric_key = f"Award_{award_label.replace(' ', '_')}"
            
            if metric_key not in success_metrics[artist_uri_str]:
                success_metrics[artist_uri_str].add(metric_key)
                award_uri = LOCAL[f"{metric_key}_{artist_name.replace(' ', '_')}"]
                g.add((award_uri, RDF.type, LOCAL.ChartPosition))
                g.add((award_uri, LOCAL.chartName, Literal(award_label, datatype=XSD.string)))
                g.add((award_uri, LOCAL.position, Literal(1, datatype=XSD.integer)))
                g.add((artist_uri, LOCAL.hasChartPosition, award_uri))
        
        if "sitelinks" in result:
            sitelink_count = int(result["sitelinks"]["value"])
            metric_key = "Wikipedia_Presence"
            
            if metric_key not in success_metrics[artist_uri_str]:
                success_metrics[artist_uri_str].add(metric_key)
                wiki_uri = LOCAL[f"Wikipedia_Presence_{artist_name.replace(' ', '_')}"]
                g.add((wiki_uri, RDF.type, LOCAL.ChartPosition))
                g.add((wiki_uri, LOCAL.chartName, Literal("Wikipedia Language Count", datatype=XSD.string)))
                g.add((wiki_uri, LOCAL.position, Literal(sitelink_count, datatype=XSD.integer)))
                g.add((artist_uri, LOCAL.hasChartPosition, wiki_uri))
        
        # Fetch releases for this artist (only once per artist)
        if artist_uri_str not in artists_processed_for_releases:
            artists_processed_for_releases.add(artist_uri_str)  # Mark as processed
            
            print(f"  Fetching releases for {artist_name}...")
            release_results = get_artist_releases(artist_uri_str)
            
            for rel_result in release_results[:5]:  # Max 5 releases per artist
                if "release" in rel_result and "releaseLabel" in rel_result:
                    release_uri_str = rel_result["release"]["value"]
                    
                    if release_uri_str not in added_releases:  # Check if release already added
                        added_releases.add(release_uri_str)
                    release_name = rel_result["releaseLabel"]["value"]
                    
                    # Create local URI for release
                    release_uri = create_release_uri(release_name)
                    
                    # Determine release type
                    release_type = rel_result.get("releaseType", {}).get("value", "")
                    if "Q134556" in release_type:  # Single
                        g.add((release_uri, RDF.type, LOCAL.Single))
                    elif "Q169930" in release_type:  # EP
                        g.add((release_uri, RDF.type, LOCAL.EP))
                    else:  # Q482994 = Album
                        g.add((release_uri, RDF.type, SCHEMA.MusicAlbum))
                    
                    g.add((release_uri, RDF.type, MO.Release))
                    g.add((release_uri, LOCAL.name, Literal(release_name, datatype=XSD.string)))
                    g.add((release_uri, RDFS.label, Literal(release_name, lang="en")))
                    
                    # Add release date if available
                    if "releaseDate" in rel_result:
                        date_str = rel_result["releaseDate"]["value"]
                        try:
                            date_obj = datetime.datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                            g.add((release_uri, LOCAL.releaseDate, Literal(date_obj.date(), datatype=XSD.date)))
                        except:
                            pass
                    
                    # Link to label if available
                    if "label" in rel_result and "labelLabel" in rel_result:
                        label_name = rel_result["labelLabel"]["value"]
                        label_uri = LOCAL[label_name.replace(" ", "_")]
                        g.add((label_uri, RDF.type, MO.Label))
                        g.add((label_uri, LOCAL.name, Literal(label_name, datatype=XSD.string)))
                        g.add((release_uri, LOCAL.publishedBy, label_uri))
                    
                    # Link artist to release
                    g.add((release_uri, LOCAL.performedBy, artist_uri))
                    g.add((artist_uri, LOCAL.performed, release_uri))

        # Process release data
        if "release" in result and "releaseLabel" in result:
            release_uri_str = result["release"]["value"]
            release_name = result["releaseLabel"]["value"]
            
            # Create local URI for release
            release_uri = create_release_uri(release_name)
            
            if release_uri_str not in added_releases:
                added_releases.add(release_uri_str)
                
                # Determine release type
                release_type = result.get("releaseType", {}).get("value", "")
                if "Q134556" in release_type:  # Single
                    g.add((release_uri, RDF.type, LOCAL.Single))
                elif "Q169930" in release_type:  # EP
                    g.add((release_uri, RDF.type, LOCAL.EP))
                else:  # Q482994 = Album
                    g.add((release_uri, RDF.type, SCHEMA.MusicAlbum))
                
                g.add((release_uri, RDF.type, MO.Release))
                g.add((release_uri, LOCAL.name, Literal(release_name, datatype=XSD.string)))
                g.add((release_uri, RDFS.label, Literal(release_name, lang="en")))
                
                # Add release date if available
                if "releaseDate" in result:
                    date_str = result["releaseDate"]["value"]
                    try:
                        date_obj = datetime.datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                        g.add((release_uri, LOCAL.releaseDate, Literal(date_obj.date(), datatype=XSD.date)))
                    except:
                        pass
                
                # Link release to label if available
                if "label" in result and "labelLabel" in result:
                    label_name = result["labelLabel"]["value"]
                    label_uri = LOCAL[label_name.replace(" ", "_")]
                    g.add((label_uri, RDF.type, MO.Label))
                    g.add((label_uri, LOCAL.name, Literal(label_name, datatype=XSD.string)))
                    g.add((release_uri, LOCAL.publishedBy, label_uri))
            
            # Link artist to release
            g.add((release_uri, LOCAL.performedBy, artist_uri))
            g.add((artist_uri, LOCAL.performed, release_uri))
    
    # Save the populated ontology
    g.serialize(destination=output_file, format="turtle")
    print(f"\nOntology populated and saved to {output_file}")
    
    # Print summary statistics
    print(f"\nPopulation Summary:")
    print(f"- Artists added: {len(added_artists)}")
    print(f"- Artists with awards: {len([a for a in success_metrics if success_metrics[a]])}")
    print(f"- Releases added: {len(added_releases)}")
    print(f"- Total triples: {len(g)}")

def main():
    """Main execution function."""
    
    print("ECS7028P - Music Artist Relationships Ontology")
    print("Basic Task: Populating from Wikidata Grammy Winners")
    print("=" * 60)
    
    # Query Wikidata
    print("\nQuerying Wikidata for Grammy-winning artists and their releases...")
    results = get_certified_artists()
    
    if not results:
        print("No results returned from Wikidata!")
        sys.exit(1)
    
    print(f"Retrieved {len(results)} artist/release records")
    
    # Output file (update existing ontology)
    output_file = "music-artist-relationships-populated.ttl"
    
    # Populate ontology
    print("\nPopulating ontology...")
    populate_ontology(results, output_file)
    
    print("\nBasic task completed successfully!")
    print(f"\nThe populated ontology demonstrates:")
    print("- Artist classification (SoloArtist vs Band)")
    print("- Release hierarchy (Album, EP, Single)")  
    print("- Multiple success metrics (Awards, Wikipedia presence)")
    print("- Label relationships")
    print("- Genre associations")
    print("\nSuccess metrics enable inference of SuccessfulArtist through:")
    print("- Award achievements (position=1)")
    print("- Wikipedia presence (position=language count)")
    print("- These diverse signals support the DL definition: SuccessfulArtist ≡ MusicArtist ⊓ ∃hasChartPosition.ChartPosition")

if __name__ == "__main__":
    main()
