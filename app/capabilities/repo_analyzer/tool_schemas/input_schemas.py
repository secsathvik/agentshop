"""Pydantic models for tool inputs."""

from pydantic import BaseModel


class SymbolLookupInput(BaseModel):
    """Input for symbol lookup tool."""

    symbol_name: str
    module: str | None = None


class ImpactAnalysisInput(BaseModel):
    """Input for impact analysis tool."""

    module: str


class CallGraphInput(BaseModel):
    """Input for call graph tool."""

    module: str
    direction: str = "both"  # "upstream" | "downstream" | "both"


class SafeRenameInput(BaseModel):
    """Input for safe rename tool."""

    module: str
    new_name: str
