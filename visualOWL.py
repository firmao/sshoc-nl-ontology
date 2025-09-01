import dash
import dash_cytoscape as cyto
from dash import html, dcc
import rdflib
from urllib.request import urlopen

# Step 1: Load and process the OWL data
# For simplicity, we'll download the OWL file from the URL.
# In a real application, you might want to save it locally.
ontology_url = "https://firmao.github.io/sshoc-nl-ontology/ontology.owl"
g = rdflib.Graph()
try:
    with urlopen(ontology_url) as response:
        g.parse(response, format="xml")
except Exception as e:
    print(f"Error loading ontology: {e}")
    # Fallback or error handling
    g.parse('local_copy.owl', format="xml")

# Step 2: Convert RDF triples to Cytoscape format
# We'll create a simplified representation for visualization.
nodes = {}
edges = []

# A simple helper function to create a human-readable name from a URI
def get_name(uri):
    return str(uri).split('/')[-1].replace('#', ' ').replace('_', ' ').replace('-', ' ')

# Iterate through all triples in the graph
for s, p, o in g:
    # A triple consists of a subject (s), a predicate (p), and an object (o)

    # Add subject as a node if it doesn't exist
    s_uri = str(s)
    if s_uri not in nodes:
        nodes[s_uri] = {
            'data': {'id': s_uri, 'label': get_name(s)},
            'classes': 'node'
        }

    # Add object as a node if it's not a literal and doesn't exist
    if isinstance(o, rdflib.URIRef) and str(o) not in nodes:
        o_uri = str(o)
        nodes[o_uri] = {
            'data': {'id': o_uri, 'label': get_name(o)},
            'classes': 'node'
        }

    # Add the relationship as an edge
    if isinstance(o, rdflib.URIRef):
        edges.append({
            'data': {
                'source': s_uri,
                'target': str(o),
                'label': get_name(p)
            }
        })
    # If the object is a literal (e.g., a string or number), we'll add it as a node
    # and link to it.
    else:
        literal_id = f"literal-{s_uri}-{p}-{str(o)}"
        literal_label = str(o)
        
        # Add the literal as a node
        nodes[literal_id] = {
            'data': {'id': literal_id, 'label': literal_label},
            'classes': 'literal'
        }
        # Add a relationship from the subject to the literal
        edges.append({
            'data': {
                'source': s_uri,
                'target': literal_id,
                'label': get_name(p)
            }
        })

elements = list(nodes.values()) + edges

# Step 3: Create the Dash Web Application
app = dash.Dash(__name__)

# Basic stylesheet for the graph
stylesheet = [
    {
        'selector': 'node',
        'style': {
            'label': 'data(label)',
            'background-color': '#6a1b9a',  # A purple color for nodes
            'color': 'white',
            'font-size': '12px',
            'text-valign': 'center',
            'text-halign': 'center',
            'padding': '10px'
        }
    },
    {
        'selector': 'edge',
        'style': {
            'label': 'data(label)',
            'curve-style': 'bezier',
            'target-arrow-shape': 'triangle',
            'line-color': '#b2bec3',
            'target-arrow-color': '#b2bec3',
            'font-size': '10px',
            'text-background-opacity': 1,
            'text-background-color': '#f5f6fa'
        }
    },
    {
        'selector': '.literal',
        'style': {
            'background-color': '#42a5f5', # A blue color for literal nodes
        }
    }
]

# Define the app layout
app.layout = html.Div(
    style={'height': '100vh', 'width': '100%', 'font-family': 'Arial, sans-serif'},
    children=[
        html.H1("Interactive SSHOC Knowledge Graph", style={'textAlign': 'center'}),
        html.Div(
            style={'display': 'flex', 'height': 'calc(100% - 60px)'},
            children=[
                # Graph Container
                cyto.Cytoscape(
                    id='cytoscape-graph',
                    style={'width': '70%', 'height': '100%', 'borderRight': '1px solid #ccc'},
                    elements=elements,
                    layout={'name': 'cose'}, # A good layout for complex graphs
                    stylesheet=stylesheet,
                    minZoom=0.1,
                    maxZoom=5
                ),
                # Info Panel
                html.Div(
                    id='entity-info-panel',
                    style={'width': '30%', 'padding': '20px', 'overflowY': 'auto'},
                    children=[
                        html.H3("Click an entity to see its details", style={'color': '#555'})
                    ]
                )
            ]
        )
    ]
)

# Step 4: Add Interactivity with Callbacks
@app.callback(
    dash.Output('entity-info-panel', 'children'),
    [dash.Input('cytoscape-graph', 'tapNodeData')]
)
def display_node_properties(node_data):
    if not node_data:
        return [html.H3("Click an entity to see its details")]

    node_id = node_data['id']
    children = [
        html.H3(node_data['label']),
        html.P(f"URI: {node_id}", style={'word-wrap': 'break-word', 'font-size': '12px'})
    ]

    # Find and display all properties for the clicked node
    node_uri = rdflib.URIRef(node_id)
    
    # Iterate through all triples where the clicked node is the subject
    for s, p, o in g.triples((node_uri, None, None)):
        children.append(
            html.Div(
                children=[
                    html.H4(get_name(p)),
                    html.P(str(o))
                ],
                style={'border-bottom': '1px dotted #ccc', 'padding': '10px 0'}
            )
        )
        
    return children

# Run the server
if __name__ == '__main__':
    app.run(debug=True)