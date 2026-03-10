from app.capabilities.repo_analyzer.indexer.repository_indexer import RepositoryIndexer
from app.capabilities.repo_analyzer.indexer.language_registry import LanguageRegistry
from app.capabilities.repo_analyzer.parser.treesitter_parser import TreeSitterParser
from app.capabilities.repo_analyzer.parser.symbol_extractor import SymbolExtractor

registry = LanguageRegistry()
files = RepositoryIndexer('.').discover_files()
parsed = TreeSitterParser(registry).parse_files(files)
print('parsed files:', len(parsed))

symbols = SymbolExtractor().extract_all(parsed)
total = sum(len(v) for v in symbols.values())
print('total symbols:', total)

for mod, syms in list(symbols.items())[:3]:
    print(mod, '->', [s.name for s in syms[:4]])