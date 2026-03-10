"""Pydantic models for tool outputs."""

from pydantic import BaseModel


class SymbolLookupOutput(BaseModel):
    """Output from symbol lookup tool."""

    results: list[dict]
    count: int


class ImpactAnalysisOutput(BaseModel):
    """Output from impact analysis tool."""

    module: str
    upstream: list[str]
    downstream: list[str]
    upstream_count: int
    downstream_count: int


class CallGraphOutput(BaseModel):
    """Output from call graph tool."""

    module: str
    imports: list[str]
    imported_by: list[str]


class SafeRenameOutput(BaseModel):
    """Output from safe rename tool."""

    old_name: str
    new_name: str
    impact: dict
    note: str
