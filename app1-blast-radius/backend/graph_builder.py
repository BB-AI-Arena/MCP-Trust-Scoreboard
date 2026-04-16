"""
graph_builder.py
Builds a NetworkX directed graph from agent permissions and integrations,
then converts it to a JSON-serializable dict with positions and metadata.
"""

import math
import networkx as nx
from typing import List, Dict, Any


# ---------------------------------------------------------------------------
# Node-type inference rules
# ---------------------------------------------------------------------------

# Ordered list of (keyword_substrings, node_type) pairs.
# The FIRST matching rule wins.
_TYPE_RULES: List[tuple] = [
    # Credentials / secrets
    (["secret", "credential", "token", "key", "vault", "kms", "ssm", "param"], "Credential"),
    # Identity / IAM
    (["iam", "role", "policy", "rbac", "ldap", "saml", "oauth", "sso", "ad", "directory"], "Identity"),
    # Databases
    (["rds", "database", "db", "postgres", "mysql", "mongo", "redis", "dynamo",
      "aurora", "cassandra", "sql", "elasticsearch", "opensearch", "bigquery"], "Database"),
    # Networks
    (["network", "vpc", "subnet", "firewall", "nacl", "security group", "sg",
      "load balancer", "elb", "alb", "nlb", "cloudfront", "cdn", "dns", "route53",
      "internet", "egress", "ingress", "proxy", "gateway"], "Network"),
    # File systems / object storage
    (["s3", "storage", "file", "blob", "gcs", "efs", "fsx", "nfs", "smb",
      "bucket", "drive", "hdfs", "filesystem", "fs"], "FileSystem"),
    # External / third-party APIs
    (["openai", "anthropic", "gemini", "cohere", "huggingface", "api",
      "webhook", "http", "rest", "graphql", "slack", "github", "gitlab",
      "jira", "confluence", "salesforce", "stripe", "twilio", "sendgrid",
      "pagerduty", "datadog", "splunk", "newrelic"], "API"),
]

_CRITICALITY_MAP: Dict[str, str] = {
    "Credential": "critical",
    "Identity": "critical",
    "Database": "high",
    "Network": "high",
    "API": "medium",
    "FileSystem": "medium",
    "Agent": "low",
}

_PERMISSION_EDGE_MAP: List[tuple] = [
    (["write", "put", "post", "delete", "update", "create", "modify", "upload"], "WriteAccess"),
    (["execute", "invoke", "run", "trigger", "call", "start", "launch"], "ExecuteAccess"),
    (["read", "get", "list", "describe", "scan", "query", "download", "fetch"], "ReadAccess"),
    (["auth", "assume", "login", "connect", "bind", "sts"], "Authenticate"),
]


def _infer_node_type(name: str) -> str:
    """Return the best-matching node type for a resource name."""
    lower = name.lower()
    for keywords, node_type in _TYPE_RULES:
        if any(kw in lower for kw in keywords):
            return node_type
    return "API"  # sensible default for unknown external resources


def _infer_edge_type(permission: str) -> str:
    """Return the best-matching edge (access) type for a permission string."""
    lower = permission.lower()
    for keywords, edge_type in _PERMISSION_EDGE_MAP:
        if any(kw in lower for kw in keywords):
            return edge_type
    return "ReadAccess"  # conservative default


def _spring_layout(G: nx.DiGraph, center_node: str) -> Dict[str, tuple]:
    """
    A lightweight spring-layout approximation that places the agent at the
    center and distributes other nodes in concentric rings by BFS distance.
    Returns {node_id: (x, y)} with values roughly in [-300, 300].
    """
    pos: Dict[str, tuple] = {}

    # BFS distances from the agent node
    try:
        distances = nx.single_source_shortest_path_length(G, center_node)
    except nx.NodeNotFound:
        distances = {n: 1 for n in G.nodes()}
        distances[center_node] = 0

    # Group nodes by distance (ring)
    rings: Dict[int, List[str]] = {}
    for node, dist in distances.items():
        rings.setdefault(dist, []).append(node)

    # Assign positions ring by ring
    for dist, nodes_in_ring in sorted(rings.items()):
        radius = dist * 120  # pixels per hop
        count = len(nodes_in_ring)
        for i, node in enumerate(nodes_in_ring):
            if dist == 0:
                pos[node] = (0.0, 0.0)
            else:
                angle = (2 * math.pi * i) / count
                x = radius * math.cos(angle)
                y = radius * math.sin(angle)
                pos[node] = (round(x, 2), round(y, 2))

    # Any node not reachable from agent (isolated or reverse edges only)
    for node in G.nodes():
        if node not in pos:
            pos[node] = (round(200 + len(pos) * 10, 2), round(200 + len(pos) * 10, 2))

    return pos


