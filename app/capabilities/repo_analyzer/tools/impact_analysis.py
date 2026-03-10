"""Impact analysis tool: compute change impact for a symbol."""

from app.capabilities.repo_analyzer.graph.code_graph import CodeKnowledgeGraph
from app.capabilities.repo_analyzer.analysis.impact_engine import ImpactAnalysisEngine


async def analyze_impact(
    input_data: dict,
    graph: CodeKnowledgeGraph,
    engine: ImpactAnalysisEngine,
) -> dict:
    """
    Analyze impact of changing a symbol. Returns ImpactReport as dict with agent-friendly formatting.

    Input: {"symbol": str, "module": str (optional)}
    """
    symbol_name = input_data.get("symbol", "")
    module_hint = input_data.get("module")

    if not symbol_name:
        return {
            "symbol": "",
            "symbol_type": "",
            "file_path": "",
            "direct_callers": [],
            "indirect_callers": [],
            "affected_modules": [],
            "affected_files": [],
            "affected_tests": [],
            "risk_score": "unknown",
            "change_surface": 0,
        }

    report = engine.analyze_impact(symbol_name, module_hint)

    def _caller_list(callers: list) -> list[dict]:
        return [
            {
                "name": c.name,
                "file": c.file_path,
                "line": c.line,
            }
            for c in callers
        ]

    return {
        "symbol": report.symbol,
        "symbol_type": report.symbol_type,
        "file_path": report.file_path,
        "direct_callers": _caller_list(report.direct_callers),
        "indirect_callers": _caller_list(report.indirect_callers),
        "affected_modules": report.affected_modules,
        "affected_files": report.affected_files,
        "affected_tests": report.affected_tests,
        "risk_score": report.risk_score,
        "change_surface": report.change_surface,
    }
