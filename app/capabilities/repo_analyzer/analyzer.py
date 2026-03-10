"""
Main orchestrator for repository analysis.

Delegates to the legacy implementation (analyzer_legacy) for the API.
The new tree-sitter pipeline (indexer, parser, graph, analysis, tools) is
available for incremental migration.
"""

from app.capabilities.repo_analyzer.analyzer_legacy import analyze, analyze_async

__all__ = ["analyze", "analyze_async"]


if __name__ == "__main__":
    import asyncio
    import json
    import sys

    path = sys.argv[1] if len(sys.argv) > 1 else "."
    result = asyncio.run(analyze_async({"repo_path": path}))
    print(json.dumps(result, indent=2, default=str))
