"""Register all v1 capabilities on startup."""

from app.capabilities.repo_analyzer.analyzer import analyze_async
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
    # repo_analyzer
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
        analyze_async,
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
