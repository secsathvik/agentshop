"""Pydantic schemas for the repository analyzer capability."""

from pydantic import BaseModel, ConfigDict, model_serializer


class RepoAnalyzerInput(BaseModel):
    """
    Input parameters for the repository analyzer capability.
    Specifies the repository path, file limits, and which paths to include/exclude.
    """

    model_config = ConfigDict(from_attributes=True)

    repo_path: str
    max_files: int = 500
    include_extensions: list[str] = [".py"]
    exclude_dirs: list[str] = [
        "__pycache__",
        ".venv",
        "venv",
        "node_modules",
        ".git",
        ".mypy_cache",
        "dist",
        "build",
        ".pytest_cache",
        "migrations",
    ]


class ModuleInfo(BaseModel):
    """
    Metadata for a single Python module parsed from the repository.
    Contains structural information: functions, classes, imports, and line counts.
    """

    model_config = ConfigDict(from_attributes=True)

    name: str  # dot-separated e.g. app.db.models
    path: str  # forward-slash relative e.g. app/db/models.py
    functions: list[str]
    classes: list[str]
    imports: list[str]
    line_count: int
    function_line_counts: dict[str, int]
    has_syntax_error: bool = False


class DependencyEdge(BaseModel):
    """
    Represents a dependency from one module to another.
    Serializes to 'from' and 'to' in JSON (Python keywords cannot be field names).
    """

    model_config = ConfigDict(from_attributes=True)

    from_module: str
    to_module: str
    import_type: str  # "import" or "from_import"

    @model_serializer(mode="plain")
    def _serialize(self) -> dict:
        return {
            "from": self.from_module,
            "to": self.to_module,
            "import_type": self.import_type,
        }


class RepoAnalyzerOutput(BaseModel):
    """
    Output from the repository analyzer including modules, dependencies,
    critical paths, architecture summary, refactor suggestions, and stats.
    """

    model_config = ConfigDict(from_attributes=True)

    modules: list[ModuleInfo]
    dependencies: list[DependencyEdge]
    critical_paths: list[str]
    architecture_summary: str
    refactor_suggestions: list[str]
    stats: dict
    success: bool
    error: str | None = None
