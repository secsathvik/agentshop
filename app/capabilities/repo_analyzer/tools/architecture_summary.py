"""Architecture summary tool: high-level project structure from graph."""

from app.capabilities.repo_analyzer.graph.code_graph import CodeGraph


def get_architecture_summary(graph: CodeGraph) -> str:
    """
    Generate a high-level architecture summary from the code graph.
    """
    modules = [n for n, d in graph.graph.nodes(data=True) if d.get("kind") == "module"]
    edges = list(graph.graph.edges(data=True))
    import_edges = [e for e in edges if e[2].get("type") == "import"]

    lines = [
        f"Project has {len(modules)} modules.",
        f"{len(import_edges)} import dependency edges.",
        f"Top-level modules: {', '.join(sorted(modules)[:10])}{'...' if len(modules) > 10 else ''}.",
    ]
    return " ".join(lines)
