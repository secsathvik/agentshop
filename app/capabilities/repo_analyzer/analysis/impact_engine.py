"""Graph traversal for impact analysis."""

from app.capabilities.repo_analyzer.graph.code_graph import CodeGraph


def get_downstream_modules(graph: CodeGraph, module: str, max_depth: int = 10) -> set[str]:
    """
    Get all modules that depend on the given module (directly or transitively).
    Traverses predecessors (nodes that point to this module).
    """
    result: set[str] = set()
    visited: set[str] = set()
    stack = [(module, 0)]

    while stack:
        node, depth = stack.pop()
        if depth > max_depth or node in visited:
            continue
        visited.add(node)

        for pred in graph.predecessors(node):
            if graph.graph.nodes.get(pred, {}).get("kind") == "module":
                result.add(pred)
            stack.append((pred, depth + 1))

    return result


def get_upstream_modules(graph: CodeGraph, module: str, max_depth: int = 10) -> set[str]:
    """
    Get all modules that the given module depends on (directly or transitively).
    Traverses successors (nodes this module points to).
    """
    result: set[str] = set()
    visited: set[str] = set()
    stack = [(module, 0)]

    while stack:
        node, depth = stack.pop()
        if depth > max_depth or node in visited:
            continue
        visited.add(node)

        for succ in graph.successors(node):
            if graph.graph.nodes.get(succ, {}).get("kind") == "module":
                result.add(succ)
            stack.append((succ, depth + 1))

    return result


def compute_impact(graph: CodeGraph, module: str) -> dict:
    """
    Compute impact of changes to a module: upstream (dependencies) and downstream (dependents).
    """
    upstream = get_upstream_modules(graph, module)
    downstream = get_downstream_modules(graph, module)
    return {
        "module": module,
        "upstream": list(upstream),
        "downstream": list(downstream),
        "upstream_count": len(upstream),
        "downstream_count": len(downstream),
    }
