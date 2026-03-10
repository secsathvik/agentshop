from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from app.schemas.capability import CapabilityInfo, CapabilitySearchResult


class CapabilityNotFoundError(Exception):
    """Raised when a capability is requested by ID but not found in the registry."""

    def __init__(self, capability_id: str) -> None:
        self.capability_id = capability_id
        super().__init__(f"Capability not found: {capability_id}")


@dataclass
class CapabilityHandler:
    """Registry entry for a capability: metadata plus the async handler function."""

    capability_id: str
    metadata: CapabilityInfo
    handler: Callable[[dict], Awaitable[dict]]


class CapabilityRegistry:
    """In-memory registry mapping capability IDs to handlers. Singleton, initialized at startup."""

    def __init__(self) -> None:
        self._handlers: dict[str, CapabilityHandler] = {}

    def register(
        self,
        capability_id: str,
        metadata: CapabilityInfo,
        handler: Callable[[dict], Awaitable[dict]],
    ) -> None:
        """Register a new capability with its metadata and async handler."""
        self._handlers[capability_id] = CapabilityHandler(
            capability_id=capability_id,
            metadata=metadata,
            handler=handler,
        )

    def get(self, capability_id: str) -> CapabilityHandler:
        """Return the handler for the given capability ID. Raises CapabilityNotFoundError if not found."""
        if capability_id not in self._handlers:
            raise CapabilityNotFoundError(capability_id)
        return self._handlers[capability_id]

    def search(self, task: str) -> list[CapabilitySearchResult]:
        """Search capabilities by keyword matching against description and tags. Returns list of matches."""
        if not task or not task.strip():
            return self.list_all()
        words = [w.lower() for w in task.strip().split() if w]
        results: list[CapabilitySearchResult] = []
        for h in self._handlers.values():
            m = h.metadata
            desc_lower = m.description.lower()
            tags_lower = [t.lower() for t in m.tags]
            if any(
                word in desc_lower or any(word in t for t in tags_lower)
                for word in words
            ):
                results.append(
                    CapabilitySearchResult(
                        id=m.id,
                        description=m.description,
                        reliability=m.reliability,
                        tags=m.tags,
                    )
                )
        return results

    def list_all(self) -> list[CapabilitySearchResult]:
        """Return all registered capabilities as search results."""
        return [
            CapabilitySearchResult(
                id=h.metadata.id,
                description=h.metadata.description,
                reliability=h.metadata.reliability,
                tags=h.metadata.tags,
            )
            for h in self._handlers.values()
        ]


_registry: CapabilityRegistry | None = None


def get_registry() -> CapabilityRegistry:
    """Return the singleton registry instance. Must be initialized via init_registry first."""
    if _registry is None:
        raise RuntimeError("CapabilityRegistry not initialized. Call init_registry() on startup.")
    return _registry


def init_registry() -> CapabilityRegistry:
    """Create and return the singleton registry. Call once at app startup."""
    global _registry
    _registry = CapabilityRegistry()
    return _registry
