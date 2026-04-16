"""
risk_scorer.py
Calculates an overall blast-radius score and surfaces the highest-risk paths
for a given graph (nodes + edges produced by graph_builder.build_graph).
"""

from typing import List, Dict, Any


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_BLAST_RATING_THRESHOLDS = [
    (76, "Catastrophic"),
    (51, "Severe"),
    (26, "Moderate"),
    (0,  "Contained"),
]

_HIGH_CRITICALITY = {"critical", "high"}
_CRITICAL_ONLY    = {"critical"}


def _rating_from_score(score: int) -> str:
    for threshold, label in _BLAST_RATING_THRESHOLDS:
        if score >= threshold:
            return label
    return "Contained"


def score_blast_radius(
    nodes: List[Dict[str, Any]],
    edges: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Calculate the blast radius score and supporting metadata.

    Scoring components
    ------------------
    - Base: 5 points per reachable non-agent node (capped at 25)
    - Credential nodes: +25 per credential node, capped at +40 total
    - WriteAccess edges: +10 each, capped at +30 total
    - External Network nodes: +15 each, capped at +30 total

    Total possible score: 25 + 40 + 30 + 30 = 125 → normalised to 0-100.

    Returns
    -------
    {
        "overall_score": int,          # 0-100
        "blast_rating": str,           # Contained / Moderate / Severe / Catastrophic
        "critical_nodes": [node_ids],  # nodes with criticality "critical" or "high"
        "highest_risk_paths": [[node_ids]]  # up to 5 paths from agent to critical/high nodes
    }
    """
    if not nodes:
        return {
            "overall_score": 0,
            "blast_rating": "Contained",
            "critical_nodes": [],
            "highest_risk_paths": [],
        }

    # -----------------------------------------------------------------------
    # Index helpers
    # -----------------------------------------------------------------------
    node_by_id: Dict[str, Dict[str, Any]] = {n["id"]: n for n in nodes}

    # Find agent node (type == "Agent")
    agent_node_id: str = next(
        (n["id"] for n in nodes if n.get("type") == "Agent"),
        nodes[0]["id"],
    )

    # Build adjacency list for BFS path finding
    adj: Dict[str, List[str]] = {n["id"]: [] for n in nodes}
    for edge in edges:
        src, tgt = edge.get("source"), edge.get("target")
        if src in adj:
            adj[src].append(tgt)

    # -----------------------------------------------------------------------
    # Score component 1: reachable node count
    # -----------------------------------------------------------------------
    non_agent_nodes = [n for n in nodes if n.get("type") != "Agent"]
    reachable_count = len(non_agent_nodes)
    score_reachable = min(reachable_count * 5, 25)

    # -----------------------------------------------------------------------
    # Score component 2: Credential nodes
    # -----------------------------------------------------------------------
    credential_nodes = [
        n for n in nodes
        if n.get("type") == "Credential"
    ]
    score_credentials = min(len(credential_nodes) * 25, 40)

    # -----------------------------------------------------------------------
    # Score component 3: WriteAccess edges
    # -----------------------------------------------------------------------
    write_edges = [e for e in edges if e.get("type") == "WriteAccess"]
    score_write = min(len(write_edges) * 10, 30)

    # -----------------------------------------------------------------------
    # Score component 4: external Network nodes
    # -----------------------------------------------------------------------
    network_nodes = [
        n for n in nodes
        if n.get("type") == "Network"
    ]
    score_network = min(len(network_nodes) * 15, 30)

    # -----------------------------------------------------------------------
    # Combine and normalise to 0-100
    # -----------------------------------------------------------------------
    raw_score = score_reachable + score_credentials + score_write + score_network
    max_raw   = 125  # 25 + 40 + 30 + 30
    overall_score = round(min((raw_score / max_raw) * 100, 100))

    # -----------------------------------------------------------------------
    # Critical nodes: criticality in {"critical", "high"}
    # -----------------------------------------------------------------------
    critical_nodes = [
        n["id"] for n in nodes
        if n.get("criticality") in _HIGH_CRITICALITY
    ]

    # -----------------------------------------------------------------------
    # Highest-risk paths: BFS from agent to each critical/high node
    # We find shortest paths and sort by priority (critical before high).
    # Return up to 5 paths.
    # -----------------------------------------------------------------------
    highest_risk_paths: List[List[str]] = []
    visited_targets: set = set()

    # Prioritise: critical criticality first, then high
    priority_targets = (
        [n for n in nodes if n.get("criticality") == "critical"] +
        [n for n in nodes if n.get("criticality") == "high"]
    )

    for target_node in priority_targets:
        target_id = target_node["id"]
        if target_id == agent_node_id or target_id in visited_targets:
            continue

        path = _bfs_path(adj, agent_node_id, target_id)
        if path and len(path) > 1:
            highest_risk_paths.append(path)
            visited_targets.add(target_id)

        if len(highest_risk_paths) >= 5:
            break

    blast_rating = _rating_from_score(overall_score)

    return {
        "overall_score": overall_score,
        "blast_rating": blast_rating,
        "critical_nodes": critical_nodes,
        "highest_risk_paths": highest_risk_paths,
    }


# ---------------------------------------------------------------------------
# BFS path finder
# ---------------------------------------------------------------------------

def _bfs_path(
    adj: Dict[str, List[str]],
    start: str,
    goal: str,
) -> List[str]:
    """
    Return the shortest path (list of node IDs) from `start` to `goal`
    using BFS over the adjacency dict `adj`. Returns [] if no path exists.
    """
    if start == goal:
        return [start]

    queue: List[List[str]] = [[start]]
    visited: set = {start}

    while queue:
        current_path = queue.pop(0)
        current_node = current_path[-1]

        for neighbour in adj.get(current_node, []):
            if neighbour == goal:
                return current_path + [neighbour]
            if neighbour not in visited:
                visited.add(neighbour)
                queue.append(current_path + [neighbour])

    return []
