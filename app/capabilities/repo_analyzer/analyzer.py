"""
Repository analyzer with graph cache and tool handlers.

Exposes async handlers for symbol_lookup, call_graph, impact_analysis,
architecture_summary, and safe_rename. Uses in-memory and disk cache to
avoid rebuilding the graph on repeated calls.
"""

import asyncio
from pathlib import Path

from app.capabilities.repo_analyzer.graph.code_graph import CodeKnowledgeGraph
from app.capabilities.repo_analyzer.graph.graph_cache import GraphCache
from app.capabilities.repo_analyzer.indexer.language_registry import LanguageRegistry
from app.capabilities.repo_analyzer.indexer.repository_indexer import RepositoryIndexer
from app.capabilities.repo_analyzer.parser.symbol_extractor import SymbolExtractor
from app.capabilities.repo_analyzer.parser.treesitter_parser import TreeSitterParser
from app.capabilities.repo_analyzer.analysis.impact_engine import ImpactAnalysisEngine
from app.capabilities.repo_analyzer.tools import (
    symbol_lookup,
    get_call_graph,
    analyze_impact,
    get_architecture_summary,
    safe_rename,
)

# Cache built graphs per repo_path
_graph_cache: dict[str, CodeKnowledgeGraph] = {}


def _normalize_repo_path(repo_path: str) -> str:
    """Normalize path for cache key."""
    return str(Path(repo_path).resolve())


def _build_graph_sync(repo_path: str) -> CodeKnowledgeGraph:
    """Run the full pipeline synchronously. Called from executor."""
    cache = GraphCache(repo_path)
    indexer = RepositoryIndexer(repo_path)
    files = indexer.discover_files()

    # Check disk cache first
    if not cache.is_stale(files):
        loaded = cache.load()
        if loaded:
            graph_data, _ = loaded
            g = CodeKnowledgeGraph()
            g.from_dict(graph_data)
            return g

    # Build from scratch
    registry = LanguageRegistry()
    parsed = TreeSitterParser(registry).parse_files(files)
    symbols = SymbolExtractor().extract_all(parsed)
    graph = CodeKnowledgeGraph()
    graph.build(symbols, files)

    # Save to disk cache
    file_hashes = {f.relative_path: cache.get_file_hash(f.path) for f in files}
    cache.save(graph, file_hashes)

    return graph


async def _get_or_build_graph(repo_path: str) -> CodeKnowledgeGraph:
    """
    Get or build the code graph for a repository.
    Uses in-memory cache and disk cache. Runs sync pipeline in executor.
    """
    key = _normalize_repo_path(repo_path)

    if key in _graph_cache:
        cache = GraphCache(repo_path)
        indexer = RepositoryIndexer(repo_path)
        files = indexer.discover_files()
        if not cache.is_stale(files):
            return _graph_cache[key]
        # Stale: fall through to rebuild

    loop = asyncio.get_event_loop()
    graph = await loop.run_in_executor(None, _build_graph_sync, repo_path)
    _graph_cache[key] = graph
    return graph


async def handle_symbol_lookup(input_data: dict) -> dict:
    """Look up a symbol by name. Returns definition location, callers, and callees."""
    try:
        repo_path = input_data.get("repo_path")
        if not repo_path:
            return {"success": False, "error": "repo_path is required"}

        graph = await _get_or_build_graph(repo_path)
        result = await symbol_lookup(input_data, graph)
        return {"success": True, **result}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def handle_call_graph(input_data: dict) -> dict:
    """Get the call graph for a symbol up to N hops deep."""
    try:
        repo_path = input_data.get("repo_path")
        if not repo_path:
            return {"success": False, "error": "repo_path is required"}

        graph = await _get_or_build_graph(repo_path)
        result = await get_call_graph(input_data, graph)
        return {"success": True, **result}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def handle_impact_analysis(input_data: dict) -> dict:
    """Analyze what breaks if a symbol changes. Returns risk score and affected callers."""
    try:
        repo_path = input_data.get("repo_path")
        if not repo_path:
            return {"success": False, "error": "repo_path is required"}

        graph = await _get_or_build_graph(repo_path)
        engine = ImpactAnalysisEngine(graph, repo_path=repo_path)
        result = await analyze_impact(input_data, graph, engine)
        return {"success": True, **result}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def handle_architecture_summary(input_data: dict) -> dict:
    """Get architecture summary for the repository."""
    try:
        repo_path = input_data.get("repo_path")
        if not repo_path:
            return {"success": False, "error": "repo_path is required"}

        graph = await _get_or_build_graph(repo_path)
        result = await get_architecture_summary(input_data, graph)
        return {"success": True, **result}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def handle_safe_rename(input_data: dict) -> dict:
    """Find all locations that need updating for a symbol rename. Read-only, no changes made."""
    try:
        repo_path = input_data.get("repo_path")
        if not repo_path:
            return {"success": False, "error": "repo_path is required"}

        graph = await _get_or_build_graph(repo_path)
        engine = ImpactAnalysisEngine(graph, repo_path=repo_path)
        result = await safe_rename(input_data, graph, engine)
        return {"success": True, **result}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def analyze_async(input_data: dict) -> dict:
    """
    Backwards-compatible entry point. Calls handle_architecture_summary.
    """
    return await handle_architecture_summary(input_data)


# Re-export sync analyze for backwards compatibility
from app.capabilities.repo_analyzer.analyzer_legacy import analyze

__all__ = [
    "analyze",
    "analyze_async",
    "handle_symbol_lookup",
    "handle_call_graph",
    "handle_impact_analysis",
    "handle_architecture_summary",
    "handle_safe_rename",
]
