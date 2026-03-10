#!/usr/bin/env python
"""Seed the capabilities table with v1 capabilities. Idempotent (upsert)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import create_engine, func
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.core.config import get_settings
from app.db.models import Capability

CAPABILITIES = [
    {
        "id": "repo_analyzer",
        "name": "Repository Analyzer",
        "description": "Analyzes repository architecture, extracts dependency graph and structure",
        "input_schema": {
            "type": "object",
            "properties": {"repo_path": {"type": "string"}, "depth": {"type": "integer"}},
            "required": ["repo_path"],
        },
        "output_schema": {
            "type": "object",
            "properties": {
                "structure": {"type": "object"},
                "dependencies": {"type": "array"},
            },
        },
        "examples": [{"repo_path": "/path/to/repo", "depth": 3}],
        "reliability": 0.9,
        "tags": ["repo", "analysis", "architecture", "dependencies"],
    },
    {
        "id": "symbol_lookup",
        "name": "Symbol Lookup",
        "description": "Look up a symbol by name. Returns definition location, callers, and callees.",
        "input_schema": {
            "type": "object",
            "properties": {
                "repo_path": {"type": "string"},
                "symbol": {"type": "string"},
                "module": {"type": "string"},
            },
            "required": ["repo_path", "symbol"],
        },
        "output_schema": {
            "type": "object",
            "properties": {
                "success": {"type": "boolean"},
                "found": {"type": "boolean"},
                "symbol": {"type": "string"},
                "file": {"type": "string"},
                "callers": {"type": "array"},
                "calls": {"type": "array"},
            },
        },
        "examples": [{"repo_path": "/path/to/repo", "symbol": "main"}],
        "reliability": 0.9,
        "tags": ["code", "symbol", "lookup", "definition"],
    },
    {
        "id": "call_graph",
        "name": "Call Graph",
        "description": "Get the call graph for a symbol up to N hops deep.",
        "input_schema": {
            "type": "object",
            "properties": {
                "repo_path": {"type": "string"},
                "symbol": {"type": "string"},
                "depth": {"type": "integer", "default": 2},
            },
            "required": ["repo_path", "symbol"],
        },
        "output_schema": {
            "type": "object",
            "properties": {
                "success": {"type": "boolean"},
                "root": {"type": "string"},
                "nodes": {"type": "array"},
                "edges": {"type": "array"},
            },
        },
        "examples": [{"repo_path": "/path/to/repo", "symbol": "main", "depth": 2}],
        "reliability": 0.9,
        "tags": ["code", "graph", "calls", "dependencies"],
    },
    {
        "id": "impact_analysis",
        "name": "Impact Analysis",
        "description": "Analyze what breaks if a symbol changes. Returns risk score and affected callers.",
        "input_schema": {
            "type": "object",
            "properties": {
                "repo_path": {"type": "string"},
                "symbol": {"type": "string"},
                "module": {"type": "string"},
            },
            "required": ["repo_path", "symbol"],
        },
        "output_schema": {
            "type": "object",
            "properties": {
                "success": {"type": "boolean"},
                "risk_score": {"type": "string"},
                "change_surface": {"type": "integer"},
                "direct_callers": {"type": "array"},
                "affected_files": {"type": "array"},
            },
        },
        "examples": [{"repo_path": "/path/to/repo", "symbol": "get_db"}],
        "reliability": 0.9,
        "tags": ["code", "impact", "safety", "refactor"],
    },
    {
        "id": "safe_rename",
        "name": "Safe Rename",
        "description": "Find all locations that need updating for a symbol rename. Read-only, no changes made.",
        "input_schema": {
            "type": "object",
            "properties": {
                "repo_path": {"type": "string"},
                "symbol": {"type": "string"},
                "new_name": {"type": "string"},
            },
            "required": ["repo_path", "symbol", "new_name"],
        },
        "output_schema": {
            "type": "object",
            "properties": {
                "success": {"type": "boolean"},
                "is_safe": {"type": "boolean"},
                "changes_required": {"type": "array"},
                "total_files_affected": {"type": "integer"},
            },
        },
        "examples": [{"repo_path": "/path/to/repo", "symbol": "get_db", "new_name": "get_session"}],
        "reliability": 0.9,
        "tags": ["code", "rename", "refactor", "safety"],
    },
    {
        "id": "security_scanner",
        "name": "Security Scanner",
        "description": "Runs static analysis to detect vulnerabilities and dependency issues",
        "input_schema": {
            "type": "object",
            "properties": {"target": {"type": "string"}, "scan_type": {"type": "string"}},
            "required": ["target"],
        },
        "output_schema": {
            "type": "object",
            "properties": {
                "vulnerabilities": {"type": "array"},
                "severity": {"type": "string"},
            },
        },
        "examples": [{"target": "src/", "scan_type": "full"}],
        "reliability": 0.85,
        "tags": ["security", "vulnerabilities", "static-analysis"],
    },
    {
        "id": "code_executor",
        "name": "Code Executor",
        "description": "Executes Python code in a sandboxed environment",
        "input_schema": {
            "type": "object",
            "properties": {"code": {"type": "string"}, "timeout_seconds": {"type": "integer"}},
            "required": ["code"],
        },
        "output_schema": {
            "type": "object",
            "properties": {"result": {}, "stdout": {"type": "string"}, "stderr": {"type": "string"}},
        },
        "examples": [{"code": "print(2 + 2)", "timeout_seconds": 5}],
        "reliability": 0.8,
        "tags": ["execution", "python", "simulation", "testing"],
    },
    {
        "id": "dependency_analyzer",
        "name": "Dependency Analyzer",
        "description": "Analyzes package.json or requirements.txt for issues",
        "input_schema": {
            "type": "object",
            "properties": {
                "file_path": {"type": "string"},
                "lock_file": {"type": "string"},
            },
            "required": ["file_path"],
        },
        "output_schema": {
            "type": "object",
            "properties": {
                "dependencies": {"type": "array"},
                "issues": {"type": "array"},
                "outdated": {"type": "array"},
            },
        },
        "examples": [{"file_path": "package.json"}, {"file_path": "requirements.txt"}],
        "reliability": 0.88,
        "tags": ["dependencies", "packages", "vulnerabilities"],
    },
    {
        "id": "doc_crawler",
        "name": "Documentation Crawler",
        "description": "Fetches and parses API documentation and usage examples",
        "input_schema": {
            "type": "object",
            "properties": {
                "url": {"type": "string"},
                "format": {"type": "string"},
            },
            "required": ["url"],
        },
        "output_schema": {
            "type": "object",
            "properties": {
                "endpoints": {"type": "array"},
                "examples": {"type": "array"},
                "content": {"type": "string"},
            },
        },
        "examples": [{"url": "https://api.example.com/docs", "format": "openapi"}],
        "reliability": 0.82,
        "tags": ["documentation", "api", "examples"],
    },
]


def main() -> int:
    settings = get_settings()
    engine = create_engine(settings.database_sync_url)

    with engine.begin() as conn:
        for cap in CAPABILITIES:
            stmt = pg_insert(Capability).values(
                id=cap["id"],
                name=cap["name"],
                description=cap["description"],
                input_schema=cap["input_schema"],
                output_schema=cap["output_schema"],
                examples=cap["examples"],
                reliability=cap["reliability"],
                tags=cap["tags"],
                is_active=True,
            ).on_conflict_do_update(
                index_elements=["id"],
                set_={
                    "name": cap["name"],
                    "description": cap["description"],
                    "input_schema": cap["input_schema"],
                    "output_schema": cap["output_schema"],
                    "examples": cap["examples"],
                    "reliability": cap["reliability"],
                    "tags": cap["tags"],
                    "is_active": True,
                    "updated_at": func.now(),
                },
            )
            conn.execute(stmt)

    print(f"Seeded {len(CAPABILITIES)} capabilities (upserted).")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
