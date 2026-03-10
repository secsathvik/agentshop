"""Verify all 5 tool API handlers work correctly."""
import asyncio
from app.capabilities.repo_analyzer.indexer.repository_indexer import RepositoryIndexer
from app.capabilities.repo_analyzer.indexer.language_registry import LanguageRegistry
from app.capabilities.repo_analyzer.parser.treesitter_parser import TreeSitterParser
from app.capabilities.repo_analyzer.parser.symbol_extractor import SymbolExtractor
from app.capabilities.repo_analyzer.graph.code_graph import CodeKnowledgeGraph
from app.capabilities.repo_analyzer.analysis.impact_engine import ImpactAnalysisEngine
from app.capabilities.repo_analyzer.tools import (
    symbol_lookup,
    get_call_graph,
    analyze_impact,
    get_architecture_summary,
    safe_rename,
)

# Build shared graph once
registry = LanguageRegistry()
files = RepositoryIndexer('.').discover_files()
parsed = TreeSitterParser(registry).parse_files(files)
symbols = SymbolExtractor().extract_all(parsed)
graph = CodeKnowledgeGraph()
graph.build(symbols, files)
engine = ImpactAnalysisEngine(graph)

async def run_checks():
    results = []

    # Tool 1: symbol_lookup
    try:
        result = await symbol_lookup(
            {"symbol": "execute_capability"}, graph
        )
        assert result["found"] == True
        assert "file" in result
        assert "start_line" in result
        results.append(("symbol_lookup (found)", True,
            f"found at {result['file']}:{result['start_line']}"))
    except Exception as e:
        results.append(("symbol_lookup (found)", False, str(e)))

    try:
        result = await symbol_lookup(
            {"symbol": "totally_fake_xyz"}, graph
        )
        assert result["found"] == False
        results.append(("symbol_lookup (not found)", True, "correctly returned found=False"))
    except Exception as e:
        results.append(("symbol_lookup (not found)", False, str(e)))

    # Tool 2: call_graph
    try:
        result = await get_call_graph(
            {"symbol": "execute_capability", "depth": 2}, graph
        )
        assert "nodes" in result
        assert "edges" in result
        results.append(("call_graph", True,
            f"{len(result['nodes'])} nodes, {len(result['edges'])} edges"))
    except Exception as e:
        results.append(("call_graph", False, str(e)))

    # Tool 3: impact_analysis
    try:
        result = await analyze_impact(
            {"symbol": "get_registry"}, graph, engine
        )
        assert "risk_score" in result
        assert "change_surface" in result
        results.append(("impact_analysis", True,
            f"risk={result['risk_score']}, surface={result['change_surface']}"))
    except Exception as e:
        results.append(("impact_analysis", False, str(e)))

    # Tool 4: architecture_summary
    try:
        result = await get_architecture_summary({}, graph)
        assert "total_files" in result
        assert "total_symbols" in result
        assert "languages" in result
        results.append(("architecture_summary", True,
            f"{result['total_files']} files, {result['total_symbols']} symbols"))
    except Exception as e:
        results.append(("architecture_summary", False, str(e)))

    # Tool 5: safe_rename
    try:
        result = await safe_rename(
            {"symbol": "get_db", "new_name": "get_session"}, graph, engine
        )
        assert "changes_required" in result
        assert "is_safe" in result
        results.append(("safe_rename", True,
            f"{result['total_files_affected']} files affected, safe={result['is_safe']}"))
    except Exception as e:
        results.append(("safe_rename", False, str(e)))

    # Print results
    print("\n=== Tool API Check Results ===\n")
    passed = failed = 0
    for name, ok, detail in results:
        status = "PASS" if ok else "FAIL"
        print(f"  [{status}] {name}")
        print(f"         {detail}")
        passed += ok
        failed += (not ok)

    print(f"\n  {passed} passed, {failed} failed")
    if failed:
        print("  Fix failures before running Prompt 7.")
    else:
        print("  All tools working. Safe to proceed with Prompt 7.")

asyncio.run(run_checks())