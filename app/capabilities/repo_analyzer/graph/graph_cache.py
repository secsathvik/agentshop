"""File-based cache for the code graph."""

import json
from pathlib import Path

import networkx as nx

from app.capabilities.repo_analyzer.graph.code_graph import CodeGraph


class GraphCache:
    """Manages loading and saving of graph cache to disk."""

    def __init__(self, cache_dir: Path | str = ".cache/repo_graph"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _cache_path(self, repo_key: str) -> Path:
        return self.cache_dir / f"{repo_key}.json"

    def save(self, repo_key: str, graph: CodeGraph) -> None:
        """Save graph to cache directory."""
        path = self._cache_path(repo_key)
        data = graph.to_dict()
        with open(path, "w") as f:
            json.dump(data, f, indent=0)

    def load(self, repo_key: str) -> CodeGraph | None:
        """Load graph from cache if it exists."""
        path = self._cache_path(repo_key)
        if not path.exists():
            return None
        try:
            with open(path) as f:
                data = json.load(f)
            g = nx.node_link_graph(data)
            cg = CodeGraph()
            cg._graph = g
            return cg
        except (json.JSONDecodeError, KeyError):
            return None


def load_cached_graph(cache_dir: str, repo_key: str) -> CodeGraph | None:
    """Convenience: load graph from cache."""
    return GraphCache(cache_dir).load(repo_key)


def save_graph_cache(cache_dir: str, repo_key: str, graph: CodeGraph) -> None:
    """Convenience: save graph to cache."""
    GraphCache(cache_dir).save(repo_key, graph)
