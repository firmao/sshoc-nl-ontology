import dash
import dash_cytoscape as cyto
from dash import html, dcc, Input, Output, State
import rdflib
from rdflib.plugins.stores.sparqlstore import SPARQLStore
from collections import Counter
import dash_bootstrap_components as dbc
from urllib.parse import urlparse
import logging
import requests
import traceback
import json

# Set up logging for better debugging
logging.basicConfig(level=logging.INFO)

# Initial setup
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])

# A simple helper function to create a human-readable name from a URI
def get_name(uri):
    parts = str(uri).split('/')
    last_part = parts[-1]
    if '#' in last_part:
        return last_part.split('#')[-1].replace('_', ' ').replace('-', ' ')
    else:
        return last_part.replace('_', ' ').replace('-', ' ')

# Global state
data_source = {'type': 'none', 'uri': None, 'expanded_nodes': set(), 'initial_elements': [], 'class_labels': []}

# --- Data Loading and Query Functions ---
def load_data(uri):
    """Detects data type and loads the graph accordingly."""
    parsed_uri = urlparse(uri)
    
    if 'sparql' in parsed_uri.path.lower() or 'sparql' in parsed_uri.query.lower():
        data_source['type'] = 'sparql'
        data_source['uri'] = uri
        
        try:
            elements, message = get_initial_sparql_nodes(uri)
            if message:
                return [], message, []
            
            data_source['initial_elements'] = elements
            data_source['expanded_nodes'] = set()
            class_labels = get_all_sparql_class_labels(uri)
            data_source['class_labels'] = class_labels
            return elements, None, class_labels
        except Exception as e:
            logging.error(f"Error in initial SPARQL query: {e}")
            return [], f"Error in initial SPARQL query: {str(e)}", []
    
    else:
        data_source['type'] = 'file'
        data_source['uri'] = uri
        
        try:
            g = rdflib.Graph()
            g.parse(uri)
            elements = get_initial_file_nodes(g)
            data_source['graph'] = g
            data_source['initial_elements'] = elements
            data_source['expanded_nodes'] = set()
            class_labels = get_all_file_class_labels(g)
            data_source['class_labels'] = class_labels
            return elements, None, class_labels
        except Exception as e:
            logging.error(f"Error loading data from file URI: {e}")
            return [], f"Error loading data from file URI: {str(e)}", []

def get_all_sparql_class_labels(endpoint_uri):
    """Fetches all rdfs:label values for rdfs:Class entities."""
    query = """
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    SELECT DISTINCT ?label WHERE {
      ?class a rdfs:Class .
      ?class rdfs:label ?label .
    }
    """
    
    params = {'query': query}
    headers = {'Accept': 'application/sparql-results+json'}
    
    try:
        response = requests.get(endpoint_uri, params=params, headers=headers)
        response.raise_for_status()
        data = response.json()
        labels = [binding['label']['value'] for binding in data['results']['bindings']]
        return labels
    except Exception as e:
        logging.error(f"Error fetching class labels: {e}")
        return []

def get_all_file_class_labels(g):
    """Fetches all rdfs:label values from a local/remote file."""
    labels = []
    for s, p, o in g.triples((None, rdflib.RDFS.label, None)):
        if isinstance(o, rdflib.Literal):
            labels.append(str(o))
    return list(set(labels))

def get_initial_sparql_nodes(endpoint_uri, limit=5):
    """
    Uses requests to safely query for the most common rdfs:Class entities,
    with an explicit PREFIX declaration.
    """
    query = f"""
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    SELECT ?class WHERE {{
      ?class a rdfs:Class .
    }}
    LIMIT {limit}
    """
    
    params = {'query': query}
    headers = {'Accept': 'application/sparql-results+json'}
    
    try:
        response = requests.get(endpoint_uri, params=params, headers=headers)
        response.raise_for_status()
        
        nodes = []
        data = response.json()
        for binding in data['results']['bindings']:
            node_uri = binding['class']['value']
            nodes.append({
                'data': {'id': node_uri, 'label': get_name(node_uri)},
                'classes': 'node'
            })
        return nodes, None
    except requests.exceptions.RequestException as e:
        return [], f"HTTP error from endpoint: {e}"
    except Exception as e:
        return [], f"Error processing SPARQL result: {e}"

