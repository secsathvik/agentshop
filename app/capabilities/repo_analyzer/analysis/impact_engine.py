"""Graph traversal for impact analysis."""

from dataclasses import dataclass
from pathlib import Path

from app.capabilities.repo_analyzer.graph.code_graph import CodeKnowledgeGraph


@dataclass
class CallerInfo:
    """Info about a caller of a symbol."""

    symbol_id: str
    name: str
    file_path: str
    line: int


@dataclass
class ImpactReport:
    """Impact analysis report for a symbol."""

    symbol: str
    symbol_type: str
    file_path: str
    direct_callers: list[CallerInfo]
    indirect_callers: list[CallerInfo]
    affected_modules: list[str]
    affected_files: list[str]
    affected_tests: list[str]
    risk_score: str
    change_surface: int


@dataclass
class SafeRenameReport:
    """Report for safe rename analysis."""

    symbol: str
    occurrences: list[dict]
    total_files: int
    is_safe: bool
    warnings: list[str]


def _caller_info(graph: CodeKnowledgeGraph, symbol_id: str) -> CallerInfo | None:
    """Build CallerInfo from graph node data."""
    data = graph.graph.nodes.get(symbol_id, {})
    if data.get("type") != "symbol":
        return None
    return CallerInfo(
        symbol_id=symbol_id,
        name=data.get("name", ""),
        file_path=data.get("file_path", ""),
        line=data.get("start_line", 0),
    )


def _empty_report(symbol: str) -> ImpactReport:
    """Return ImpactReport with empty lists and risk_score=unknown."""
    return ImpactReport(
        symbol=symbol,
        symbol_type="",
        file_path="",
        direct_callers=[],
        indirect_callers=[],
        affected_modules=[],
        affected_files=[],
        affected_tests=[],
        risk_score="unknown",
        change_surface=0,
    )


