import json
import requests
from rdflib import Graph, URIRef, Literal, Namespace
from rdflib.namespace import RDF, RDFS, OWL, DCTERMS

def generate_owl_ontology(json_data):
    """
    Generates an OWL RDF ontology from the provided JSON data.

    Args:
        json_data (dict): The dictionary containing the ontology data.

    Returns:
        str: A string containing the OWL ontology in RDF/XML format.
    """
    # Initialize the RDF graph
    g = Graph()

    # Define namespaces used in the ontology
    dsv_ontology = Namespace("https://w3id.org/dsv-ontology#")
    bibo = Namespace("http://purl.org/ontology/bibo/")
    cube = Namespace("http://purl.org/linked-data/cube#")
    csvw = Namespace("http://www.w3.org/ns/csvw#")
    event = Namespace("http://purl.org/NET/c4dm/event.owl#")
    foaf = Namespace("http://xmlns.com/foaf/0.1/")
    skos = Namespace("http://www.w3.org/2004/02/skos/core#")
    vann = Namespace("http://purl.org/vocab/vann/")
    schema = Namespace("https://schema.org/")
    rdmt = Namespace("https://terms.codata.org/rdmt/")

    # Bind namespaces to prefixes in the graph for clean output
    g.bind("dsv-ontology", dsv_ontology)
    g.bind("bibo", bibo)
    g.bind("cube", cube)
    g.bind("csvw", csvw)
    g.bind("event", event)
    g.bind("foaf", foaf)
    g.bind("skos", skos)
    g.bind("vann", vann)
    g.bind("schema", schema)
    g.bind("rdmt", rdmt)
    g.bind("rdf", RDF)
    g.bind("rdfs", RDFS)
    g.bind("owl", OWL)
    g.bind("dcterms", DCTERMS)

    # Add the main ontology triple
    ontology_uri = URIRef("https://w3id.org/dsv-ontology")
    g.add((ontology_uri, RDF.type, OWL.Ontology))
    g.add((ontology_uri, vann.preferredNamespacePrefix, Literal("dsv-ontology")))
    g.add((ontology_uri, vann.preferredNamespaceUri, URIRef(dsv_ontology)))
    
    # Add imports as specified in the JSON
    # This part is manually done based on the ontology's structure
    g.add((ontology_uri, OWL.imports, URIRef(cube)))
    g.add((ontology_uri, OWL.imports, URIRef(csvw)))
    g.add((ontology_uri, OWL.imports, URIRef(bibo)))
    g.add((ontology_uri, OWL.imports, URIRef(event)))
    g.add((ontology_uri, OWL.imports, URIRef(skos)))
    g.add((ontology_uri, OWL.imports, URIRef(foaf)))

    # Iterate through the bindings and create RDF triples
    for binding in json_data.get("results", {}).get("bindings", []):
        entity_type_value = binding.get("type", {}).get("value")
        entity_uri = URIRef(binding.get("entity", {}).get("value"))

        # Skip AnnotationProperty for the main loop, as they are handled as predicates
        if entity_type_value == "AnnotationProperty":
            continue

        # Determine the RDF type based on the JSON
        if entity_type_value == "Class":
            rdf_type = OWL.Class
        elif entity_type_value == "ObjectProperty":
            rdf_type = OWL.ObjectProperty
        elif entity_type_value == "DatatypeProperty":
            rdf_type = OWL.DatatypeProperty
        else:
            # Skip if the type is unknown or not an RDF entity
            continue

        g.add((entity_uri, RDF.type, rdf_type))

        # Add common properties
        label = binding.get("label", {}).get("value")
        if label:
            g.add((entity_uri, RDFS.label, Literal(label, lang="en")))

        comment = binding.get("comment", {}).get("value")
        if comment:
            g.add((entity_uri, RDFS.comment, Literal(comment, lang="en")))

        # Add subClassOf property
        sub_class_of_value = binding.get("subClassOf", {}).get("value")
        if sub_class_of_value:
            g.add((entity_uri, RDFS.subClassOf, URIRef(sub_class_of_value)))
        
        # Handle multiple subClassOf entries if they exist
        sub_class_of_list = binding.get("subClassOf", [])
        if isinstance(sub_class_of_list, list):
            for sub_class_uri in sub_class_of_list:
                g.add((entity_uri, RDFS.subClassOf, URIRef(sub_class_uri.get("value"))))

        # Add domain and range for properties
        domain_value = binding.get("domain", {}).get("value")
        if domain_value and rdf_type in [OWL.ObjectProperty, OWL.DatatypeProperty]:
            g.add((entity_uri, RDFS.domain, URIRef(domain_value)))

        range_value = binding.get("range", {}).get("value")
        if range_value and rdf_type in [OWL.ObjectProperty, OWL.DatatypeProperty]:
            g.add((entity_uri, RDFS.range, URIRef(range_value)))

    # Serialize the graph to OWL/XML format
    return g.serialize(format="xml", pretty=True)

def fetch_json_from_url(url):
    """
    Fetches JSON content from a given URL.

    Args:
        url (str): The URL to fetch the JSON from.

    Returns:
        dict: The parsed JSON content.
    """
    try:
        response = requests.get(url)
        response.raise_for_status()  # Raise an exception for bad status codes (4xx or 5xx)
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching data from URL: {e}")
        return None
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON from response: {e}")
        return None

if __name__ == "__main__":
    # Replace this URL with the actual URL of your ontology JSON file
    ontology_url = "https://example.com/ontology.json"

    data = fetch_json_from_url(ontology_url)
    if data:
        try:
            owl_output = generate_owl_ontology(data)
            print(owl_output)
        except Exception as e:
            print(f"An unexpected error occurred during ontology generation: {e}")
