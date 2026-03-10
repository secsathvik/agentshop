"""Safe rename tool: suggest safe renames with impact preview."""

from app.capabilities.repo_analyzer.graph.code_graph import CodeGraph
from app.capabilities.repo_analyzer.analysis.impact_engine import compute_impact


def safe_rename(
    graph: CodeGraph,
    module: str,
    new_name: str,
) -> dict:
    """
    Preview impact of renaming a module. Does not perform the rename.
    """
    impact = compute_impact(graph, module)
    return {
        "old_name": module,
        "new_name": new_name,
        "impact": impact,
        "note": "This is a preview. No changes were made.",
    }