class ImpactAnalysisEngine:
    """Analyzes impact of changes to symbols using the code knowledge graph."""

    def __init__(self, graph: CodeKnowledgeGraph, repo_path: str | None = None) -> None:
        self.graph = graph
        self.repo_path = repo_path

    def analyze_impact(
        self,
        symbol_name: str,
        module_hint: str | None = None,
    ) -> ImpactReport:
        """Analyze impact of changing a symbol."""
        matches = self.graph.find_symbol(symbol_name, module_hint)
        if not matches:
            return _empty_report(symbol_name)

        symbol_id = matches[0]
        data = self.graph.graph.nodes.get(symbol_id, {})

        # Step 2: Direct callers
        direct_ids = self.graph.get_callers(symbol_id)
        direct_callers = []
        for sid in direct_ids:
            info = _caller_info(self.graph, sid)
            if info:
                direct_callers.append(info)

        # Step 3: Indirect callers (2 hops max)
        indirect_ids: set[str] = set()
        for direct_id in direct_ids:
            for sid in self.graph.get_callers(direct_id):
                if sid not in direct_ids and sid != symbol_id:
                    indirect_ids.add(sid)
        indirect_callers = []
        for sid in indirect_ids:
            info = _caller_info(self.graph, sid)
            if info:
                indirect_callers.append(info)

        # Step 4: Affected modules and files
        affected_modules: set[str] = set()
        affected_files: set[str] = set()
        for info in direct_callers + indirect_callers:
            caller_data = self.graph.graph.nodes.get(info.symbol_id, {})
            mod = caller_data.get("module_name")
            if mod:
                affected_modules.add(mod)
            if info.file_path:
                affected_files.add(info.file_path)

        # Step 5: Affected tests
        affected_tests = [
            f for f in affected_files
            if "test_" in f or "_test" in f or "/tests/" in f
        ]

        # Step 6: Risk scoring
        change_surface = len(direct_callers) + len(indirect_callers)
        if change_surface == 0:
            risk_score = "low"
        elif change_surface <= 3:
            risk_score = "medium"
        elif change_surface <= 10:
            risk_score = "high"
        else:
            risk_score = "critical"

        return ImpactReport(
            symbol=symbol_name,
            symbol_type=data.get("symbol_type", ""),
            file_path=data.get("file_path", ""),
            direct_callers=direct_callers,
            indirect_callers=indirect_callers,
            affected_modules=sorted(affected_modules),
            affected_files=sorted(affected_files),
            affected_tests=sorted(affected_tests),
            risk_score=risk_score,
            change_surface=change_surface,
        )

    def find_safe_rename_targets(self, symbol_name: str) -> SafeRenameReport:
        """Analyze whether a symbol can be safely renamed."""
        matches = self.graph.find_symbol(symbol_name)
        warnings: list[str] = []

        if not matches:
            return SafeRenameReport(
                symbol=symbol_name,
                occurrences=[],
                total_files=0,
                is_safe=True,
                warnings=["Symbol not found in graph"],
            )

        occurrences: list[dict] = []
        seen_files: set[str] = set()

        # DEFINES edges: file -> symbol (definition site)
        for symbol_id in matches:
            data = self.graph.graph.nodes.get(symbol_id, {})
            fp = data.get("file_path", "")
            line = data.get("start_line", 0)
            context_line = self._get_context_line(fp, line)
            occurrences.append({
                "file_path": fp,
                "line": line,
                "column": 0,
                "context_line": context_line,
                "type": "definition",
            })
            if fp:
                seen_files.add(fp)

        # CALLS edges: callers of this symbol
        for symbol_id in matches:
            for caller_id in self.graph.get_callers(symbol_id):
                caller_data = self.graph.graph.nodes.get(caller_id, {})
                fp = caller_data.get("file_path", "")
                line = caller_data.get("start_line", 0)
                context_line = self._get_context_line(fp, line)
                occurrences.append({
                    "file_path": fp,
                    "line": line,
                    "column": 0,
                    "context_line": context_line,
                    "type": "call",
                })
                if fp:
                    seen_files.add(fp)

        # Heuristic warnings (string/decorator detection would need source parsing)
        if any(o.get("type") == "call" for o in occurrences):
            pass  # Could add "references from other modules" warning

        is_safe = len(warnings) == 0

        return SafeRenameReport(
            symbol=symbol_name,
            occurrences=occurrences,
            total_files=len(seen_files),
            is_safe=is_safe,
            warnings=warnings,
        )

    def _get_context_line(self, file_path: str, line: int) -> str:
        """Get the line of code at file_path:line. Returns empty if unavailable."""
        if not self.repo_path or not file_path:
            return ""
        try:
            base = Path(self.repo_path) if isinstance(self.repo_path, str) else self.repo_path
            full = (base / file_path).resolve()
            if not full.exists():
                return ""
            lines = full.read_text(encoding="utf-8", errors="replace").splitlines()
            if 1 <= line <= len(lines):
                return lines[line - 1].strip()
        except (OSError, UnicodeDecodeError):
            pass
        return ""


# Legacy functions for backward compatibility
def get_downstream_modules(
    graph: CodeKnowledgeGraph, module: str, max_depth: int = 10
) -> set[str]:
    """Get modules that depend on the given module (transitive via IMPORTS)."""
    result: set[str] = set()
    visited: set[str] = set()
    stack = [(module, 0)]
    while stack:
        node, depth = stack.pop()
        if depth > max_depth or node in visited:
            continue
        visited.add(node)
        for dep in graph.get_dependents(node):
            result.add(dep)
            stack.append((dep, depth + 1))
    return result


def get_upstream_modules(
    graph: CodeKnowledgeGraph, module: str, max_depth: int = 10
) -> set[str]:
    """Get modules the given module depends on (transitive via IMPORTS)."""
    result: set[str] = set()
    visited: set[str] = set()
    stack = [(module, 0)]
    while stack:
        node, depth = stack.pop()
        if depth > max_depth or node in visited:
            continue
        visited.add(node)
        for dep in graph.get_dependencies(node):
            result.add(dep)
            stack.append((dep, depth + 1))
    return result


def compute_impact(graph: CodeKnowledgeGraph, module: str) -> dict:
    """Compute impact of changes to a module."""
    upstream = get_upstream_modules(graph, module)
    downstream = get_downstream_modules(graph, module)
    return {
        "module": module,
        "upstream": list(upstream),
        "downstream": list(downstream),
        "upstream_count": len(upstream),
        "downstream_count": len(downstream),
    }
