"""Architecture summary tool: high-level project structure from graph."""

import networkx as nx

from app.capabilities.repo_analyzer.graph.code_graph import CodeKnowledgeGraph


async def get_architecture_summary(
    input_data: dict,
    graph: CodeKnowledgeGraph,
) -> dict:
    """
    Generate architecture summary from the whole graph.

    Input: {} (no required input)
    """
    g = graph.graph

    file_nodes = [n for n, d in g.nodes(data=True) if d.get("type") == "file"]
    symbol_nodes = [n for n, d in g.nodes(data=True) if d.get("type") == "symbol"]
    module_nodes = [n for n, d in g.nodes(data=True) if d.get("type") == "module"]

    # Languages from file nodes
    languages = list({
        d.get("language", "")
        for n, d in g.nodes(data=True)
        if d.get("type") == "file" and d.get("language")
    })
    languages.sort()

    # Symbol count per module
    module_symbol_count: dict[str, int] = {}
    for sid in symbol_nodes:
        data = g.nodes.get(sid, {})
        mod = data.get("module_name")
        if mod:
            module_symbol_count[mod] = module_symbol_count.get(mod, 0) + 1

    # Dependency count per module (outgoing IMPORTS)
    module_dependency_count: dict[str, int] = {}
    for n, d in g.nodes(data=True):
        if d.get("type") != "file":
            continue
        mod = d.get("module_name")
        if not mod:
            continue
        count = 0
        for _, succ in g.out_edges(n):
            ed = g.edges.get((n, succ), {})
            if ed.get("type") == graph.IMPORTS:
                count += 1
        module_dependency_count[mod] = module_dependency_count.get(mod, 0) + count

    # Top modules by symbol count and dependency count
    top_module_data = [
        {
            "name": mod,
            "symbol_count": module_symbol_count.get(mod, 0),
            "dependency_count": module_dependency_count.get(mod, 0),
        }
        for mod in module_nodes
    ]
    top_module_data.sort(
        key=lambda x: (x["symbol_count"], x["dependency_count"]),
        reverse=True,
    )
    top_modules = top_module_data[:15]

    # Most depended on (importers / dependents)
    module_dependent_count: dict[str, int] = {}
    for mod in module_nodes:
        module_dependent_count[mod] = len(graph.get_dependents(mod))
    most_depended_on = sorted(
        [{"module": m, "dependent_count": c} for m, c in module_dependent_count.items()],
        key=lambda x: x["dependent_count"],
        reverse=True,
    )[:10]

    # Most complex symbols (caller + callee count)
    symbol_complexity = []
    for sid in symbol_nodes:
        caller_count = len(graph.get_callers(sid))
        callee_count = len(graph.get_callees(sid))
        data = g.nodes.get(sid, {})
        symbol_complexity.append({
            "symbol": data.get("name", sid),
            "caller_count": caller_count,
            "callee_count": callee_count,
        })
    symbol_complexity.sort(
        key=lambda x: x["caller_count"] + x["callee_count"],
        reverse=True,
    )
    most_complex = symbol_complexity[:10]

    # Circular imports: build module-level import graph and find cycles
    # Files import modules. Map module -> modules it imports.
    mod_imports: dict[str, set[str]] = {}
    for n, d in g.nodes(data=True):
        if d.get("type") != "file":
            continue
        mod = d.get("module_name")
        if not mod:
            continue
        mod_imports.setdefault(mod, set())
        for _, succ in g.out_edges(n):
            ed = g.edges.get((n, succ), {})
            if ed.get("type") == graph.IMPORTS and g.nodes.get(succ, {}).get("type") == "module":
                mod_imports[mod].add(succ)

    cycle_graph = nx.DiGraph()
    for mod, deps in mod_imports.items():
        for dep in deps:
            cycle_graph.add_edge(mod, dep)

    try:
        cycle_edges = list(nx.find_cycle(cycle_graph))
        has_circular_imports = True
        # Format as "mod1 -> mod2 -> mod3 -> mod1"
        path = [u for u, v in cycle_edges]
        if path:
            circular_imports = [" -> ".join(path + [path[0]])]
        else:
            circular_imports = []
    except nx.NetworkXNoCycle:
        has_circular_imports = False
        circular_imports = []

    # Architecture layers: top-level prefixes
    top_levels: set[str] = set()
    for mod in module_nodes:
        if "." in mod:
            top_levels.add(mod.split(".")[0])
        else:
            top_levels.add(mod)
    architecture_layers = sorted(top_levels) if top_levels else ["(none)"]

    return {
        "total_files": len(file_nodes),
        "total_symbols": len(symbol_nodes),
        "languages": languages,
        "top_modules": top_modules,
        "most_depended_on": most_depended_on,
        "most_complex": most_complex,
        "has_circular_imports": has_circular_imports,
        "circular_imports": circular_imports,
        "architecture_layers": architecture_layers,
    }
