"""Register all v1 capabilities on startup."""

from app.capabilities.repo_analyzer.analyzer import (
    handle_architecture_summary,
    handle_call_graph,
    handle_impact_analysis,
    handle_safe_rename,
    handle_symbol_lookup,
)
from app.registry.registry import CapabilityRegistry
from app.schemas.capability import CapabilityInfo


def _stub_handler(capability_id: str):
    """Create a stub handler that returns a placeholder response."""

    async def handler(_input: dict) -> dict:
        return {
            "status": "stub",
            "capability": capability_id,
            "message": "Real implementation coming soon",
        }

    return handler


def register_capabilities(registry: CapabilityRegistry) -> None:
    """Register all v1 capabilities. Call during app startup."""
    # repo_analyzer (default behavior, backwards compatible)
    registry.register(
        "repo_analyzer",
        CapabilityInfo(
            id="repo_analyzer",
            name="Repository Analyzer",
            description="Analyzes repository architecture, extracts dependency graph and structure",
            input_schema={
                "type": "object",
                "properties": {
                    "repo_path": {"type": "string"},
                    "max_files": {"type": "integer", "default": 500},
                    "include_extensions": {"type": "array", "items": {"type": "string"}},
                    "exclude_dirs": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["repo_path"],
            },
            output_schema={
                "type": "object",
                "properties": {
                    "modules": {"type": "array"},
                    "dependencies": {"type": "array"},
                    "critical_paths": {"type": "array"},
                    "architecture_summary": {"type": "string"},
                    "refactor_suggestions": {"type": "array"},
                    "stats": {"type": "object"},
                    "success": {"type": "boolean"},
                    "error": {"type": ["string", "null"]},
                },
            },
            examples=[
                {"repo_path": "/path/to/repo"},
                {"repo_path": "/path/to/repo", "max_files": 200},
            ],
            reliability=0.9,
            tags=["repo", "analysis", "architecture", "dependencies"],
        ),
        handle_architecture_summary,
    )

    # symbol_lookup
    registry.register(
        "symbol_lookup",
        CapabilityInfo(
            id="symbol_lookup",
            name="Symbol Lookup",
            description="Look up a symbol by name. Returns definition location, callers, and callees.",
            input_schema={
                "type": "object",
                "properties": {
                    "repo_path": {"type": "string"},
                    "symbol": {"type": "string"},
                    "module": {"type": "string"},
                },
                "required": ["repo_path", "symbol"],
            },
            output_schema={
                "type": "object",
                "properties": {
                    "success": {"type": "boolean"},
                    "found": {"type": "boolean"},
                    "symbol": {"type": "string"},
                    "file": {"type": "string"},
                    "callers": {"type": "array"},
                    "calls": {"type": "array"},
                    "error": {"type": ["string", "null"]},
                },
            },
            examples=[{"repo_path": "/path/to/repo", "symbol": "main"}],
            reliability=0.9,
            tags=["code", "symbol", "lookup", "definition"],
        ),
        handle_symbol_lookup,
    )

    # call_graph
    registry.register(
        "call_graph",
        CapabilityInfo(
            id="call_graph",
            name="Call Graph",
            description="Get the call graph for a symbol up to N hops deep.",
            input_schema={
                "type": "object",
                "properties": {
                    "repo_path": {"type": "string"},
                    "symbol": {"type": "string"},
                    "depth": {"type": "integer", "default": 2},
                },
                "required": ["repo_path", "symbol"],
            },
            output_schema={
                "type": "object",
                "properties": {
                    "success": {"type": "boolean"},
                    "root": {"type": "string"},
                    "nodes": {"type": "array"},
                    "edges": {"type": "array"},
                    "error": {"type": ["string", "null"]},
                },
            },
            examples=[{"repo_path": "/path/to/repo", "symbol": "main", "depth": 2}],
            reliability=0.9,
            tags=["code", "graph", "calls", "dependencies"],
        ),
        handle_call_graph,
    )

    # impact_analysis
    registry.register(
        "impact_analysis",
        CapabilityInfo(
            id="impact_analysis",
            name="Impact Analysis",
            description="Analyze what breaks if a symbol changes. Returns risk score and affected callers.",
            input_schema={
                "type": "object",
                "properties": {
                    "repo_path": {"type": "string"},
                    "symbol": {"type": "string"},
                    "module": {"type": "string"},
                },
                "required": ["repo_path", "symbol"],
            },
            output_schema={
                "type": "object",
                "properties": {
                    "success": {"type": "boolean"},
                    "risk_score": {"type": "string"},
                    "change_surface": {"type": "integer"},
                    "direct_callers": {"type": "array"},
                    "affected_files": {"type": "array"},
                    "error": {"type": ["string", "null"]},
                },
            },
            examples=[{"repo_path": "/path/to/repo", "symbol": "get_db"}],
            reliability=0.9,
            tags=["code", "impact", "safety", "refactor"],
        ),
        handle_impact_analysis,
    )

    # safe_rename
    registry.register(
        "safe_rename",
        CapabilityInfo(
            id="safe_rename",
            name="Safe Rename",
            description="Find all locations that need updating for a symbol rename. Read-only, no changes made.",
            input_schema={
                "type": "object",
                "properties": {
                    "repo_path": {"type": "string"},
                    "symbol": {"type": "string"},
                    "new_name": {"type": "string"},
                },
                "required": ["repo_path", "symbol", "new_name"],
            },
            output_schema={
                "type": "object",
                "properties": {
                    "success": {"type": "boolean"},
                    "is_safe": {"type": "boolean"},
                    "changes_required": {"type": "array"},
                    "total_files_affected": {"type": "integer"},
                    "error": {"type": ["string", "null"]},
                },
            },
            examples=[{"repo_path": "/path/to/repo", "symbol": "get_db", "new_name": "get_session"}],
            reliability=0.9,
            tags=["code", "rename", "refactor", "safety"],
        ),
        handle_safe_rename,
    )

    # security_scanner
    registry.register(
        "security_scanner",
        CapabilityInfo(
            id="security_scanner",
            name="Security Scanner",
            description="Runs static analysis to detect vulnerabilities and dependency issues",
            input_schema={
                "type": "object",
                "properties": {"target": {"type": "string"}, "scan_type": {"type": "string"}},
                "required": ["target"],
            },
            output_schema={
                "type": "object",
                "properties": {
                    "vulnerabilities": {"type": "array"},
                    "severity": {"type": "string"},
                },
            },
            examples=[{"target": "src/", "scan_type": "full"}],
            reliability=0.85,
            tags=["security", "vulnerabilities", "static-analysis"],
        ),
        _stub_handler("security_scanner"),
    )

    # code_executor
    registry.register(
        "code_executor",
        CapabilityInfo(
            id="code_executor",
            name="Code Executor",
            description="Executes Python code in a sandboxed environment",
            input_schema={
                "type": "object",
                "properties": {"code": {"type": "string"}, "timeout_seconds": {"type": "integer"}},
                "required": ["code"],
            },
            output_schema={
                "type": "object",
                "properties": {"result": {}, "stdout": {"type": "string"}, "stderr": {"type": "string"}},
            },
            examples=[{"code": "print(2 + 2)", "timeout_seconds": 5}],
            reliability=0.8,
            tags=["execution", "python", "simulation", "testing"],
        ),
        _stub_handler("code_executor"),
    )

    # dependency_analyzer
    registry.register(
        "dependency_analyzer",
        CapabilityInfo(
            id="dependency_analyzer",
            name="Dependency Analyzer",
            description="Analyzes package.json or requirements.txt for issues",
            input_schema={
                "type": "object",
                "properties": {
                    "file_path": {"type": "string"},
                    "lock_file": {"type": "string"},
                },
                "required": ["file_path"],
            },
            output_schema={
                "type": "object",
                "properties": {
                    "dependencies": {"type": "array"},
                    "issues": {"type": "array"},
                    "outdated": {"type": "array"},
                },
            },
            examples=[{"file_path": "package.json"}, {"file_path": "requirements.txt"}],
            reliability=0.88,
            tags=["dependencies", "packages", "vulnerabilities"],
        ),
        _stub_handler("dependency_analyzer"),
    )

    # doc_crawler
    registry.register(
        "doc_crawler",
        CapabilityInfo(
            id="doc_crawler",
            name="Documentation Crawler",
            description="Fetches and parses API documentation and usage examples",
            input_schema={
                "type": "object",
                "properties": {
                    "url": {"type": "string"},
                    "format": {"type": "string"},
                },
                "required": ["url"],
            },
            output_schema={
                "type": "object",
                "properties": {
                    "endpoints": {"type": "array"},
                    "examples": {"type": "array"},
                    "content": {"type": "string"},
                },
            },
            examples=[{"url": "https://api.example.com/docs", "format": "openapi"}],
            reliability=0.82,
            tags=["documentation", "api", "examples"],
        ),
        _stub_handler("doc_crawler"),
    )
