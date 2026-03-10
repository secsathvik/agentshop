"""Builds and stores the code graph using NetworkX."""

from pathlib import Path
from typing import Any

import networkx as nx

from app.capabilities.repo_analyzer.parser.symbol_extractor import Symbol
from app.capabilities.repo_analyzer.indexer.repository_indexer import IndexedFile


class CodeGraph:
    """A directed graph of code symbols and their relationships."""

    def __init__(self):
        self._graph = nx.DiGraph()

    def add_node(self, node_id: str, **attrs: Any) -> None:
        """Add or update a node."""
        self._graph.add_node(node_id, **attrs)

    def add_edge(self, source: str, target: str, **attrs: Any) -> None:
        """Add an edge between nodes."""
        self._graph.add_edge(source, target, **attrs)

    def nodes(self):
        """Iterate over nodes."""
        return self._graph.nodes()

    def edges(self):
        """Iterate over edges."""
        return self._graph.edges()

    def successors(self, node: str):
        """Get nodes that this node depends on."""
        return self._graph.successors(node)

    def predecessors(self, node: str):
        """Get nodes that depend on this node."""
        return self._graph.predecessors(node)

    @property
    def graph(self) -> nx.DiGraph:
        """Access the underlying NetworkX graph."""
        return self._graph

    def to_dict(self) -> dict:
        """Serialize graph for caching (node_link format)."""
        return nx.node_link_data(self._graph)


def build_graph(
    root: Path,
    indexed_files: list[IndexedFile],
    symbols_by_file: dict[str, list[Symbol]] | None = None,
    symbols_by_module: dict[str, list[Symbol]] | None = None,
) -> CodeGraph:
    """
    Build a CodeGraph from indexed files and extracted symbols.

    Pass either symbols_by_file (path -> symbols) or symbols_by_module (module_name -> symbols).
    """
    g = CodeGraph()

    for f in indexed_files:
        if symbols_by_module is not None:
            symbols = symbols_by_module.get(f.module_name, [])
        else:
            symbols = (symbols_by_file or {}).get(str(f.path), [])

        g.add_node(f.module_name, kind="module", path=f.relative_path, language=f.language)

        for sym in symbols:
            sym_id = f"{f.module_name}::{sym.symbol_type}::{sym.name}"
            g.add_node(
                sym_id,
                kind=sym.symbol_type,
                name=sym.name,
                module=f.module_name,
                file=f.relative_path,
                line_start=sym.start_line,
                line_end=sym.end_line,
            )
            g.add_edge(sym_id, f.module_name, type="defined_in")

        for sym in symbols:
            if sym.symbol_type == "import":
                # Parse import to extract module refs (simplified)
                imp = sym.name
                if " import " in imp:
                    # from x import y
                    parts = imp.split(" import ", 1)[0].replace("from ", "").strip().split(".")
                else:
                    # import x
                    parts = imp.replace("import ", "").strip().split(",")[0].strip().split(".")
                target = ".".join(parts)
                if target and target != f.module_name:
                    g.add_edge(f.module_name, target, type="import")

    return g