def get_initial_file_nodes(g):
    """Finds the most frequent nodes in a local/remote file."""
    node_counts = Counter()
    for s, p, o in g:
        node_counts[s] += 1
        if isinstance(o, rdflib.URIRef):
            node_counts[o] += 1
    
    most_frequent_nodes_uris = [uri for uri, count in node_counts.most_common(5)]
    nodes = []
    for uri in most_frequent_nodes_uris:
        uri_str = str(uri)
        nodes.append({
            'data': {'id': uri_str, 'label': get_name(uri)},
            'classes': 'node'
        })
    return nodes

def get_related_nodes_for_expansion(node_id):
    """Fetches neighbors of a node based on the data source type."""
    if data_source['type'] == 'sparql':
        store = SPARQLStore(data_source['uri'], publicID=data_source['uri'])
        g = rdflib.Graph(store)
        
        query_subject = f"""
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
        CONSTRUCT {{ <{node_id}> ?p ?o . }} 
        WHERE {{ <{node_id}> ?p ?o . }} 
        LIMIT 100
        """
        query_object = f"""
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
        CONSTRUCT {{ ?s ?p ?o . }} 
        WHERE {{ ?s ?p <{node_id}> . }} 
        LIMIT 100
        """
        
        temp_g = rdflib.Graph(store)
        temp_g.query(query_subject)
        temp_g.query(query_object)
        
        triples = list(temp_g.triples((None, None, None)))
    
    elif data_source['type'] == 'file':
        g = data_source['graph']
        triples = list(g.triples((rdflib.URIRef(node_id), None, None))) + \
                  list(g.triples((None, None, rdflib.URIRef(node_id))))
    
    new_elements = []
    for s, p, o in triples:
        s_uri = str(s)
        new_elements.append({'data': {'id': s_uri, 'label': get_name(s)}, 'classes': 'node'})
        
        if isinstance(o, rdflib.URIRef):
            o_uri = str(o)
            new_elements.append({'data': {'id': o_uri, 'label': get_name(o)}, 'classes': 'node'})
            new_elements.append({'data': {'source': s_uri, 'target': o_uri, 'label': get_name(p)}})
        else:
            literal_id = f"literal-{s_uri}-{p}-{str(o)}"
            new_elements.append({'data': {'id': literal_id, 'label': str(o)}, 'classes': 'literal'})
            new_elements.append({'data': {'source': s_uri, 'target': literal_id, 'label': get_name(p)}})
            
    return new_elements

