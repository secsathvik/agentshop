"""File discovery and language detection for repository indexing."""

from dataclasses import dataclass
from pathlib import Path

from app.capabilities.repo_analyzer.indexer.language_registry import LanguageRegistry

MAX_FILE_BYTES = 500 * 1024  # 500KB


@dataclass
class IndexedFile:
    """A discovered file with its path and metadata."""

    path: Path
    relative_path: str
    extension: str
    language: str
    size_bytes: int
    module_name: str


DEFAULT_CONFIG = {
    "max_files": 1000,
    "exclude_dirs": [
        "__pycache__",
        ".git",
        ".venv",
        "venv",
        "node_modules",
        "dist",
        "build",
        ".pytest_cache",
        "migrations",
        "alembic",
        "scripts",
        ".mypy_cache",
    ],
    "include_extensions": [".py", ".js", ".ts", ".tsx", ".jsx"],
}


class RepositoryIndexer:
    """Discovers and indexes source files in a repository."""

    def __init__(self, repo_path: str, config: dict | None = None) -> None:
        self.root = Path(repo_path).resolve()
        if not self.root.exists():
            raise ValueError(f"Path does not exist: {repo_path}")
        if not self.root.is_dir():
            raise ValueError(f"Path is not a directory: {repo_path}")

        cfg = config or {}
        self.max_files = cfg.get("max_files", DEFAULT_CONFIG["max_files"])
        self.exclude_dirs = set(cfg.get("exclude_dirs", DEFAULT_CONFIG["exclude_dirs"]))
        self.include_extensions = set(
            cfg.get("include_extensions", DEFAULT_CONFIG["include_extensions"])
        )
        self.language_registry = LanguageRegistry()

    def discover_files(self) -> list[IndexedFile]:
        """
        Discover source files in the repository.
        Returns sorted list of IndexedFile.
        """
        results: list[IndexedFile] = []

        for path in self.root.rglob("*"):
            if len(results) >= self.max_files:
                break

            if not path.is_file():
                continue

            ext = path.suffix
            if ext not in self.include_extensions:
                continue
            if not self.language_registry.is_supported(ext):
                continue

            parts = path.relative_to(self.root).parts
            if any(part in self.exclude_dirs for part in parts):
                continue

            relative_path = "/".join(parts)
            if relative_path.startswith(("alembic/", "scripts/")):
                continue

            try:
                size_bytes = path.stat().st_size
            except OSError:
                continue
            if size_bytes > MAX_FILE_BYTES:
                continue

            lang_info = self.language_registry.get_language(ext)
            if not lang_info:
                continue
            language = lang_info["name"]

            # module_name: dot-separated, for Python __init__.py use package name
            module_name = relative_path.replace("/", ".").replace("\\", ".").rsplit(
                ext, 1
            )[0]
            if module_name.endswith(".__init__"):
                module_name = module_name.rsplit(".__init__", 1)[0] or "__init__"

            results.append(
                IndexedFile(
                    path=path,
                    relative_path=relative_path,
                    extension=ext,
                    language=language,
                    size_bytes=size_bytes,
                    module_name=module_name,
                )
            )

        return sorted(results, key=lambda f: f.relative_path)

    def get_stats(self) -> dict:
        """Return summary of discovered files by language."""
        files = self.discover_files()
        stats: dict[str, int] = {}
        for f in files:
            stats[f.language] = stats.get(f.language, 0) + 1
        return {
            "total_files": len(files),
            "by_language": dict(sorted(stats.items())),
        }


if __name__ == "__main__":
    import sys

    path = sys.argv[1] if len(sys.argv) > 1 else "."
    try:
        indexer = RepositoryIndexer(path)
        stats = indexer.get_stats()
        print(f"Indexed {stats['total_files']} files")
        for lang, count in stats["by_language"].items():
            print(f"  {lang}: {count}")
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)
