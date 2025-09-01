import requests
from rdflib import Graph, URIRef, Literal, Namespace
from rdflib.namespace import RDF, RDFS, OWL, DCTERMS

def run_sparql_query_and_build_graph():
    """
    Runs a SPARQL query against the ODISSEI endpoint and builds an OWL graph.
    """
    # Define the SPARQL endpoint and query
    sparql_endpoint = "https://api.kg.odissei.nl/datasets/odissei/odissei-kg-acceptance/services/odissei-kg-acceptance-virtuoso/sparql"
    
    # The SPARQL query provided by the user.
    query = """
    PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    PREFIX owl: <http://www.w3.org/2002/07/owl#>
    
    SELECT DISTINCT ?entity ?type ?label ?comment ?subClassOf ?domain ?range
    WHERE {
      # This finds all entities that are classified as either a class.
      ?entity a ?type .
      FILTER(?type = rdfs:Class || ?type = owl:Class)
    
      # This filter explicitly excludes the unwanted classes.
      FILTER(?entity != rdfs:Resource && 
             ?entity != rdf:Property && 
             ?entity != rdfs:Class && 
             ?entity != owl:Thing && 
             ?entity != rdf:List && 
             ?entity != rdfs:Datatype)
    
      # The following are OPTIONAL, meaning they will be included in the output if they exist,
      # but their absence will not prevent a class from being listed.
      OPTIONAL { ?entity rdfs:label ?label . }
      OPTIONAL { ?entity rdfs:comment ?comment . }
      OPTIONAL { ?entity rdfs:subClassOf ?subClassOf . }
    
      # This finds properties that have this class as their domain or range.
      OPTIONAL { ?domain rdfs:domain ?entity . }
      OPTIONAL { ?range rdfs:range ?entity . }
    }
    """

    # Set up the HTTP request headers for the SPARQL query
    headers = {
        'Accept': 'application/sparql-results+json',
        'Content-Type': 'application/x-www-form-urlencoded'
    }
    data = {'query': query}

    print("Running SPARQL query...")
    try:
        response = requests.post(sparql_endpoint, headers=headers, data=data)
        response.raise_for_status() # Raise an exception for bad status codes
        results = response.json()
        print("Query successful. Processing results...")
    except requests.exceptions.RequestException as e:
        print(f"Error connecting to SPARQL endpoint: {e}")
        return None

    # Create a new RDF graph to hold the ontology
    g = Graph()

    # Define the ontology URI and its annotations
    ontology_uri = URIRef("https://kg.odissei.nl/SSHOC-NL-ontology.owl")
    g.add((ontology_uri, RDF.type, OWL.Ontology))
    g.add((ontology_uri, RDFS.label, Literal("SSHOC-NL ontology")))
    g.add((ontology_uri, RDFS.comment, Literal("This is the ontology documentation for the SSHOC-NL Knowledge Graph, available at https://kg.odissei.nl/.")))
    g.add((ontology_uri, DCTERMS.creator, Literal("Andre Valdestilhas")))

    # Process the SPARQL results and add triples to the graph
    bindings = results['results']['bindings']
    for row in bindings:
        # Get the entity URI
        entity_uri = URIRef(row['entity']['value'])

        # Add the entity as a class
        if 'type' in row:
            g.add((entity_uri, RDF.type, URIRef(row['type']['value'])))
        else:
            # If no type is explicitly returned, assume it's a class since the query filtered for that
            g.add((entity_uri, RDF.type, OWL.Class)) 

        # Add label, comment, and subClassOf relationships if they exist
        if 'label' in row:
            g.add((entity_uri, RDFS.label, Literal(row['label']['value'])))
        if 'comment' in row:
            g.add((entity_uri, RDFS.comment, Literal(row['comment']['value'])))
        if 'subClassOf' in row:
            g.add((entity_uri, RDFS.subClassOf, URIRef(row['subClassOf']['value'])))
        
        # Add domain and range relationships if they exist
        if 'domain' in row:
            domain_uri = URIRef(row['domain']['value'])
            g.add((domain_uri, RDFS.domain, entity_uri))
        if 'range' in row:
            range_uri = URIRef(row['range']['value'])
            g.add((range_uri, RDFS.range, entity_uri))

    # Save the graph to an OWL file
    try:
        output_file = "SSHOC-NL_ontology.owl"
        g.serialize(destination=output_file, format='xml')
        print(f"Successfully generated OWL file: {output_file}")
        return True
    except Exception as e:
        print(f"Error serializing graph to file: {e}")
        return False

# Run the main function
if __name__ == "__main__":
    # Ensure rdflib and requests are installed.
    # To install: pip install rdflib requests
    try:
        import rdflib
        import requests
    except ImportError:
        print("Please install the required libraries: 'pip install rdflib requests'")
    else:
        run_sparql_query_and_build_graph()
