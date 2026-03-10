"""Safe rename tool: preview changes for a symbol rename (READ-ONLY, no file modifications)."""

import re
from pathlib import Path

from app.capabilities.repo_analyzer.graph.code_graph import CodeKnowledgeGraph
from app.capabilities.repo_analyzer.analysis.impact_engine import ImpactAnalysisEngine


async def safe_rename(
    input_data: dict,
    graph: CodeKnowledgeGraph,
    engine: ImpactAnalysisEngine,
) -> dict:
    """
    Preview what would need to change for a symbol rename. READ-ONLY - makes NO file modifications.

    Input: {"symbol": str, "new_name": str}
    """
    symbol_name = input_data.get("symbol", "")
    new_name = input_data.get("new_name", "")

    if not symbol_name or not new_name:
        return {
            "symbol": symbol_name,
            "new_name": new_name,
            "is_safe": False,
            "warnings": ["Missing symbol or new_name"],
            "changes_required": [],
            "total_files_affected": 0,
            "estimated_risk": "unknown",
        }

    report = engine.find_safe_rename_targets(symbol_name)
    repo_path = Path(engine.repo_path) if engine.repo_path else Path.cwd()

    changes_required = []
    for occ in report.occurrences:
        fp = occ.get("file_path", "")
        line = occ.get("line", 0)
        context = occ.get("context_line", "")
        if not context:
            # Fallback: try to read the file
            try:
                full = (repo_path / fp).resolve()
                if full.exists():
                    lines = full.read_text(encoding="utf-8", errors="replace").splitlines()
                    if 1 <= line <= len(lines):
                        context = lines[line - 1]
            except (OSError, UnicodeDecodeError):
                pass
        # Suggest replacement: simple word-boundary replace of symbol_name with new_name
        suggested = re.sub(
            r"\b" + re.escape(symbol_name) + r"\b",
            new_name,
            context,
            count=1,
        )
        changes_required.append({
            "file": fp,
            "line": line,
            "current_text": context,
            "suggested_text": suggested,
        })

    # Estimated risk from change surface
    impact = engine.analyze_impact(symbol_name)
    risk = impact.risk_score
    if risk == "unknown":
        risk = "low" if report.total_files <= 1 else "medium"

    return {
        "symbol": symbol_name,
        "new_name": new_name,
        "is_safe": report.is_safe,
        "warnings": report.warnings,
        "changes_required": changes_required,
        "total_files_affected": report.total_files,
        "estimated_risk": risk,
    }
