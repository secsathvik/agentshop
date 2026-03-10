from app.capabilities.repo_analyzer.indexer.repository_indexer import RepositoryIndexer
from app.capabilities.repo_analyzer.indexer.language_registry import LanguageRegistry
from app.capabilities.repo_analyzer.parser.treesitter_parser import TreeSitterParser
from app.capabilities.repo_analyzer.parser.symbol_extractor import SymbolExtractor

registry = LanguageRegistry()
files = RepositoryIndexer('.').discover_files()
parsed = TreeSitterParser(registry).parse_files(files)
symbols = SymbolExtractor().extract_all(parsed)

print("=== Modules with symbols ===")
count = 0
for mod, syms in symbols.items():
    if syms:
        print(f"{mod} -> {[s.name for s in syms[:5]]}")
        for s in syms[:2]:
            print(f"  {s.name}: type={s.symbol_type}, calls={s.calls[:3]}")
        count += 1
    if count >= 5:
        break