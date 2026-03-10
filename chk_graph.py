"""Verify the code graph builds correctly with real edges."""
from app.capabilities.repo_analyzer.indexer.repository_indexer import RepositoryIndexer
from app.capabilities.repo_analyzer.indexer.language_registry import LanguageRegistry
from app.capabilities.repo_analyzer.parser.treesitter_parser import TreeSitterParser
from app.capabilities.repo_analyzer.parser.symbol_extractor import SymbolExtractor
from app.capabilities.repo_analyzer.graph.code_graph import CodeKnowledgeGraph

# Build pipeline
registry = LanguageRegistry()
files = RepositoryIndexer('.').discover_files()
parsed = TreeSitterParser(registry).parse_files(files)
symbols = SymbolExtractor().extract_all(parsed)

# Build graph
graph = CodeKnowledgeGraph()
graph.build(symbols, files)

# Check node count
nodes = list(graph.graph.nodes(data=True))
edges = list(graph.graph.edges(data=True))
print(f"Total nodes: {len(nodes)}")
print(f"Total edges: {len(edges)}")

# Count edge types
edge_types = {}
for u, v, data in edges:
    t = data.get('type', 'unknown')
    edge_types[t] = edge_types.get(t, 0) + 1
print(f"Edge types: {edge_types}")

# Test get_callers on a known function
print("\n=== Callers of execute_capability ===")
matches = graph.find_symbol("execute_capability")
print(f"Found symbol IDs: {matches}")
if matches:
    callers = graph.get_callers(matches[0])
    print(f"Callers: {callers}")

# Test get_callees
print("\n=== Callees of execute_capability ===")
if matches:
    callees = graph.get_callees(matches[0])
    print(f"Callees: {callees[:5]}")