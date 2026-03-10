"""Maps file extensions to tree-sitter language grammars."""

import importlib
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import tree_sitter

SUPPORTED_LANGUAGES: dict[str, dict[str, str]] = {
    ".py": {"name": "python", "grammar": "tree_sitter_python"},
    ".js": {"name": "javascript", "grammar": "tree_sitter_javascript"},
    ".ts": {"name": "typescript", "grammar": "tree_sitter_typescript"},
    ".tsx": {"name": "typescript", "grammar": "tree_sitter_typescript"},
    ".jsx": {"name": "javascript", "grammar": "tree_sitter_javascript"},
}


class LanguageRegistry:
    """Registry of supported languages and their tree-sitter grammars."""

    SUPPORTED_LANGUAGES = SUPPORTED_LANGUAGES

    def __init__(self) -> None:
        self._parsers: dict[str, "tree_sitter.Parser"] = {}
        self._language_objects: dict[str, "tree_sitter.Language"] = {}

    def get_language_object(self, extension: str) -> "tree_sitter.Language | None":
        """Return the Language object for queries (e.g. tree_sitter.Query). Caches per grammar."""
        lang_info = self.get_language(extension)
        if not lang_info:
            return None
        grammar_name = lang_info["grammar"]
        if grammar_name in self._language_objects:
            return self._language_objects[grammar_name]
        try:
            from tree_sitter import Language

            grammar_module = importlib.import_module(grammar_name)
            lang_obj = Language(grammar_module.language())
            self._language_objects[grammar_name] = lang_obj
            return lang_obj
        except ImportError:
            return None

    def get_language(self, extension: str) -> dict[str, str] | None:
        """Return language info for the extension, or None if unsupported."""
        ext = extension if extension.startswith(".") else f".{extension}"
        return self.SUPPORTED_LANGUAGES.get(ext)

    def is_supported(self, extension: str) -> bool:
        """Return True if the extension is supported."""
        ext = extension if extension.startswith(".") else f".{extension}"
        return ext in self.SUPPORTED_LANGUAGES

    def get_parser(self, extension: str) -> "tree_sitter.Parser | None":
        """
        Initialize and return a tree-sitter Parser for the given extension.
        Caches parsers; returns None for unsupported extensions or if grammar fails to load.
        """
        lang_info = self.get_language(extension)
        if not lang_info:
            return None

        grammar_name = lang_info["grammar"]
        if grammar_name in self._parsers:
            return self._parsers[grammar_name]

        try:
            from tree_sitter import Language, Parser

            lang_obj = self.get_language_object(extension)
            if lang_obj is None:
                return None
            parser = Parser(lang_obj)
            self._parsers[grammar_name] = parser
            return parser
        except ImportError:
            return None
