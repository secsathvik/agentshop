import time

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.db.models import ExecutionLog
from app.registry.registry import CapabilityNotFoundError, get_registry
from app.schemas.capability import (
    CapabilitySearchResult,
    ExecuteRequest,
    ExecuteResponse,
)

router = APIRouter(tags=["capabilities"])


@router.get(
    "/capabilities",
    response_model=list[CapabilitySearchResult],
    summary="List or search capabilities",
)
async def list_capabilities(
    task: str | None = Query(default=None, description="Search term for filtering by description or tags"),
) -> list[CapabilitySearchResult]:
    """
    List available capabilities. If `task` is provided, returns capabilities matching
    the search term in their description or tags. Otherwise returns all registered capabilities.
    """
    registry = get_registry()
    if task is not None and task.strip():
        return registry.search(task)
    return registry.list_all()


@router.post(
    "/execute",
    response_model=ExecuteResponse,
    summary="Execute a capability",
)
async def execute_capability(
    request: ExecuteRequest,
    db: AsyncSession = Depends(get_db),
) -> ExecuteResponse:
    """
    Execute a capability by ID. Runs the capability handler with the provided input,
    records the execution in the database, and returns a structured response.
    Returns 404 if the capability does not exist. Returns 200 with success=False
    if execution fails (agent receives a structured error response).
    """
    registry = get_registry()
    try:
        handler = registry.get(request.capability_id)
    except CapabilityNotFoundError as e:
        raise HTTPException(status_code=404, detail=f"Capability not found: {e.capability_id}")

    start_ms = time.perf_counter_ns() // 1_000_000
    try:
        result = await handler.handler(request.input)
        success = True
        error_msg = None
    except Exception as exc:
        result = {}
        success = False
        error_msg = str(exc)

    end_ms = time.perf_counter_ns() // 1_000_000
    execution_time_ms = int(end_ms - start_ms)

    log = ExecutionLog(
        capability_id=request.capability_id,
        input=request.input,
        result=result,
        success=success,
        execution_time_ms=execution_time_ms,
        error=error_msg,
        agent_context=request.context,
    )
    db.add(log)
    await db.commit()

    return ExecuteResponse(
        capability_id=request.capability_id,
        result=result,
        success=success,
        execution_time_ms=execution_time_ms,
        error=error_msg,
    )