# --- Dash Layout ---
app.layout = dbc.Container(
    fluid=True,
    children=[
        html.H1("Knowledge Graph Explorer", className="my-4 text-center"),
        dbc.Row(
            justify="center",
            children=[
                dbc.Col(
                    [
                        dbc.InputGroup(
                            [
                                dbc.Input(
                                    id='uri-input',
                                    type='text',
                                    placeholder="Enter SPARQL endpoint or OWL file URI...",
                                    value="https://api.kg.odissei.nl/datasets/odissei/odissei-kg/services/odissei-virtuoso/sparql",
                                ),
                                dbc.Button("Load Graph", id="load-button", color="primary"),
                            ],
                            className="mb-3"
                        ),
                        dbc.Row(
                            [
                                dbc.Col(
                                    dcc.Dropdown(
                                        id='search-input',
                                        placeholder="Search for a class...",
                                        options=[],
                                        clearable=True
                                    ),
                                    width=9
                                ),
                                dbc.Col(
                                    dbc.Button("Search Class", id="search-button", color="secondary"),
                                    width=3
                                )
                            ],
                            className="mb-3"
                        ),
                        html.Div(id='error-message', className="text-danger mb-3"),
                    ],
                    width=8,
                )
            ]
        ),
        dcc.Store(id='class-labels-store', data=json.dumps([])),
        dcc.Loading(
            id="loading-spinner",
            type="circle",
            children=[
                html.Div(
                    style={'display': 'flex', 'height': 'calc(100vh - 210px)'},
                    children=[
                        cyto.Cytoscape(
                            id='cytoscape-graph',
                            style={'width': '70%', 'height': '100%', 'borderRight': '1px solid #ccc'},
                            elements=[],
                            layout={'name': 'cose', 'nodeRepulsion': 200000, 'nodeDimensionsIncludeLabels': True},
                            stylesheet=[
                                {
                                    'selector': 'node',
                                    'style': {
                                        'content': 'data(label)',
                                        'font-family': 'Arial, sans-serif',
                                        'font-size': '12px',
                                        'text-valign': 'center',
                                        'text-halign': 'center',
                                        'background-color': '#6a1b9a',
                                        'color': 'white',
                                        'text-wrap': 'wrap',
                                        'text-max-width': '80px',
                                        'width': 'label',
                                        'height': 'label',
                                        'padding': '15px',
                                        'shape': 'round-rectangle',
                                        'border-width': 1,
                                        'border-color': '#5a0f8a'
                                    }
                                },
                                {
                                    'selector': '.literal',
                                    'style': {
                                        'background-color': '#42a5f5',
                                        'shape': 'rectangle',
                                        'text-max-width': '100px',
                                        'border-color': '#3295e5'
                                    }
                                },
                                {
                                    'selector': 'edge',
                                    'style': {
                                        'label': '',
                                        'curve-style': 'bezier',
                                        'target-arrow-shape': 'triangle',
                                        'line-color': '#b2bec3',
                                        'target-arrow-color': '#b2bec3',
                                        'font-size': '10px'
                                    }
                                },
                                {
                                    'selector': 'edge:hover',
                                    'style': {
                                        'label': 'data(label)',
                                        'text-background-color': 'white',
                                        'text-background-opacity': 1,
                                        'text-background-padding': '3px',
                                        'color': '#333'
                                    }
                                },
                                {
                                    'selector': 'node:selected',
                                    'style': {
                                        'border-width': 3,
                                        'border-color': '#FFD700'
                                    }
                                }
                            ],
                            minZoom=0.1,
                            maxZoom=5
                        ),
                        html.Div(
                            id='entity-info-panel',
                            style={'width': '30%', 'padding': '20px', 'overflowY': 'auto'},
                            children=[html.H3("Click an entity to expand its relationships", className="text-secondary")]
                        )
                    ]
                )
            ]
        )
    ]
)

# --- Callbacks ---
@app.callback(
    [Output('cytoscape-graph', 'elements'),
     Output('entity-info-panel', 'children'),
     Output('error-message', 'children'),
     Output('class-labels-store', 'data')],
    [Input('load-button', 'n_clicks')],
    [State('uri-input', 'value')],
    prevent_initial_call=True
)
def load_graph(n_clicks, uri):
    if n_clicks is None or not uri:
        return dash.no_update, dash.no_update, "", json.dumps([])
    
    elements, error_message, class_labels = load_data(uri)
    
    if error_message:
        return [], [html.H3("Click an entity to expand its relationships")], error_message, json.dumps([])
    
    return elements, [html.H3("Click on a node to toggle its relationships.")], "", json.dumps(class_labels)

@app.callback(
    Output('search-input', 'options'),
    [Input('class-labels-store', 'data')]
)
def update_search_options(labels_data):
    if labels_data:
        labels = json.loads(labels_data)
        return [{'label': label, 'value': label} for label in labels]
    return []

