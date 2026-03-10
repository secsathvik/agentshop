"""Builds and stores the code graph using NetworkX."""

from pathlib import Path
from typing import Any

import networkx as nx

from app.capabilities.repo_analyzer.parser.symbol_extractor import Symbol
from app.capabilities.repo_analyzer.indexer.repository_indexer import IndexedFile


def _symbol_id(module_name: str, symbol_name: str) -> str:
    return f"{module_name}::{symbol_name}"


class CodeKnowledgeGraph:
    """A directed graph of files, modules, symbols, and their relationships."""

    CALLS = "CALLS"
    IMPORTS = "IMPORTS"
    DEFINES = "DEFINES"
    INHERITS = "INHERITS"
    CONTAINS = "CONTAINS"

    def __init__(self) -> None:
        self._graph = nx.DiGraph()

    @property
    def graph(self) -> nx.DiGraph:
        """Access the underlying NetworkX graph."""
        return self._graph

    def build(
        self,
        symbols_by_module: dict[str, list[Symbol]],
        indexed_files: list[IndexedFile],
    ) -> None:
        """Build the graph from symbols and indexed files."""

        # Map module_name -> relative_path
        module_to_path: dict[str, str] = {
            f.module_name: f.relative_path for f in indexed_files
        }

        # Step 1 — Add all nodes
        for f in indexed_files:
            self._graph.add_node(
                f.relative_path,
                type="file",
                language=f.language,
                relative_path=f.relative_path,
                module_name=f.module_name,
            )
        for mod_name in symbols_by_module:
            self._graph.add_node(mod_name, type="module", module_name=mod_name)
        for mod_name, symbols in symbols_by_module.items():
            for sym in symbols:
                sid = _symbol_id(mod_name, sym.name)
                self._graph.add_node(
                    sid,
                    type="symbol",
                    name=sym.name,
                    symbol_type=sym.symbol_type,
                    file_path=sym.file_path,
                    module_name=sym.module_name,
                    start_line=sym.start_line,
                    end_line=sym.end_line,
                )

        # Step 2 — Add DEFINES edges (file -> symbol)
        for mod_name, symbols in symbols_by_module.items():
            path = module_to_path.get(mod_name)
            if not path:
                continue
            for sym in symbols:
                sid = _symbol_id(mod_name, sym.name)
                self._graph.add_edge(path, sid, type=self.DEFINES)

        # Step 3 — Add CONTAINS edges (module -> symbol)
        for mod_name, symbols in symbols_by_module.items():
            for sym in symbols:
                sid = _symbol_id(mod_name, sym.name)
                self._graph.add_edge(mod_name, sid, type=self.CONTAINS)

        # Step 4 — Add CALLS edges
        name_to_symbol_ids: dict[str, list[str]] = {}
        for mod_name, symbols in symbols_by_module.items():
            for sym in symbols:
                if sym.symbol_type == "import":
                    continue
                sid = _symbol_id(mod_name, sym.name)
                name_to_symbol_ids.setdefault(sym.name, []).append(sid)

        for mod_name, symbols in symbols_by_module.items():
            for sym in symbols:
                if sym.symbol_type == "import" or not sym.calls:
                    continue
                caller_id = _symbol_id(mod_name, sym.name)
                for called_name in sym.calls:
                    candidates = name_to_symbol_ids.get(called_name, [])
                    if not candidates:
                        continue
                    target_id = self._pick_best_match(candidates, mod_name)
                    if target_id:
                        self._graph.add_edge(caller_id, target_id, type=self.CALLS)

        # Step 5 — Add IMPORTS edges (file -> module)
        for mod_name, symbols in symbols_by_module.items():
            path = module_to_path.get(mod_name)
            if not path:
                continue
            for sym in symbols:
                if sym.symbol_type != "import":
                    continue
                target_module = sym.name.strip()
                if not target_module:
                    continue
                if self._graph.has_node(target_module) and self._graph.nodes[target_module].get("type") == "module":
                    self._graph.add_edge(path, target_module, type=self.IMPORTS)

        # Step 6 — Add INHERITS edges (only if Symbol has bases attribute)
        for mod_name, symbols in symbols_by_module.items():
            for sym in symbols:
                if sym.symbol_type != "class":
                    continue
                sym_bases = getattr(sym, "bases", None) or []
                if not sym_bases:
                    continue
                caller_id = _symbol_id(mod_name, sym.name)
                for base_name in sym_bases:
                    candidates = name_to_symbol_ids.get(base_name, [])
                    base_classes = [
                        c for c in candidates
                        if self._graph.nodes.get(c, {}).get("symbol_type") == "class"
                    ]
                    if not base_classes:
                        continue
                    target_id = self._pick_best_match(base_classes, mod_name)
                    if target_id:
                        self._graph.add_edge(caller_id, target_id, type=self.INHERITS)

    def _pick_best_match(self, candidate_ids: list[str], module_hint: str) -> str | None:
        """Prefer same-module match, then first cross-module. Never skip."""
        if not candidate_ids:
            return None
        same_module = [c for c in candidate_ids if c.startswith(module_hint + "::")]
        if same_module:
            return same_module[0]
        return candidate_ids[0]

    def get_callers(self, symbol_id: str) -> list[str]:
        """Returns symbol IDs that have CALLS edge pointing to this symbol."""
        result: list[str] = []
        for pred in self._graph.predecessors(symbol_id):
            edge_data = self._graph.edges.get((pred, symbol_id), {})
            if edge_data.get("type") == self.CALLS:
                result.append(pred)
        return result

    def get_callees(self, symbol_id: str) -> list[str]:
        """Returns symbol IDs this symbol calls."""
        result: list[str] = []
        for succ in self._graph.successors(symbol_id):
            edge_data = self._graph.edges.get((symbol_id, succ), {})
            if edge_data.get("type") == self.CALLS:
                result.append(succ)
        return result

    def get_dependencies(self, module_name: str) -> list[str]:
        """Returns modules this module imports."""
        result: list[str] = []
        for node_id, data in self._graph.nodes(data=True):
            if data.get("type") != "file" or data.get("module_name") != module_name:
                continue
            for succ in self._graph.successors(node_id):
                edge_data = self._graph.edges.get((node_id, succ), {})
                if edge_data.get("type") == self.IMPORTS:
                    result.append(succ)
        return result

    def get_dependents(self, module_name: str) -> list[str]:
        """Returns modules that import this module."""
        result: list[str] = []
        if not self._graph.has_node(module_name):
            return result
        for pred in self._graph.predecessors(module_name):
            edge_data = self._graph.edges.get((pred, module_name), {})
            if edge_data.get("type") != self.IMPORTS:
                continue
            pred_data = self._graph.nodes.get(pred, {})
            if pred_data.get("type") == "file":
                mod = pred_data.get("module_name")
                if mod and mod not in result:
                    result.append(mod)
        return result

    def find_symbol(self, name: str, module_hint: str | None = None) -> list[str]:
        """Searches symbol nodes by name. If module_hint provided, prefer symbols in that module."""
        matches: list[str] = []
        for node_id, data in self._graph.nodes(data=True):
            if data.get("type") != "symbol":
                continue
            if data.get("name") == name:
                matches.append(node_id)
        if module_hint and matches:
            same_mod = [m for m in matches if m.startswith(module_hint + "::")]
            if same_mod:
                return same_mod
        return matches

    def to_dict(self) -> dict:
        """Serializes graph to dict for caching."""
        return nx.node_link_data(self._graph)

    def from_dict(self, data: dict) -> None:
        """Loads graph from dict."""
        self._graph = nx.node_link_graph(data)


# Legacy aliases for backward compatibility
class CodeGraph(CodeKnowledgeGraph):
    """Alias for CodeKnowledgeGraph for backward compatibility."""

    pass


def build_graph(
    root: Path,
    indexed_files: list[IndexedFile],
    symbols_by_file: dict[str, list[Symbol]] | None = None,
    symbols_by_module: dict[str, list[Symbol]] | None = None,
) -> CodeKnowledgeGraph:
    """
    Build a graph from indexed files and symbols.
    Converts symbols_by_file to symbols_by_module if needed, then uses CodeKnowledgeGraph.build.
    """
    if symbols_by_module is None:
        symbols_by_module = {}
        for f in indexed_files:
            path_key = str(f.path)
            if symbols_by_file and path_key in symbols_by_file:
                symbols_by_module.setdefault(f.module_name, []).extend(
                    symbols_by_file[path_key]
                )
    g = CodeKnowledgeGraph()
    g.build(symbols_by_module, indexed_files)
    return g