def build_graph(
    agent_name: str,
    permissions: List[str],
    integrations: List[str],
    endpoint_type: str,
) -> Dict[str, Any]:
    """
    Build a directed graph from an agent's permissions and integrations.

    Parameters
    ----------
    agent_name    : display name of the agent (becomes the root node)
    permissions   : list of permission strings, e.g. ["s3:GetObject", "rds:connect"]
    integrations  : list of integration names, e.g. ["openai", "stripe", "iam"]
    endpoint_type : hint about the agent's exposure type (e.g. "public", "internal")

    Returns
    -------
    {
        "nodes": [{"id", "type", "label", "criticality", "x", "y", "reach_score"}],
        "edges": [{"source", "target", "type"}]
    }
    """
    G = nx.DiGraph()

    agent_id = f"agent_{agent_name.lower().replace(' ', '_')}"
    G.add_node(agent_id, type="Agent", label=agent_name)

    # -----------------------------------------------------------------------
    # Parse permissions → resource nodes + edges
    # -----------------------------------------------------------------------
    for perm in permissions:
        # Support both "service:Action" and plain "action_on_resource" strings
        if ":" in perm:
            service, action = perm.split(":", 1)
            resource_name = service.strip()
            edge_type = _infer_edge_type(action)
        else:
            resource_name = perm.strip()
            edge_type = _infer_edge_type(perm)

        if not resource_name:
            continue

        node_id = f"resource_{resource_name.lower().replace(' ', '_').replace('/', '_')}"
        node_type = _infer_node_type(resource_name)
        label = resource_name.upper() if len(resource_name) <= 5 else resource_name.title()

        if not G.has_node(node_id):
            G.add_node(node_id, type=node_type, label=label)

        G.add_edge(agent_id, node_id, type=edge_type)

    # -----------------------------------------------------------------------
    # Parse integrations → API/service nodes
    # -----------------------------------------------------------------------
    for integration in integrations:
        if not integration:
            continue

        node_id = f"integration_{integration.lower().replace(' ', '_').replace('/', '_')}"
        node_type = _infer_node_type(integration)
        label = integration.title()

        if not G.has_node(node_id):
            G.add_node(node_id, type=node_type, label=label)

        # Integrations imply the agent can call out to them
        G.add_edge(agent_id, node_id, type="ExecuteAccess")

    # -----------------------------------------------------------------------
    # Add an "Internet" network node if endpoint_type is public
    # -----------------------------------------------------------------------
    if endpoint_type and endpoint_type.lower() in ("public", "external", "internet"):
        internet_id = "network_internet"
        if not G.has_node(internet_id):
            G.add_node(internet_id, type="Network", label="Internet")
        G.add_edge(agent_id, internet_id, type="WriteAccess")

    # -----------------------------------------------------------------------
    # Layout
    # -----------------------------------------------------------------------
    pos = _spring_layout(G, agent_id)

    # -----------------------------------------------------------------------
    # Transitive reach score
    # Defined as: (number of nodes reachable from this node) / total_nodes
    # Gives a 0-1 float; scale to 0-100 for display.
    # -----------------------------------------------------------------------
    total_nodes = max(G.number_of_nodes(), 1)

    nodes_out = []
    for node_id, data in G.nodes(data=True):
        try:
            reachable = len(nx.descendants(G, node_id))
        except Exception:
            reachable = 0

        reach_score = round((reachable / total_nodes) * 100, 2)
        node_type = data.get("type", "API")
        x, y = pos.get(node_id, (0.0, 0.0))

        nodes_out.append({
            "id": node_id,
            "type": node_type,
            "label": data.get("label", node_id),
            "criticality": _CRITICALITY_MAP.get(node_type, "medium"),
            "x": x,
            "y": y,
            "reach_score": reach_score,
        })

    edges_out = [
        {"source": u, "target": v, "type": data.get("type", "ReadAccess")}
        for u, v, data in G.edges(data=True)
    ]

    return {"nodes": nodes_out, "edges": edges_out}