@app.callback(
    [Output('cytoscape-graph', 'elements', allow_duplicate=True),
     Output('error-message', 'children', allow_duplicate=True)],
    [Input('search-button', 'n_clicks')],
    [State('search-input', 'value')],
    prevent_initial_call=True
)
def search_class(n_clicks, search_term):
    if not search_term or not data_source['uri']:
        return dash.no_update, "Please enter a search term."

    if data_source['type'] == 'sparql':
        endpoint_uri = data_source['uri']
        
        query_exact = f"""
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        SELECT ?class WHERE {{
          ?class rdfs:label "{search_term}" .
        }}
        LIMIT 1
        """
        
        params = {'query': query_exact}
        headers = {'Accept': 'application/sparql-results+json'}
        try:
            response = requests.get(endpoint_uri, params=params, headers=headers)
            response.raise_for_status()
            data = response.json()
            if data['results']['bindings']:
                node_uri = data['results']['bindings'][0]['class']['value']
                elements = [{'data': {'id': node_uri, 'label': get_name(node_uri)}, 'classes': 'node'}]
                data_source['initial_elements'] = elements
                data_source['expanded_nodes'] = set()
                return elements, ""
        except Exception as e:
            return dash.no_update, f"Error searching for exact match: {str(e)}"

        query_partial = f"""
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        SELECT DISTINCT ?class WHERE {{
          ?class rdfs:label ?label .
          FILTER (regex(?label, "{search_term}", "i"))
        }}
        LIMIT 10
        """

        params = {'query': query_partial}
        headers = {'Accept': 'application/sparql-results+json'}
        try:
            response = requests.get(endpoint_uri, params=params, headers=headers)
            response.raise_for_status()
            data = response.json()
            if data['results']['bindings']:
                elements = []
                for binding in data['results']['bindings']:
                    node_uri = binding['class']['value']
                    elements.append({'data': {'id': node_uri, 'label': get_name(node_uri)}, 'classes': 'node'})
                data_source['initial_elements'] = elements
                data_source['expanded_nodes'] = set()
                return elements, "No exact match found. Displaying similar classes."
            else:
                return [], "No matching classes found."
        except Exception as e:
            return dash.no_update, f"Error searching for similar matches: {str(e)}"
    
    else: # File-based search
        g = data_source.get('graph')
        if not g:
            return [], "Graph not loaded."
        
        subject = None
        for s, p, o in g.triples((None, rdflib.RDFS.label, rdflib.Literal(search_term))):
            if isinstance(s, rdflib.URIRef):
                subject = s
                break
        
        if subject:
            elements = [{'data': {'id': str(subject), 'label': get_name(subject)}, 'classes': 'node'}]
            data_source['initial_elements'] = elements
            data_source['expanded_nodes'] = set()
            return elements, ""

        elements = []
        for s, p, o in g.triples((None, rdflib.RDFS.label, None)):
            if search_term.lower() in str(o).lower():
                elements.append({'data': {'id': str(s), 'label': str(o)}, 'classes': 'node'})
        
        if elements:
            data_source['initial_elements'] = elements
            data_source['expanded_nodes'] = set()
            return elements, "No exact match found. Displaying similar classes."
        else:
            return [], "No matching classes found."


@app.callback(
    [Output('cytoscape-graph', 'elements', allow_duplicate=True),
     Output('entity-info-panel', 'children', allow_duplicate=True)],
    [Input('cytoscape-graph', 'tapNodeData')],
    prevent_initial_call=True
)
def display_related_nodes(node_data):
    if not node_data:
        return dash.no_update, dash.no_update
    
    node_id = node_data['id']
    
    # Toggle the expanded state of the clicked node
    if node_id in data_source['expanded_nodes']:
        data_source['expanded_nodes'].remove(node_id)
    else:
        data_source['expanded_nodes'].add(node_id)
    
    all_elements = data_source['initial_elements'][:]
    elements_ids = {elem['data']['id'] for elem in all_elements if 'id' in elem['data']}
    
    info_children = [
        html.H3(node_data['label']),
        html.P(f"URI: {node_id}", style={'word-wrap': 'break-word', 'font-size': '12px'})
    ]

    try:
        for expanded_node_id in data_source['expanded_nodes']:
            new_elements = get_related_nodes_for_expansion(expanded_node_id)
            
            for elem in new_elements:
                if 'id' in elem['data']:
                    if elem['data']['id'] not in elements_ids:
                        all_elements.append(elem)
                        elements_ids.add(elem['data']['id'])
                else: # It's an edge
                    all_elements.append(elem)
            
            if expanded_node_id == node_id:
                for elem in new_elements:
                    if 'source' in elem['data'] and elem['data']['source'] == node_id:
                        info_children.append(
                            html.Div(
                                children=[
                                    html.H4(get_name(elem['data']['label'])),
                                    html.P(get_name(elem['data']['target']) if 'target' in elem['data'] else "")
                                ],
                                style={'border-bottom': '1px dotted #ccc', 'padding': '10px 0'}
                            )
                        )
                        
    except Exception as e:
        if node_id in data_source['expanded_nodes']:
             data_source['expanded_nodes'].remove(node_id)
        
        logging.error("Error during node expansion:", exc_info=True)
        return dash.no_update, [html.H3(f"Error expanding node: {str(e)}")]
    
    return all_elements, info_children

if __name__ == '__main__':
    app.run(debug=True)