"""Parses source files into syntax trees using tree-sitter."""

import logging
from dataclasses import dataclass

import tree_sitter

from app.capabilities.repo_analyzer.indexer.language_registry import LanguageRegistry
from app.capabilities.repo_analyzer.indexer.repository_indexer import IndexedFile

logger = logging.getLogger(__name__)


@dataclass
class ParsedFile:
    """A successfully parsed file with its syntax tree and content."""

    indexed_file: IndexedFile
    tree: tree_sitter.Tree
    content: bytes
    parse_errors: bool


class TreeSitterParser:
    """Parses source files into tree-sitter syntax trees."""

    def __init__(self, language_registry: LanguageRegistry) -> None:
        self.language_registry = language_registry

    def parse_file(self, indexed_file: IndexedFile) -> ParsedFile | None:
        """
        Parse an indexed file into a syntax tree.
        Returns ParsedFile or None on failure.
        """
        try:
            content = indexed_file.path.read_bytes()
        except Exception as e:
            logger.exception("Failed to read file %s: %s", indexed_file.relative_path, e)
            return None

        parser = self.language_registry.get_parser(indexed_file.extension)
        if parser is None:
            logger.warning("No parser for extension %s: %s", indexed_file.extension, indexed_file.relative_path)
            return None

        try:
            tree = parser.parse(content)
        except Exception as e:
            logger.exception("Parse failed for %s: %s", indexed_file.relative_path, e)
            return None

        parse_errors = tree.root_node.has_error if tree.root_node else True

        return ParsedFile(
            indexed_file=indexed_file,
            tree=tree,
            content=content,
            parse_errors=parse_errors,
        )

    def parse_files(self, indexed_files: list[IndexedFile]) -> list[ParsedFile]:
        """Parse multiple files, returning only successful parses."""
        results: list[ParsedFile] = []
        for f in indexed_files:
            parsed = self.parse_file(f)
            if parsed is not None:
                results.append(parsed)
        return results
