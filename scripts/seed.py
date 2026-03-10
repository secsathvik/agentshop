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
