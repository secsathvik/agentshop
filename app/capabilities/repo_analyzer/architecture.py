"""Generates architecture summary and refactor suggestions from analyzed modules."""

from app.capabilities.repo_analyzer.schemas import DependencyEdge, ModuleInfo

LARGE_MODULE_LINES = 300
HIGH_FAN_OUT = 15


def _find_cycles(
    modules: list[ModuleInfo],
    edges: list[DependencyEdge],
) -> list[list[str]]:
    """Find circular dependencies using DFS."""
    module_set = {m.name for m in modules}
    graph: dict[str, list[str]] = {m.name: [] for m in modules}
    for e in edges:
        if e.from_module in module_set and e.to_module in module_set:
            graph[e.from_module].append(e.to_module)

    cycles: list[list[str]] = []
    seen_cycles: set[frozenset[str]] = set()

    def dfs(node: str, path: list[str], on_stack: set[str]) -> None:
        path.append(node)
        on_stack.add(node)
        for child in graph.get(node, []):
            if child in on_stack:
                idx = path.index(child)
                cycle = path[idx:] + [child]
                key = frozenset(cycle)
                if key not in seen_cycles and len(key) > 1:
                    seen_cycles.add(key)
                    cycles.append(cycle)
            else:
                dfs(child, path, on_stack)
        path.pop()
        on_stack.discard(node)

    for start in module_set:
        dfs(start, [], set())

    return cycles


def build_architecture_summary(
    modules: list[ModuleInfo],
    edges: list[DependencyEdge],
) -> str:
    if not modules:
        return "No Python modules found."

    total = len(modules)
    total_lines = sum(m.line_count for m in modules)
    total_funcs = sum(len(m.functions) for m in modules)
    total_classes = sum(len(m.classes) for m in modules)

    all_imports = [i for m in modules for i in m.imports]
    has_fastapi = any("fastapi" in i.lower() for i in all_imports)
    has_django = any("django" in i.lower() for i in all_imports)
    has_flask = any("flask" in i.lower() for i in all_imports)
    framework = (
        "FastAPI" if has_fastapi
        else "Django" if has_django
        else "Flask" if has_flask
        else "Python"
    )

    has_routes = any(
        "route" in m.path or "api" in m.path or "endpoint" in m.path
        for m in modules
    )
    has_db = any(
        "db" in m.path or "model" in m.path or "database" in m.path
        for m in modules
    )
    has_services = any(
        "service" in m.path or "manager" in m.path or "handler" in m.path
        for m in modules
    )
    has_tests = any("test" in m.path for m in modules)
    entry_point = next(
        (m.path for m in modules
         if m.path in ["app/main.py", "main.py", "app/app.py", "run.py"]),
        None
    )

    parts = []

    parts.append(
        f"{framework} project with {total} modules, "
        f"{total_funcs} functions, and {total_classes} classes "
        f"({total_lines} total lines)."
    )

    layers = []
    if has_routes:
        layers.append("API routes")
    if has_services:
        layers.append("service layer")
    if has_db:
        layers.append("database layer")

    if len(layers) >= 2:
        parts.append(
            f"Follows a layered architecture with "
            f"{', '.join(layers)}."
        )
    elif layers:
        parts.append(f"Contains a {layers[0]}.")

    if entry_point:
        parts.append(f"Entry point at {entry_point}.")

    if has_tests:
        test_count = sum(1 for m in modules if "test" in m.path)
        parts.append(f"Test suite present with {test_count} test file(s).")

    parts.append(
        f"{len(edges)} intra-repository dependency edges detected."
    )

    return " ".join(parts)


def build_refactor_suggestions(
    modules: list[ModuleInfo],
    edges: list[DependencyEdge],
) -> list[str]:
    """Generate refactor suggestions based on heuristics."""
    suggestions: list[str] = []

    module_set = {m.name for m in modules}
    graph: dict[str, list[str]] = {m.name: [] for m in modules}
    for e in edges:
        if e.from_module in module_set and e.to_module in module_set:
            graph[e.from_module].append(e.to_module)

    cycles = _find_cycles(modules, edges)
    for cycle in cycles[:3]:
        suggestions.append(
            f"Circular dependency: {' -> '.join(cycle)} -> {cycle[0]}"
        )

    large = [m for m in modules if m.line_count > LARGE_MODULE_LINES]
    for m in large[:3]:
        suggestions.append(
            f"Large module ({m.line_count} lines): {m.name} - consider splitting"
        )

    suggestions_added = 0
    for module in modules:
        long_fns = [
            (fn_name, count)
            for fn_name, count in module.function_line_counts.items()
            if count > 50
        ]
        if long_fns and suggestions_added < 3:
            fn_list = ", ".join(f"'{n}' ({c} lines)" for n, c in long_fns[:3])
            suggestions.append(
                f"'{module.name}' has functions exceeding 50 lines: "
                f"{fn_list} — consider splitting"
            )
            suggestions_added += 1

    for module in modules:
        if len(module.functions) >= 10:
            suggestions.append(
                f"'{module.name}' has {len(module.functions)} functions "
                f"— consider splitting into smaller modules"
            )

    fan_out = {m.name: len(graph.get(m.name, [])) for m in modules}
    high_fan = [(n, c) for n, c in fan_out.items() if c >= HIGH_FAN_OUT]
    for name, count in sorted(high_fan, key=lambda x: -x[1])[:3]:
        suggestions.append(
            f"High fan-out ({count} outgoing deps): {name} - may be doing too much"
        )

    return suggestions[:10]
