"""Builds minimal LLM context from the code graph."""

from pathlib import Path

from app.capabilities.repo_analyzer.graph.code_graph import CodeKnowledgeGraph
from app.capabilities.repo_analyzer.analysis.impact_engine import ImpactReport


class ContextBuilder:
    """Builds compact text context for LLM and agent consumption."""

    MAX_CALLERS = 10
    MAX_CALLEES = 10
    MAX_TOKENS = 500

    def build_symbol_context(
        self,
        symbol_id: str,
        graph: CodeKnowledgeGraph,
    ) -> str:
        """Builds a compact text context for LLM consumption."""
        data = graph.graph.nodes.get(symbol_id, {})
        if not data or data.get("type") != "symbol":
            return f"Symbol {symbol_id} not found."

        name = data.get("name", "?")
        symbol_type = data.get("symbol_type", "?")
        file_path = data.get("file_path", "?")
        start_line = data.get("start_line", 0)
        module_name = data.get("module_name", "?")

        lines = [
            f"Symbol: {name} ({symbol_type})",
            f"File: {file_path}, Line {start_line}",
            "",
        ]

        callers = graph.get_callers(symbol_id)
        caller_infos = []
        for cid in callers[: self.MAX_CALLERS]:
            cdata = graph.graph.nodes.get(cid, {})
            caller_infos.append(
                f"  - {cdata.get('name', '?')} in {cdata.get('file_path', '?')}:{cdata.get('start_line', 0)}"
            )
        lines.append(f"Callers ({len(callers)}):")
        lines.extend(caller_infos if caller_infos else ["  (none)"])
        lines.append("")

        callees = graph.get_callees(symbol_id)
        callee_infos = []
        for cid in callees[: self.MAX_CALLEES]:
            cdata = graph.graph.nodes.get(cid, {})
            callee_infos.append(f"  - {cdata.get('name', '?')} in {cdata.get('file_path', '?')}")
        lines.append(f"Calls ({len(callees)}):")
        lines.extend(callee_infos if callee_infos else ["  (none)"])
        lines.append("")
        lines.append(f"Module: {module_name}")

        result = "\n".join(lines)
        if len(result.split()) > self.MAX_TOKENS:
            result = " ".join(result.split()[: self.MAX_TOKENS]) + "..."
        return result

    def build_impact_context(self, impact: ImpactReport) -> str:
        """Builds compact impact summary for agent consumption."""
        direct_names = [c.name for c in impact.direct_callers]
        indirect_names = [c.name for c in impact.indirect_callers]

        if impact.risk_score == "low":
            rec = "Low impact. Safe to change."
        elif impact.risk_score == "medium":
            rec = "Medium impact. Review callers before changing."
        elif impact.risk_score == "high":
            rec = "High impact. Proceed with caution and run tests."
        else:
            rec = "Critical impact. Extensive testing required."

        lines = [
            f"Impact Analysis: {impact.symbol}",
            f"Risk: {impact.risk_score} ({impact.change_surface} affected symbols)",
            "",
            f"Direct callers ({len(impact.direct_callers)}): {', '.join(direct_names[:15])}{'...' if len(direct_names) > 15 else ''}",
            f"Indirect callers ({len(impact.indirect_callers)}): {', '.join(indirect_names[:15])}{'...' if len(indirect_names) > 15 else ''}",
            f"Affected files ({len(impact.affected_files)}): {', '.join(impact.affected_files[:10])}{'...' if len(impact.affected_files) > 10 else ''}",
            f"Affected tests ({len(impact.affected_tests)}): {', '.join(impact.affected_tests[:10])}{'...' if len(impact.affected_tests) > 10 else ''}",
            "",
            f"Recommendation: {rec}",
        ]
        return "\n".join(lines)


# Legacy functions for backward compatibility
def build_context(
    graph: CodeKnowledgeGraph,
    root: Path,
    module: str,
    include_upstream: bool = True,
    include_downstream: bool = True,
    max_files: int = 20,
) -> str:
    """Build context by including file contents for module and its dependencies."""
    from app.capabilities.repo_analyzer.analysis.impact_engine import (
        get_upstream_modules,
        get_downstream_modules,
    )

    modules_to_include: set[str] = {module}
    if include_upstream:
        modules_to_include |= get_upstream_modules(graph, module)
    if include_downstream:
        modules_to_include |= get_downstream_modules(graph, module)

    mod_list = list(modules_to_include)[:max_files]
    parts = []

    for node_id, data in graph.graph.nodes(data=True):
        if data.get("type") != "file":
            continue
        if data.get("module_name") not in mod_list:
            continue
        path = data.get("relative_path") or node_id
        file_path = root / path
        if not file_path.exists():
            continue
        try:
            content = file_path.read_text(encoding="utf-8", errors="replace")
            parts.append(f"=== {path} ===\n{content}")
        except (OSError, UnicodeDecodeError):
            pass

    return "\n\n".join(parts)


def build_minimal_context(
    graph: CodeKnowledgeGraph,
    module: str,
    max_nodes: int = 50,
) -> str:
    """Build minimal context from graph structure only."""
    if "::" in module:
        return ContextBuilder().build_symbol_context(module, graph)
    data = graph.graph.nodes.get(module, {})
    if data and data.get("type") == "module":
        deps = graph.get_dependencies(module)
        dependents = graph.get_dependents(module)
        return (
            f"Module: {module}\n"
            f"Dependencies ({len(deps)}): {', '.join(sorted(deps)[:10])}\n"
            f"Dependents ({len(dependents)}): {', '.join(sorted(dependents)[:10])}"
        )
    matches = graph.find_symbol(module)
    if matches:
        return ContextBuilder().build_symbol_context(matches[0], graph)
    return f"Module/symbol '{module}' not found in graph."


def build_symbol_context_legacy(
    graph: CodeKnowledgeGraph, symbol_id: str
) -> str:
    """Legacy: build symbol context."""
    return ContextBuilder().build_symbol_context(symbol_id, graph)
