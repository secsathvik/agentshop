"""Call graph tool: BFS traversal of call relationships around a symbol."""

from collections import deque

from app.capabilities.repo_analyzer.graph.code_graph import CodeKnowledgeGraph


async def get_call_graph(input_data: dict, graph: CodeKnowledgeGraph) -> dict:
    """
    Get call graph around a symbol via BFS up to depth hops.

    Input: {"symbol": str, "depth": int (default 2, max 4)}
    Returns nodes and edges for agent-friendly consumption.
    """
    symbol_name = input_data.get("symbol", "")
    depth = min(
        max(int(input_data.get("depth", 2)), 1),
        4,
    )

    if not symbol_name:
        return {
            "root": "",
            "nodes": [],
            "edges": [],
            "depth": depth,
        }

    matches = graph.find_symbol(symbol_name)
    if not matches:
        return {
            "root": symbol_name,
            "nodes": [],
            "edges": [],
            "depth": depth,
        }

    root_id = matches[0]
    root_data = graph.graph.nodes.get(root_id, {})
    root_name = root_data.get("name", symbol_name)

    # BFS: (node_id, current_depth)
    visited: set[str] = set()
    queue: deque[tuple[str, int]] = deque([(root_id, 0)])
    nodes_dict: dict[str, dict] = {}
    edges_list: list[dict] = []

    def add_node(sid: str) -> None:
        if sid in nodes_dict:
            return
        data = graph.graph.nodes.get(sid, {})
        nodes_dict[sid] = {
            "id": sid,
            "name": data.get("name", sid),
            "type": data.get("symbol_type", "symbol"),
            "file": data.get("file_path", ""),
        }

    add_node(root_id)

    while queue:
        node_id, d = queue.popleft()
        if node_id in visited or d >= depth:
            continue
        visited.add(node_id)

        # Predecessors (callers)
        for pred_id in graph.get_callers(node_id):
            add_node(pred_id)
            edges_list.append({"from": pred_id, "to": node_id})
            if pred_id not in visited and d + 1 < depth:
                queue.append((pred_id, d + 1))

        # Successors (callees)
        for succ_id in graph.get_callees(node_id):
            add_node(succ_id)
            edges_list.append({"from": node_id, "to": succ_id})
            if succ_id not in visited and d + 1 < depth:
                queue.append((succ_id, d + 1))

    return {
        "root": root_name,
        "nodes": list(nodes_dict.values()),
        "edges": edges_list,
        "depth": depth,
    }
