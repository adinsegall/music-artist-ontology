#!/usr/bin/env python3
"""
add_swrl_rules.py - Advanced Task
Adds SWRL rules to demonstrate inference capabilities
"""

import rdflib
from rdflib import Graph, Namespace, Literal, URIRef
from rdflib.namespace import RDF, RDFS, OWL

# Namespaces
LOCAL = Namespace("http://www.semanticweb.org/adinsegall/ontologies/2025/4/music-artist-relationships#")
MO = Namespace("http://purl.org/ontology/mo/")
SWRL = Namespace("http://www.w3.org/2003/11/swrl#")
SWRLB = Namespace("http://www.w3.org/2003/11/swrlb#")

def add_swrl_rules(input_file, output_file):
    """Add SWRL rules to the ontology."""
    
    # Load ontology
    g = Graph()
    g.parse(input_file, format="turtle")
    
    # Bind namespaces
    g.bind("", LOCAL)
    g.bind("mo", MO)
    g.bind("swrl", SWRL)
    g.bind("swrlb", SWRLB)
    
    # Add new classes for inferences
    g.add((LOCAL.ProlificArtist, RDF.type, OWL.Class))
    g.add((LOCAL.ProlificArtist, RDFS.subClassOf, MO.MusicArtist))
    g.add((LOCAL.ProlificArtist, RDFS.comment, Literal("Artists with 5+ releases")))
    
    g.add((LOCAL.VeteranArtist, RDF.type, OWL.Class))
    g.add((LOCAL.VeteranArtist, RDFS.subClassOf, MO.MusicArtist))
    g.add((LOCAL.VeteranArtist, RDFS.comment, Literal("Artists active before 1970")))
    
    g.add((LOCAL.AwardWinner, RDF.type, OWL.Class))
    g.add((LOCAL.AwardWinner, RDFS.subClassOf, MO.MusicArtist))
    g.add((LOCAL.AwardWinner, RDFS.comment, Literal("Artists with awards/chart positions")))
    
    g.add((LOCAL.CollaborativeArtist, RDF.type, OWL.Class))
    g.add((LOCAL.CollaborativeArtist, RDFS.subClassOf, MO.MusicArtist))
    g.add((LOCAL.CollaborativeArtist, RDFS.comment, Literal("Artists with 3+ collaborations")))
    
    g.add((LOCAL.MultiGenreArtist, RDF.type, OWL.Class))
    g.add((LOCAL.MultiGenreArtist, RDFS.subClassOf, MO.MusicArtist))
    g.add((LOCAL.MultiGenreArtist, RDFS.comment, Literal("Artists with 3+ genres")))
    
    # Rule 1: Prolific Artist (5+ releases)
    # Note: In actual Protégé, you'd use the SWRL editor
    # This is a simplified representation
    rule1_comment = """
    Rule: ProlificArtist
    Artist(?x) ∧ performed(?x, ?r1) ∧ performed(?x, ?r2) ∧ performed(?x, ?r3) ∧ 
    performed(?x, ?r4) ∧ performed(?x, ?r5) ∧ 
    differentFrom(?r1, ?r2) ∧ differentFrom(?r1, ?r3) ∧ differentFrom(?r1, ?r4) ∧ 
    differentFrom(?r1, ?r5) ∧ differentFrom(?r2, ?r3) ∧ differentFrom(?r2, ?r4) ∧ 
    differentFrom(?r2, ?r5) ∧ differentFrom(?r3, ?r4) ∧ differentFrom(?r3, ?r5) ∧ 
    differentFrom(?r4, ?r5) → ProlificArtist(?x)
    """
    
    # Rule 2: Veteran Artist (active before 1970)
    rule2_comment = """
    Rule: VeteranArtist
    Artist(?x) ∧ activeYearsStart(?x, ?year) ∧ swrlb:lessThan(?year, 1970) → VeteranArtist(?x)
    """
    
    # Rule 3: Award Winner
    rule3_comment = """
    Rule: AwardWinner
    Artist(?x) ∧ hasChartPosition(?x, ?award) → AwardWinner(?x)
    """
    
    # Rule 4: Collaborative Artist (3+ collaborations)
    rule4_comment = """
    Rule: CollaborativeArtist
    Artist(?x) ∧ collaboratedWith(?x, ?y1) ∧ collaboratedWith(?x, ?y2) ∧ 
    collaboratedWith(?x, ?y3) ∧ differentFrom(?y1, ?y2) ∧ 
    differentFrom(?y1, ?y3) ∧ differentFrom(?y2, ?y3) → CollaborativeArtist(?x)
    """
    
    # Rule 5: Multi-Genre Artist
    rule5_comment = """
    Rule: MultiGenreArtist
    Artist(?x) ∧ genre(?x, ?g1) ∧ genre(?x, ?g2) ∧ genre(?x, ?g3) ∧ 
    differentFrom(?g1, ?g2) ∧ differentFrom(?g1, ?g3) ∧ 
    differentFrom(?g2, ?g3) → MultiGenreArtist(?x)
    """
    
    # Add rule documentation
    rules_uri = LOCAL.SWRLRules
    g.add((rules_uri, RDF.type, OWL.AnnotationProperty))
    g.add((rules_uri, RDFS.comment, Literal(
        rule1_comment + "\n" + 
        rule2_comment + "\n" + 
        rule3_comment + "\n" + 
        rule4_comment + "\n" + 
        rule5_comment
    )))
    
    # Save ontology
    g.serialize(destination=output_file, format="turtle")
    
    print("SWRL Rules Added:")
    print("1. ProlificArtist - Artists with 5+ releases")
    print("2. VeteranArtist - Artists active before 1970")
    print("3. AwardWinner - Artists with awards/chart positions")
    print("4. CollaborativeArtist - Artists with 3+ collaborations")
    print("5. MultiGenreArtist - Artists with 3+ genres")
    print(f"\nOntology saved to: {output_file}")
    print("\nNOTE: Load this in Protégé and run Pellet reasoner to see inferences")
    
    # Quick manual check of what would be inferred
    print("\n" + "="*50)
    print("EXPECTED INFERENCES (after running Pellet):")
    print("="*50)
    
    # Check for prolific artists
    prolific = []
    for artist in g.subjects(RDF.type, MO.MusicArtist):
        releases = list(g.objects(artist, LOCAL.performed))
        if len(releases) >= 5:
            name = g.value(artist, LOCAL.name)
            if name:
                prolific.append((str(name), len(releases)))
    
    if prolific:
        print("\nProlific Artists:")
        for name, count in sorted(prolific, key=lambda x: x[1], reverse=True):
            print(f"  - {name} ({count} releases)")
    
    # Check for veteran artists
    veterans = []
    for artist in g.subjects(RDF.type, MO.MusicArtist):
        year = g.value(artist, LOCAL.activeYearsStart)
        if year and str(year) < "1970":
            name = g.value(artist, LOCAL.name)
            if name:
                veterans.append((str(name), str(year)))
    
    if veterans:
        print("\nVeteran Artists:")
        for name, year in sorted(veterans, key=lambda x: x[1]):
            print(f"  - {name} (active since {year})")
    
    # Check for award winners
    award_winners = []
    for artist in g.subjects(RDF.type, MO.MusicArtist):
        awards = list(g.objects(artist, LOCAL.hasChartPosition))
        if awards:
            name = g.value(artist, LOCAL.name)
            if name:
                award_winners.append((str(name), len(awards)))
    
    if award_winners:
        print("\nAward Winners:")
        for name, count in sorted(award_winners, key=lambda x: x[1], reverse=True):
            print(f"  - {name} ({count} awards/positions)")
    
    # Check for multi-genre artists
    multi_genre = []
    for artist in g.subjects(RDF.type, MO.MusicArtist):
        genres = list(g.objects(artist, LOCAL.genre))
        if len(genres) >= 3:
            name = g.value(artist, LOCAL.name)
            if name:
                multi_genre.append((str(name), len(genres)))
    
    if multi_genre:
        print("\nMulti-Genre Artists:")
        for name, count in sorted(multi_genre, key=lambda x: x[1], reverse=True):
            print(f"  - {name} ({count} genres)")

def main():
    """Main execution."""
    input_file = "music-artist-relationships-enriched.ttl"
    output_file = "music-artist-relationships-advanced.ttl"
    
    print("ADVANCED TASK - Adding SWRL Rules")
    print("="*50)
    
    add_swrl_rules(input_file, output_file)
    
    print("\n\nNEXT STEPS:")
    print("1. Open music-artist-relationships-advanced.ttl in Protégé")
    print("2. Go to Window > Tabs > SWRL Tab")
    print("3. Add the rules shown above using SWRL syntax")
    print("4. Run Pellet reasoner (Reasoner > Pellet > Start)")
    print("5. Check inferred class memberships in Class hierarchy")
    print("6. Take screenshots for your report")

if __name__ == "__main__":
    main()