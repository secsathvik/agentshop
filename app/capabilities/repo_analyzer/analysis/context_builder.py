"""Builds minimal LLM context from the code graph."""

from pathlib import Path

from app.capabilities.repo_analyzer.graph.code_graph import CodeGraph
from app.capabilities.repo_analyzer.analysis.impact_engine import (
    get_upstream_modules,
    get_downstream_modules,
)


def build_context(
    graph: CodeGraph,
    root: Path,
    module: str,
    include_upstream: bool = True,
    include_downstream: bool = True,
    max_files: int = 20,
) -> str:
    """
    Build context string for an LLM by including relevant module file contents.

    Includes the target module plus its upstream/downstream dependencies.
    """
    modules_to_include: set[str] = {module}
    if include_upstream:
        modules_to_include |= get_upstream_modules(graph, module)
    if include_downstream:
        modules_to_include |= get_downstream_modules(graph, module)

    # Limit to max_files
    mod_list = list(modules_to_include)[:max_files]
    parts = []

    for mod in mod_list:
        data = graph.graph.nodes.get(mod, {})
        path = data.get("path")
        if not path:
            continue
        file_path = root / path
        if not file_path.exists():
            continue
        try:
            content = file_path.read_text(encoding="utf-8", errors="replace")
            parts.append(f"=== {path} ===\n{content}")
        except (OSError, UnicodeDecodeError):
            pass

    return "\n\n".join(parts)


def build_minimal_context(
    graph: CodeGraph,
    module: str,
    max_nodes: int = 50,
) -> str:
    """
    Build a minimal context string from graph structure only (no file contents).

    Useful for quick summaries without reading files.
    """
    data = graph.graph.nodes.get(module, {})
    if not data:
        return f"Module '{module}' not found in graph."

    upstream = get_upstream_modules(graph, module)
    downstream = get_downstream_modules(graph, module)

    lines = [
        f"Module: {module}",
        f"Path: {data.get('path', '?')}",
        f"Language: {data.get('language', '?')}",
        f"Upstream ({len(upstream)}): {', '.join(sorted(upstream)[:10])}{'...' if len(upstream) > 10 else ''}",
        f"Downstream ({len(downstream)}): {', '.join(sorted(downstream)[:10])}{'...' if len(downstream) > 10 else ''}",
    ]
    return "\n".join(lines)
