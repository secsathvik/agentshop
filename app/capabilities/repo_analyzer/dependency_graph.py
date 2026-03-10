"""Builds dependency graph and finds critical paths from module imports."""

from app.capabilities.repo_analyzer.schemas import DependencyEdge, ModuleInfo


def _import_to_type(imp: str) -> str:
    """Heuristic: single segment = import, else from_import."""
    if not imp or imp.startswith("."):
        return "from_import"
    return "import" if "." not in imp else "from_import"


def _resolve_import_to_module(imp: str, known_modules: set[str]) -> str | None:
    """
    Resolve import string to a known module. Returns the most specific match.
    E.g. 'app.schemas.capability.CapabilityInfo' -> 'app.schemas.capability'
    """
    imp = imp.lstrip(".")
    if not imp or imp not in known_modules:
        parts = imp.split(".")
        for i in range(len(parts), 0, -1):
            candidate = ".".join(parts[:i])
            if candidate in known_modules:
                return candidate
        return None
    return imp if imp in known_modules else None


def build_edges(
    modules: list[ModuleInfo],
    known_modules: set[str],
) -> list[DependencyEdge]:
    """
    Build dependency edges from module imports.
    Only includes edges where to_module is in known_modules (intra-repo deps).
    """
    edges: list[DependencyEdge] = []
    for mod in modules:
        for imp in mod.imports:
            to_mod = _resolve_import_to_module(imp, known_modules)
            if to_mod and to_mod != mod.name:
                edges.append(
                    DependencyEdge(
                        from_module=mod.name,
                        to_module=to_mod,
                        import_type=_import_to_type(imp),
                    )
                )
    seen: set[tuple[str, str]] = set()
    unique: list[DependencyEdge] = []
    for e in edges:
        key = (e.from_module, e.to_module)
        if key not in seen:
            seen.add(key)
            unique.append(e)
    return unique


def find_critical_paths(
    modules: list[ModuleInfo],
    edges: list[DependencyEdge],
    limit: int = 10,
) -> list[str]:
    """
    Find longest dependency chains (critical paths).
    Returns list of module chains, e.g. ['app -> app.db -> app.db.models'].
    """
    module_set = {m.name for m in modules}
    from_to: dict[str, list[str]] = {}
    for e in edges:
        if e.from_module in module_set and e.to_module in module_set:
            from_to.setdefault(e.from_module, []).append(e.to_module)

    def longest_path_from(node: str, visited: frozenset[str]) -> list[str]:
        if node in visited:
            return []
        visited = visited | {node}
        children = from_to.get(node, [])
        best: list[str] = [node]
        for child in children:
            cand = [node] + longest_path_from(child, visited)
            if len(cand) > len(best):
                best = cand
        return best

    all_paths: list[list[str]] = []
    for start in module_set:
        p = longest_path_from(start, frozenset())
        if len(p) > 1:
            all_paths.append(p)

    all_paths.sort(key=lambda x: (-len(x), ".".join(x)))
    return [" -> ".join(p) for p in all_paths[:limit]]
