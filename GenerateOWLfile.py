import json
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
        
        # Handle multiple subClassOf entries if they exist (not in this specific JSON, but good practice)
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

if __name__ == "__main__":
    # The JSON data is provided here as a string for a self-contained example.
    # In a real-world scenario, you would load this from a file.
    json_content = """
    {
      "head": {
        "vars": [
          "entity",
          "type",
          "label",
          "comment",
          "subClassOf",
          "domain",
          "range"
        ]
      },
      "results": {
        "bindings": [
          {
            "entity": {
              "type": "uri",
              "value": "https://w3id.org/dsv-ontology#CategoricalDataType"
            },
            "type": {
              "type": "literal",
              "value": "Class"
            },
            "label": {
              "type": "literal",
              "value": "Categorical Statistical Data Type"
            },
            "comment": {
              "type": "literal",
              "value": "Set of statistical data types can be observed and - or - categorised."
            },
            "subClassOf": {
              "type": "uri",
              "value": "https://w3id.org/dsv-ontology#StatisticalDataType"
            }
          },
          {
            "entity": {
              "type": "uri",
              "value": "https://w3id.org/dsv-ontology#Column"
            },
            "type": {
              "type": "literal",
              "value": "Class"
            },
            "label": {
              "type": "literal",
              "value": "Dataset Component"
            },
            "comment": {
              "type": "literal",
              "value": "Set of individual columns of a dataset."
            },
            "subClassOf": [
                {"type": "uri", "value": "http://purl.org/linked-data/cube#ComponentSpecification"},
                {"type": "uri", "value": "http://www.w3.org/ns/csvw#Column"}
            ]
          },
          {
            "entity": {
              "type": "uri",
              "value": "https://w3id.org/dsv-ontology#ColumnProperty"
            },
            "type": {
              "type": "literal",
              "value": "Class"
            },
            "label": {
              "type": "literal",
              "value": "Column Property"
            },
            "comment": {
              "type": "literal",
              "value": "RDF Properties represented by the column."
            },
            "subClassOf": [
                {"type": "uri", "value": "http://purl.org/linked-data/cube#DimensionProperty"},
                {"type": "uri", "value": "http://www.w3.org/1999/02/22-rdf-syntax-ns#Property"}
            ]
          },
          {
            "entity": {
              "type": "uri",
              "value": "https://w3id.org/dsv-ontology#Dataset"
            },
            "type": {
              "type": "literal",
              "value": "Class"
            },
            "label": {
              "type": "literal",
              "value": "Dataset"
            },
            "comment": {
              "type": "literal",
              "value": "Set of data."
            },
            "subClassOf": [
                {"type": "uri", "value": "http://purl.org/linked-data/cube#DataSet"},
                {"type": "uri", "value": "http://www.w3.org/ns/csvw#Table"}
            ]
          },
          {
            "entity": {
              "type": "uri",
              "value": "https://w3id.org/dsv-ontology#DatasetSchema"
            },
            "type": {
              "type": "literal",
              "value": "Class"
            },
            "label": {
              "type": "literal",
              "value": "Dataset Schema"
            },
            "comment": {
              "type": "literal",
              "value": "The structural schema of a dataset."
            },
            "subClassOf": [
                {"type": "uri", "value": "http://purl.org/linked-data/cube#DataStructureDefinition"},
                {"type": "uri", "value": "http://www.w3.org/ns/csvw#TableSchema"}
            ]
          },
          {
            "entity": {
              "type": "uri",
              "value": "https://w3id.org/dsv-ontology#StatisticalDataType"
            },
            "type": {
              "type": "literal",
              "value": "Class"
            },
            "label": {
              "type": "literal",
              "value": "Statistical Data Type"
            },
            "comment": {
              "type": "literal",
              "value": "Set of statistical data types."
            }
          },
          {
            "entity": {
              "type": "uri",
              "value": "https://w3id.org/dsv-ontology#SummaryStatistics"
            },
            "type": {
              "type": "literal",
              "value": "Class"
            },
            "label": {
              "type": "literal",
              "value": "Summary Statistics"
            },
            "comment": {
              "type": "literal",
              "value": "Set of summary statistics about the dataset or column."
            }
          },
          {
            "entity": {
              "type": "uri",
              "value": "https://w3id.org/dsv-ontology#NumericalDataType"
            },
            "type": {
              "type": "literal",
              "value": "Class"
            },
            "label": {
              "type": "literal",
              "value": "Numerical Statistical Data Type"
            },
            "comment": {
              "type": "literal",
              "value": "Set of statistical data types can be measured and quantified."
            },
            "subClassOf": {
              "type": "uri",
              "value": "https://w3id.org/dsv-ontology#StatisticalDataType"
            }
          },
          {
            "entity": {
              "type": "uri",
              "value": "https://w3id.org/dsv-ontology#IntervalDataType"
            },
            "type": {
              "type": "literal",
              "value": "Class"
            },
            "label": {
              "type": "literal",
              "value": "Interval Statistical Data Type"
            },
            "comment": {
              "type": "literal",
              "value": "Statistical data type representing ordered data measured over a numerical scale with equal distance between units."
            },
            "subClassOf": {
              "type": "uri",
              "value": "https://w3id.org/dsv-ontology#NumericalDataType"
            }
          },
          {
            "entity": {
              "type": "uri",
              "value": "https://w3id.org/dsv-ontology#NominalDataType"
            },
            "type": {
              "type": "literal",
              "value": "Class"
            },
            "label": {
              "type": "literal",
              "value": "Nominal Statistical Data Type"
            },
            "comment": {
              "type": "literal",
              "value": "Statistical data type representing discrete units that cannot be ordered or measured."
            },
            "subClassOf": {
              "type": "uri",
              "value": "https://w3id.org/dsv-ontology#CategoricalDataType"
            }
          },
          {
            "entity": {
              "type": "uri",
              "value": "https://w3id.org/dsv-ontology#OrdinalDataType"
            },
            "type": {
              "type": "literal",
              "value": "Class"
            },
            "label": {
              "type": "literal",
              "value": "Ordinal Statistical Data Type"
            },
            "comment": {
              "type": "literal",
              "value": "Statistical data type representing discrete units that can be ordered or measured."
            },
            "subClassOf": {
              "type": "uri",
              "value": "https://w3id.org/dsv-ontology#CategoricalDataType"
            }
          },
          {
            "entity": {
              "type": "uri",
              "value": "https://w3id.org/dsv-ontology#RatioDataType"
            },
            "type": {
              "type": "literal",
              "value": "Class"
            },
            "label": {
              "type": "literal",
              "value": "Ratio Statistical Data Type"
            },
            "comment": {
              "type": "literal",
              "value": "Statistical data type representing ordered data with equal distance between units, where negative values are not allowed."
            },
            "subClassOf": {
              "type": "uri",
              "value": "https://w3id.org/dsv-ontology#NumericalDataType"
            }
          },
          {
            "entity": {
              "type": "uri",
              "value": "http://purl.org/ontology/bibo/cites"
            },
            "type": {
              "type": "literal",
              "value": "ObjectProperty"
            },
            "label": {
              "type": "literal",
              "value": "cites"
            },
            "comment": {
              "type": "literal",
              "value": "Relates a document to another document that is cited by the first document as reference, comment, review, quotation or for another purpose."
            },
            "domain": {
              "type": "uri",
              "value": "https://schema.org/SoftwareSourceCode"
            },
            "range": {
              "type": "uri",
              "value": "http://purl.org/ontology/bibo/Document"
            }
          },
          {
            "entity": {
              "type": "uri",
              "value": "https://w3id.org/dsv-ontology#hasCategories"
            },
            "type": {
              "type": "literal",
              "value": "AnnotationProperty"
            },
            "label": {
              "type": "literal",
              "value": "has categories"
            },
            "comment": {
              "type": "literal",
              "value": "Links the dataset or column to a list of categories."
            },
            "domain": [
                {"type": "uri", "value": "https://w3id.org/dsv-ontology#Dataset"},
                {"type": "uri", "value": "https://w3id.org/dsv-ontology#Column"}
            ],
            "range": {
              "type": "uri",
              "value": "http://www.w3.org/1999/02/22-rdf-syntax-ns#List"
            }
          }
        ]
      }
    }
    """
    
    # Load the JSON data
    try:
        data = json.loads(json_content)
        owl_output = generate_owl_ontology(data)
        print(owl_output)
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
