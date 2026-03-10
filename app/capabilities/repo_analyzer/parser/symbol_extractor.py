"""Extracts symbols (functions, classes, imports) from tree-sitter syntax trees."""

from dataclasses import dataclass
from typing import TYPE_CHECKING

import tree_sitter

if TYPE_CHECKING:
    from app.capabilities.repo_analyzer.parser.treesitter_parser import ParsedFile


@dataclass
class Symbol:
    """A symbol extracted from source (function, class, method, import, call)."""

    name: str
    symbol_type: str  # "function", "class", "method", "import", "call"
    file_path: str
    module_name: str
    start_line: int
    end_line: int
    parent: str | None  # for methods: the class name
    calls: list[str]
    docstring: str | None


class SymbolExtractor:
    """Extracts symbols from parsed files using tree-sitter queries."""

    def __init__(self, language_registry=None) -> None:
        self._language_registry = language_registry

    def extract(self, parsed_file: "ParsedFile") -> list[Symbol]:
        """Extract symbols from a parsed file."""
        idx = parsed_file.indexed_file
        tree = parsed_file.tree
        content = parsed_file.content
        file_path = idx.relative_path
        module_name = idx.module_name
        language = idx.language

        if not tree or not tree.root_node:
            return []

        symbols: list[Symbol] = []

        if language == "python":
            self._extract_python(tree.root_node, content, file_path, module_name, symbols)
        elif language in ("javascript", "typescript"):
            self._extract_javascript(tree.root_node, content, file_path, module_name, symbols)

        return symbols

    def _get_text(self, content: bytes, node: tree_sitter.Node) -> str:
        return content[node.start_byte : node.end_byte].decode("utf-8", errors="replace")

    def _extract_depends_injections(
        self,
        func_node: tree_sitter.Node,
        content: bytes,
        depends_default_query: object,
        depends_keyword_query: object,
    ) -> list[str]:
        """Extract FastAPI Depends(get_db) injected names from function parameters."""
        injected: list[str] = []
        for query in (depends_default_query, depends_keyword_query):
            caps = query.captures(func_node)
            dep_funcs = caps.get("dep_func", [])
            injected_names = caps.get("injected_name", [])
            for dep_n, inj_n in zip(dep_funcs, injected_names):
                if self._get_text(content, dep_n) == "Depends":
                    injected.append(self._get_text(content, inj_n))
        return injected

    def _get_parent_class(self, node: tree_sitter.Node, content: bytes) -> str | None:
        """Walk parent chain to find enclosing class_definition. Return class name or None."""
        current = node.parent
        while current:
            if current.type == "class_definition":
                name_node = current.child_by_field_name("name")
                if name_node:
                    return self._get_text(content, name_node)
            current = current.parent
        return None

    def _extract_python(
        self,
        root: tree_sitter.Node,
        content: bytes,
        file_path: str,
        module_name: str,
        symbols: list[Symbol],
    ) -> None:
        """Extract symbols from Python using tree-sitter queries."""
        try:
            from tree_sitter import Language, Query

            import tree_sitter_python as tsp
            language = Language(tsp.language())

            # FIX 2: Query finds ALL function_definitions anywhere (including inside decorated_definition)
            functions_query = Query(
                language,
                "(function_definition name: (identifier) @func_name)",
            )
            classes_query = Query(
                language,
                "(class_definition name: (identifier) @class_name)",
            )
            # FIX 3: Import queries
            import_stmt_query = Query(
                language,
                "(import_statement (dotted_name) @mod)",
            )
            import_from_query = Query(
                language,
                "(import_from_statement module_name: (dotted_name) @mod)",
            )
            # FIX 4: Call extraction per function
            calls_query = Query(
                language,
                """
                (call function: [
                    (identifier) @call_name
                    (attribute attribute: (identifier) @call_name)
                ])
                """,
            )
            # FastAPI Depends() injection: def route(db=Depends(get_db)) or db: Session = Depends(get_db)
            depends_default_query = Query(
                language,
                """
                [
                    (default_parameter
                        value: (call
                            function: (identifier) @dep_func
                            arguments: (argument_list (identifier) @injected_name)))
                    (typed_default_parameter
                        value: (call
                            function: (identifier) @dep_func
                            arguments: (argument_list (identifier) @injected_name)))
                ]
                """,
            )
            depends_keyword_query = Query(
                language,
                """
                (keyword_argument
                    value: (call
                        function: (identifier) @dep_func
                        arguments: (argument_list (identifier) @injected_name)))
                """,
            )

            # FIX 1: captures() returns dict {"capture_name": [Node, ...]}
            class_name_nodes = classes_query.captures(root).get("class_name", [])
            for name_node in class_name_nodes:
                cls_node = self._get_ancestor_of_capture(name_node, root, "class_definition")
                if cls_node:
                    cls_name = self._get_text(content, name_node)
                    symbols.append(
                        Symbol(
                            name=cls_name,
                            symbol_type="class",
                            file_path=file_path,
                            module_name=module_name,
                            start_line=cls_node.start_point[0] + 1,
                            end_line=cls_node.end_point[0] + 1,
                            parent=None,
                            calls=[],
                            docstring=self._get_docstring(content, cls_node),
                        )
                    )

            func_name_nodes = functions_query.captures(root).get("func_name", [])
            for name_node in func_name_nodes:
                func_node = self._get_ancestor_of_capture(name_node, root, "function_definition")
                if not func_node:
                    continue
                fn_name = self._get_text(content, name_node)
                # FIX 5: Parent class via node.parent walk
                parent_class = self._get_parent_class(func_node, content)
                sym_type = "method" if parent_class else "function"
                # FIX 4: Call extraction scoped to func_node
                call_captures = calls_query.captures(func_node)
                call_names = [
                    self._get_text(content, n)
                    for n in call_captures.get("call_name", [])
                ]
                # FastAPI Depends() injection pass
                call_names.extend(
                    self._extract_depends_injections(
                        func_node, content, depends_default_query, depends_keyword_query
                    )
                )
                call_names = list(dict.fromkeys(call_names))
                symbols.append(
                    Symbol(
                        name=fn_name,
                        symbol_type=sym_type,
                        file_path=file_path,
                        module_name=module_name,
                        start_line=func_node.start_point[0] + 1,
                        end_line=func_node.end_point[0] + 1,
                        parent=parent_class,
                        calls=call_names,
                        docstring=self._get_docstring(content, func_node),
                    )
                )

            # FIX 3: Import extraction - dict format, @mod capture
            for mod_node in import_stmt_query.captures(root).get("mod", []):
                mod_name = self._get_text(content, mod_node)
                if mod_name:
                    import_node = self._get_ancestor_of_capture(mod_node, root, "import_statement")
                    if import_node:
                        symbols.append(
                            Symbol(
                                name=mod_name,
                                symbol_type="import",
                                file_path=file_path,
                                module_name=module_name,
                                start_line=import_node.start_point[0] + 1,
                                end_line=import_node.end_point[0] + 1,
                                parent=None,
                                calls=[],
                                docstring=None,
                            )
                        )

            for mod_node in import_from_query.captures(root).get("mod", []):
                mod_name = self._get_text(content, mod_node)
                if mod_name:
                    import_node = self._get_ancestor_of_capture(
                        mod_node, root, "import_from_statement"
                    )
                    if import_node:
                        symbols.append(
                            Symbol(
                                name=mod_name,
                                symbol_type="import",
                                file_path=file_path,
                                module_name=module_name,
                                start_line=import_node.start_point[0] + 1,
                                end_line=import_node.end_point[0] + 1,
                                parent=None,
                                calls=[],
                                docstring=None,
                            )
                        )

        except Exception:
            self._extract_python_simple(root, content, file_path, module_name, symbols)

    def _get_ancestor_of_capture(
        self, capture_node: tree_sitter.Node, root: tree_sitter.Node, node_type: str
    ) -> tree_sitter.Node | None:
        """Find innermost node of node_type that contains capture_node."""
        cap_start, cap_end = capture_node.start_byte, capture_node.end_byte

        def find(node: tree_sitter.Node) -> tree_sitter.Node | None:
            if not (node.start_byte <= cap_start and cap_end <= node.end_byte):
                return None
            for child in node.children:
                found = find(child)
                if found:
                    return found
            return node if node.type == node_type else None

        return find(root)

    def _extract_python_simple(
        self,
        node: tree_sitter.Node,
        content: bytes,
        file_path: str,
        module_name: str,
        symbols: list[Symbol],
    ) -> None:
        """Fallback extraction without queries."""
        if node.type == "function_definition":
            name_node = node.child_by_field_name("name")
            if name_node:
                name = self._get_text(content, name_node)
                symbols.append(
                    Symbol(
                        name=name,
                        symbol_type="function",
                        file_path=file_path,
                        module_name=module_name,
                        start_line=node.start_point[0] + 1,
                        end_line=node.end_point[0] + 1,
                        parent=None,
                        calls=[],
                        docstring=None,
                    )
                )
        elif node.type == "class_definition":
            name_node = node.child_by_field_name("name")
            if name_node:
                name = self._get_text(content, name_node)
                symbols.append(
                    Symbol(
                        name=name,
                        symbol_type="class",
                        file_path=file_path,
                        module_name=module_name,
                        start_line=node.start_point[0] + 1,
                        end_line=node.end_point[0] + 1,
                        parent=None,
                        calls=[],
                        docstring=None,
                    )
                )
        elif node.type in ("import_statement", "import_from_statement"):
            imp_text = self._get_text(content, node).strip()
            symbols.append(
                Symbol(
                    name=imp_text,
                    symbol_type="import",
                    file_path=file_path,
                    module_name=module_name,
                    start_line=node.start_point[0] + 1,
                    end_line=node.end_point[0] + 1,
                    parent=None,
                    calls=[],
                    docstring=None,
                )
            )

        for child in node.children:
            self._extract_python_simple(child, content, file_path, module_name, symbols)

    def _get_docstring(self, content: bytes, node: tree_sitter.Node) -> str | None:
        """Extract first string node in function/class body as docstring."""
        body = node.child_by_field_name("body")
        if not body or body.child_count == 0:
            return None
        first = body.child(0)
        if first and first.type == "expression_statement":
            expr = first.child(0)
            if expr and expr.type == "string":
                return self._get_text(content, expr).strip().strip('"\'')
        return None

    def _extract_javascript(
        self,
        root: tree_sitter.Node,
        content: bytes,
        file_path: str,
        module_name: str,
        symbols: list[Symbol],
    ) -> None:
        """Extract symbols from JavaScript/TypeScript."""

        def visit(node: tree_sitter.Node) -> None:
            if node.type == "function_declaration":
                name_node = node.child_by_field_name("name")
                if name_node:
                    name = self._get_text(content, name_node)
                    symbols.append(
                        Symbol(
                            name=name,
                            symbol_type="function",
                            file_path=file_path,
                            module_name=module_name,
                            start_line=node.start_point[0] + 1,
                            end_line=node.end_point[0] + 1,
                            parent=None,
                            calls=[],
                            docstring=None,
                        )
                    )
            elif node.type == "method_definition":
                name_node = node.child_by_field_name("name")
                if name_node:
                    name = self._get_text(content, name_node)
                    symbols.append(
                        Symbol(
                            name=name,
                            symbol_type="method",
                            file_path=file_path,
                            module_name=module_name,
                            start_line=node.start_point[0] + 1,
                            end_line=node.end_point[0] + 1,
                            parent=None,
                            calls=[],
                            docstring=None,
                        )
                    )
            elif node.type == "class_declaration":
                name_node = node.child_by_field_name("name")
                if name_node:
                    name = self._get_text(content, name_node)
                    symbols.append(
                        Symbol(
                            name=name,
                            symbol_type="class",
                            file_path=file_path,
                            module_name=module_name,
                            start_line=node.start_point[0] + 1,
                            end_line=node.end_point[0] + 1,
                            parent=None,
                            calls=[],
                            docstring=None,
                        )
                    )
            elif node.type in ("import_statement", "import_declaration"):
                imp_text = self._get_text(content, node).strip()
                symbols.append(
                    Symbol(
                        name=imp_text,
                        symbol_type="import",
                        file_path=file_path,
                        module_name=module_name,
                        start_line=node.start_point[0] + 1,
                        end_line=node.end_point[0] + 1,
                        parent=None,
                        calls=[],
                        docstring=None,
                    )
                )

            for child in node.children:
                visit(child)

        visit(root)

    def extract_all(self, parsed_files: list["ParsedFile"]) -> dict[str, list[Symbol]]:
        """Extract symbols from all parsed files. Returns dict mapping module_name -> list[Symbol]."""
        result: dict[str, list[Symbol]] = {}
        for pf in parsed_files:
            syms = self.extract(pf)
            module_name = pf.indexed_file.module_name
            result[module_name] = syms
        return result
