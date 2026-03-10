from pydantic import BaseModel, ConfigDict, Field


class CapabilityInfo(BaseModel):
    """
    Full metadata for a capability in the AgentShop system. Describes what an agent
    can do, its input/output shapes, reliability score, and example use cases.
    Used when registering capabilities and when returning detailed capability details.
    """

    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    description: str
    input_schema: dict
    output_schema: dict
    examples: list[dict]
    reliability: float = Field(ge=0, le=1, description="Score between 0 and 1")
    tags: list[str]


class CapabilitySearchResult(BaseModel):
    """
    Compact representation of a capability for search and discovery endpoints.
    Contains the fields most relevant for filtering and selecting capabilities
    without the full schema or example payloads.
    """

    model_config = ConfigDict(from_attributes=True)

    id: str
    description: str
    reliability: float
    tags: list[str]


class ExecuteRequest(BaseModel):
    """
    Request body for executing a capability. The agent provides the capability ID,
    the input payload conforming to the capability's input_schema, and optional
    context metadata (e.g., user ID, session ID) for the capability to use.
    """

    model_config = ConfigDict(from_attributes=True)

    capability_id: str
    input: dict
    context: dict | None = None


class ExecuteResponse(BaseModel):
    """
    Response from a capability execution. Includes the result payload, success flag,
    execution time, and an optional error message when execution fails.
    """

    model_config = ConfigDict(from_attributes=True)

    capability_id: str
    result: dict
    success: bool
    execution_time_ms: int
    error: str | None = None
