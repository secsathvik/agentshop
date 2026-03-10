"""Symbol lookup tool: find where a symbol is defined."""

from app.capabilities.repo_analyzer.graph.code_graph import CodeGraph


def symbol_lookup(graph: CodeGraph, symbol_name: str, module: str | None = None) -> list[dict]:
    """
    Look up a symbol in the graph. If module is given, restricts search to that module.
    """
    results = []
    for node_id, data in graph.graph.nodes(data=True):
        if data.get("name") == symbol_name:
            if module and data.get("module") != module:
                continue
            results.append(
                {
                    "node_id": node_id,
                    "kind": data.get("kind"),
                    "name": data.get("name"),
                    "module": data.get("module"),
                    "file": data.get("file"),
                    "line_start": data.get("line_start"),
                    "line_end": data.get("line_end"),
                }
            )
    return results
