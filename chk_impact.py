"""Verify impact analysis engine works correctly."""
from app.capabilities.repo_analyzer.indexer.repository_indexer import RepositoryIndexer
from app.capabilities.repo_analyzer.indexer.language_registry import LanguageRegistry
from app.capabilities.repo_analyzer.parser.treesitter_parser import TreeSitterParser
from app.capabilities.repo_analyzer.parser.symbol_extractor import SymbolExtractor
from app.capabilities.repo_analyzer.graph.code_graph import CodeKnowledgeGraph
from app.capabilities.repo_analyzer.analysis.impact_engine import ImpactAnalysisEngine

# Build pipeline
registry = LanguageRegistry()
files = RepositoryIndexer('.').discover_files()
parsed = TreeSitterParser(registry).parse_files(files)
symbols = SymbolExtractor().extract_all(parsed)
graph = CodeKnowledgeGraph()
graph.build(symbols, files)
engine = ImpactAnalysisEngine(graph)

# Test 1: impact on get_db (should have callers - used in routes)
print("=== Impact: get_db ===")
report = engine.analyze_impact("get_db")
print(f"  symbol: {report.symbol}")
print(f"  risk_score: {report.risk_score}")
print(f"  direct_callers: {len(report.direct_callers)}")
print(f"  indirect_callers: {len(report.indirect_callers)}")
print(f"  affected_files: {report.affected_files[:3]}")
print(f"  change_surface: {report.change_surface}")

# Test 2: impact on a function with no callers
print("\n=== Impact: execute_capability ===")
report2 = engine.analyze_impact("execute_capability")
print(f"  risk_score: {report2.risk_score}")
print(f"  direct_callers: {len(report2.direct_callers)}")

# Test 3: safe rename targets
print("\n=== Safe rename: get_db -> get_session ===")
rename = engine.find_safe_rename_targets("get_db")
print(f"  occurrences: {len(rename.occurrences)}")
print(f"  total_files: {rename.total_files}")
print(f"  is_safe: {rename.is_safe}")
print(f"  warnings: {rename.warnings}")