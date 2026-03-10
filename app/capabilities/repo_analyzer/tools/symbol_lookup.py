"""Symbol lookup tool: find where a symbol is defined and its relationships."""

from app.capabilities.repo_analyzer.graph.code_graph import CodeKnowledgeGraph


async def symbol_lookup(input_data: dict, graph: CodeKnowledgeGraph) -> dict:
    """
    Look up a symbol in the graph.

    Input: {"symbol": str, "module": str (optional)}
    Returns symbol location, callers, calls, and docstring.
    """
    symbol_name = input_data.get("symbol", "")
    module_hint = input_data.get("module")

    if not symbol_name:
        return {
            "found": False,
            "symbol": "",
            "type": "",
            "file": "",
            "start_line": 0,
            "end_line": 0,
            "callers": [],
            "calls": [],
            "docstring": None,
        }

    matches = graph.find_symbol(symbol_name, module_hint)
    if not matches:
        return {
            "found": False,
            "symbol": symbol_name,
            "type": "",
            "file": "",
            "start_line": 0,
            "end_line": 0,
            "callers": [],
            "calls": [],
            "docstring": None,
        }

    symbol_id = matches[0]
    data = graph.graph.nodes.get(symbol_id, {})

    # Build callers list: {name, file, line}
    callers = []
    for caller_id in graph.get_callers(symbol_id):
        caller_data = graph.graph.nodes.get(caller_id, {})
        callers.append({
            "name": caller_data.get("name", ""),
            "file": caller_data.get("file_path", ""),
            "line": caller_data.get("start_line", 0),
        })

    # Build calls list: {name, file}
    calls = []
    for callee_id in graph.get_callees(symbol_id):
        callee_data = graph.graph.nodes.get(callee_id, {})
        calls.append({
            "name": callee_data.get("name", ""),
            "file": callee_data.get("file_path", ""),
        })

    return {
        "found": True,
        "symbol": data.get("name", symbol_name),
        "type": data.get("symbol_type", ""),
        "file": data.get("file_path", ""),
        "start_line": data.get("start_line", 0),
        "end_line": data.get("end_line", 0),
        "callers": callers,
        "calls": calls,
        "docstring": graph.graph.nodes.get(symbol_id, {}).get("docstring"),
    }
