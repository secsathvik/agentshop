"""Main orchestrator for repository analysis."""

from pathlib import Path

from app.capabilities.repo_analyzer.architecture import (
    build_architecture_summary,
    build_refactor_suggestions,
)
from app.capabilities.repo_analyzer.dependency_graph import (
    build_edges,
    find_critical_paths,
)
from app.capabilities.repo_analyzer.file_walker import collect_python_files
from app.capabilities.repo_analyzer.schemas import (
    RepoAnalyzerInput,
    RepoAnalyzerOutput,
)
from app.capabilities.repo_analyzer.ast_parser import parse_file


def analyze(input_data: dict) -> RepoAnalyzerOutput:
    """
    Run full repository analysis. Accepts dict (e.g. from API) and returns
    RepoAnalyzerOutput. Sets success=False and error on failure.
    """
    try:
        params = RepoAnalyzerInput.model_validate(input_data)
    except Exception as e:
        return RepoAnalyzerOutput(
            modules=[],
            dependencies=[],
            critical_paths=[],
            architecture_summary="",
            refactor_suggestions=[],
            stats={},
            success=False,
            error=str(e),
        )

    repo_path = params.repo_path
    root = Path(repo_path).resolve()

    if not root.is_dir():
        return RepoAnalyzerOutput(
            modules=[],
            dependencies=[],
            critical_paths=[],
            architecture_summary="",
            refactor_suggestions=[],
            stats={
                "total_files": 0,
                "total_lines": 0,
                "total_functions": 0,
                "total_classes": 0,
                "avg_functions_per_module": 0.0,
                "avg_complexity": 0.0,
                "parse_errors": 0,
                "largest_module": "",
                "languages": ["python"],
            },
            success=False,
            error=f"Repository path does not exist or is not a directory: {repo_path}",
        )

    files = collect_python_files(
        repo_path,
        max_files=params.max_files,
        include_extensions=params.include_extensions,
        exclude_dirs=params.exclude_dirs,
    )

    modules: list = []
    for module_name, rel_path in files:
        mod = parse_file(root, module_name, rel_path)
        modules.append(mod)

    modules = [
        m for m in modules
        if not (
            len(m.functions) == 0
            and len(m.classes) == 0
            and len(m.imports) == 0
        )
    ]

    known = {m.name for m in modules}
    edges = build_edges(modules, known)
    critical_paths = find_critical_paths(modules, edges, limit=10)
    architecture_summary = build_architecture_summary(modules, edges)
    refactor_suggestions = build_refactor_suggestions(modules, edges)

    total_lines = sum(m.line_count for m in modules)
    total_funcs = sum(len(m.functions) for m in modules)
    total_classes = sum(len(m.classes) for m in modules)
    parse_errors = sum(1 for m in modules if m.has_syntax_error)
    largest = max(modules, key=lambda m: m.line_count) if modules else None

    stats = {
        "total_files": len(modules),
        "total_lines": total_lines,
        "total_functions": total_funcs,
        "total_classes": total_classes,
        "avg_functions_per_module": total_funcs / len(modules) if modules else 0.0,
        "avg_complexity": 0.0,
        "parse_errors": parse_errors,
        "largest_module": largest.name if largest else "",
        "languages": ["python"],
    }

    return RepoAnalyzerOutput(
        modules=modules,
        dependencies=edges,
        critical_paths=critical_paths,
        architecture_summary=architecture_summary,
        refactor_suggestions=refactor_suggestions,
        stats=stats,
        success=True,
        error=None,
    )


async def analyze_async(input_data: dict) -> dict:
    """
    Async entry point for the capability handler. Runs analyze() and returns
    the result as a dict (for API JSON response).
    """
    result = analyze(input_data)
    return result.model_dump(mode="json")
 
if __name__ == "__main__": 
    import asyncio, json, sys 
    path = sys.argv[1] if len(sys.argv) > 1 else "." 
    result = asyncio.run(analyze_async({"repo_path": path})) 
    print(json.dumps(result, indent=2, default=str)) 
 
if __name__ == "__main__": 
    import asyncio, json, sys 
    path = sys.argv[1] if len(sys.argv) > 1 else "." 
    result = asyncio.run(analyze_async({"repo_path": path})) 
    print(json.dumps(result, indent=2, default=str)) 
