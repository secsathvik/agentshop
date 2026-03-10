"""Call graph tool: get call/import relationships for a module."""

from app.capabilities.repo_analyzer.graph.code_graph import CodeGraph


def get_call_graph(
    graph: CodeGraph,
    module: str,
    *,
    direction: str = "both",
) -> dict:
    """
    Get call/import graph for a module.
    direction: "upstream" | "downstream" | "both"
    """
    from app.capabilities.repo_analyzer.analysis.impact_engine import (
        get_upstream_modules,
        get_downstream_modules,
    )

    upstream = get_upstream_modules(graph, module) if direction in ("upstream", "both") else set()
    downstream = get_downstream_modules(graph, module) if direction in ("downstream", "both") else set()

    return {
        "module": module,
        "imports": list(upstream),
        "imported_by": list(downstream),
    }
