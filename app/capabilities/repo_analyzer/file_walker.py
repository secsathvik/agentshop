"""Walks the repository and collects Python files respecting limits and exclusions."""

import os
from pathlib import Path


def collect_python_files(
    repo_path: str,
    *,
    max_files: int = 500,
    include_extensions: list[str] | None = None,
    exclude_dirs: list[str] | None = None,
) -> list[tuple[str, str]]:
    """
    Collect Python files from the repository.

    Returns a list of (module_name, file_path) tuples where:
    - module_name is dot-separated (e.g. app.db.models)
    - file_path is forward-slash relative path (e.g. app/db/models.py)

    Stops after max_files to avoid excessive work.
    """
    include_extensions = include_extensions or [".py"]
    exclude_dirs = set((exclude_dirs or [])) | {
        "__pycache__", ".git", ".venv", "venv", "node_modules",
        "dist", "build", ".pytest_cache", "alembic", "scripts",
        ".mypy_cache", "migrations",
    }

    root = Path(repo_path).resolve()
    if not root.is_dir():
        return []

    results: list[tuple[str, str]] = []
    seen: set[str] = set()

    for path in root.rglob("*"):
        if len(results) >= max_files:
            break

        if not path.is_file():
            continue

        if path.suffix not in include_extensions:
            continue

        parts = path.relative_to(root).parts
        if any(part in exclude_dirs for part in parts):
            continue

        rel_path = "/".join(parts)
        if rel_path.startswith(("alembic/", "scripts/")):
            continue

        module_name = rel_path.replace("/", ".").replace("\\", ".").rsplit(".py", 1)[0]
        if module_name.endswith(".__init__"):
            module_name = module_name.rsplit(".__init__", 1)[0] or "__init__"

        if module_name in seen:
            continue
        seen.add(module_name)

        results.append((module_name, rel_path))

    return results
