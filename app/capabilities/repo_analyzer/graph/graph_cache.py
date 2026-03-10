"""File-based cache for the code graph."""

import hashlib
import json
from pathlib import Path

from app.capabilities.repo_analyzer.graph.code_graph import CodeKnowledgeGraph
from app.capabilities.repo_analyzer.indexer.repository_indexer import IndexedFile


class GraphCache:
    """Manages loading and saving of graph cache to disk."""

    CACHE_DIR = ".agentshop_cache"
    CACHE_FILENAME = "graph.json"

    def __init__(self, repo_path: str) -> None:
        self.repo_path = Path(repo_path).resolve()
        self.cache_dir = self.repo_path / self.CACHE_DIR
        self.cache_path = self.cache_dir / self.CACHE_FILENAME

    def _ensure_cache_dir(self) -> None:
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def save(
        self,
        graph: CodeKnowledgeGraph,
        file_hashes: dict[str, str],
    ) -> None:
        """Saves graph.to_dict() and file_hashes to cache file as JSON."""
        self._ensure_cache_dir()
        data = {
            "graph": graph.to_dict(),
            "file_hashes": file_hashes,
        }
        with open(self.cache_path, "w") as f:
            json.dump(data, f, indent=0)

    def load(self) -> tuple[dict, dict] | None:
        """Returns (graph_data, file_hashes) or None if cache doesn't exist."""
        if not self.cache_path.exists():
            return None
        try:
            with open(self.cache_path) as f:
                data = json.load(f)
            graph_data = data.get("graph", {})
            file_hashes = data.get("file_hashes", {})
            return graph_data, file_hashes
        except (json.JSONDecodeError, KeyError):
            return None

    def get_file_hash(self, file_path: Path) -> str:
        """Returns MD5 hash of file content."""
        path = Path(file_path).resolve()
        if not path.exists() or not path.is_file():
            return ""
        try:
            content = path.read_bytes()
            return hashlib.md5(content).hexdigest()
        except (OSError, UnicodeDecodeError):
            return ""

    def is_stale(self, indexed_files: list[IndexedFile]) -> bool:
        """Loads cache, compares current file hashes to cached ones. Returns True if stale."""
        loaded = self.load()
        if loaded is None:
            return True
        _, cached_hashes = loaded

        current_paths = {f.relative_path for f in indexed_files}
        cached_paths = set(cached_hashes.keys())

        if current_paths != cached_paths:
            return True

        for f in indexed_files:
            current_hash = self.get_file_hash(f.path)
            if cached_hashes.get(f.relative_path) != current_hash:
                return True
        return False


def load_cached_graph(repo_path: str) -> tuple[CodeKnowledgeGraph, dict] | None:
    """Load graph and file hashes from cache. Returns (graph, file_hashes) or None."""
    cache = GraphCache(repo_path)
    result = cache.load()
    if result is None:
        return None
    graph_data, file_hashes = result
    g = CodeKnowledgeGraph()
    g.from_dict(graph_data)
    return g, file_hashes


def save_graph_cache(
    repo_path: str,
    graph: CodeKnowledgeGraph,
    file_hashes: dict[str, str],
) -> None:
    """Save graph and file hashes to cache."""
    cache = GraphCache(repo_path)
    cache.save(graph, file_hashes)
