"""Parses Python files using AST to extract module metadata."""

import ast
import os
from pathlib import Path

from app.capabilities.repo_analyzer.schemas import ModuleInfo


def _resolve_import(module_name: str, level: int, current_module: str) -> str:
    """Resolve a relative import to an absolute module name."""
    if level == 0:
        return module_name
    parts = current_module.split(".")[: -level]
    base = ".".join(parts) if parts else ""
    if module_name:
        return f"{base}.{module_name}" if base else module_name
    return base


def parse_module(
    file_path: str,
    content: str,
    module_name: str,
) -> ModuleInfo:
    """
    Parse a Python file and extract ModuleInfo.
    Returns ModuleInfo with has_syntax_error=True if parsing fails.
    """
    path_slash = file_path.replace("\\", "/")
    functions: list[str] = []
    classes: list[str] = []
    imports: list[str] = []
    function_line_counts: dict[str, int] = {}

    try:
        tree = ast.parse(content)
    except SyntaxError:
        lines = content.count("\n") + 1 if content else 0
        return ModuleInfo(
            name=module_name,
            path=path_slash,
            functions=[],
            classes=[],
            imports=[],
            line_count=lines,
            function_line_counts={},
            has_syntax_error=True,
        )

    line_count = content.count("\n") + 1 if content else 0

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                resolved = _resolve_import(
                    node.module, node.level or 0, module_name
                )
                for alias in node.names:
                    if alias.name == "*":
                        imports.append(resolved)
                    else:
                        imports.append(f"{resolved}.{alias.name}")
            else:
                resolved = _resolve_import("", node.level or 0, module_name)
                for alias in node.names:
                    imports.append(f"{resolved}.{alias.name}")

    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            functions.append(node.name)
            end = getattr(node, "end_lineno", node.lineno) or node.lineno
            function_line_counts[node.name] = end - node.lineno + 1
        elif isinstance(node, ast.ClassDef):
            classes.append(node.name)
            for inner in ast.walk(node):
                if isinstance(inner, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    end = (
                        getattr(inner, "end_lineno", inner.lineno) or inner.lineno
                    )
                    function_line_counts[inner.name] = end - inner.lineno + 1

    return ModuleInfo(
        name=module_name,
        path=path_slash,
        functions=functions,
        classes=classes,
        imports=imports,
        line_count=line_count,
        function_line_counts=function_line_counts,
        has_syntax_error=False,
    )


def parse_file(
    repo_root: Path,
    module_name: str,
    rel_path: str,
) -> ModuleInfo:
    """
    Read a file from disk and parse it.
    Returns ModuleInfo with has_syntax_error=True on read or parse failure.
    """
    full_path = repo_root / rel_path.replace("/", os.sep)
    try:
        content = full_path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return ModuleInfo(
            name=module_name,
            path=rel_path.replace("\\", "/"),
            functions=[],
            classes=[],
            imports=[],
            line_count=0,
            function_line_counts={},
            has_syntax_error=True,
        )
    return parse_module(rel_path.replace("\\", "/"), content, module_name)


def parse_file_from_path(repo_path: str, module_name: str, rel_path: str) -> ModuleInfo:
    """Convenience wrapper: parse a file given repo root path as string."""
    return parse_file(Path(repo_path), module_name, rel_path)
