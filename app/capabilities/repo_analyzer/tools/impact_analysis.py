"""Impact analysis tool: compute change impact for a module."""

from app.capabilities.repo_analyzer.graph.code_graph import CodeGraph
from app.capabilities.repo_analyzer.analysis.impact_engine import compute_impact


def run_impact_analysis(graph: CodeGraph, module: str) -> dict:
    """
    Run impact analysis for a module. Returns upstream and downstream modules.
    """
    return compute_impact(graph, module)
