#!/usr/bin/env python
"""Smoke tests for the AgentShop API. Requires the API to be running."""

import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import httpx

API_URL = os.environ.get("API_URL", "http://localhost:8000")
BASE = API_URL.rstrip("/")


async def run_test(name: str, coro):
    """Run a test and print PASS/FAIL with response info."""
    try:
        result = await coro
        print(f"[PASS] {name}")
        if result:
            print(f"       Response: {result}")
        return True
    except Exception as e:
        print(f"[FAIL] {name}")
        print(f"       Error: {e}")
        return False


async def test_health(client: httpx.AsyncClient) -> bool:
    r = await client.get(f"{BASE}/health")
    if r.status_code != 200:
        raise AssertionError(f"status={r.status_code}, body={r.text}")
    data = r.json()
    if data.get("status") != "ok":
        raise AssertionError(f"expected status=ok, got {data}")
    return str(data)


async def test_list_capabilities(client: httpx.AsyncClient) -> bool:
    r = await client.get(f"{BASE}/api/v1/capabilities")
    if r.status_code != 200:
        raise AssertionError(f"status={r.status_code}, body={r.text}")
    data = r.json()
    if not isinstance(data, list):
        raise AssertionError(f"expected list, got {type(data)}")
    if len(data) < 5:
        raise AssertionError(f"expected >= 5 items, got {len(data)}")
    return f"list with {len(data)} items"


async def test_search_security(client: httpx.AsyncClient) -> bool:
    r = await client.get(f"{BASE}/api/v1/capabilities", params={"task": "security"})
    if r.status_code != 200:
        raise AssertionError(f"status={r.status_code}, body={r.text}")
    data = r.json()
    ids = [item["id"] for item in data]
    if "security_scanner" not in ids:
        raise AssertionError(f"expected security_scanner in results, got {ids}")
    return f"security_scanner in {ids}"


async def test_execute_repo_analyzer(client: httpx.AsyncClient) -> bool:
    repo_path = str(Path(__file__).resolve().parent.parent)
    r = await client.post(
        f"{BASE}/api/v1/execute",
        json={"capability_id": "repo_analyzer", "input": {"repo_path": repo_path}},
    )
    if r.status_code != 200:
        raise AssertionError(f"status={r.status_code}, body={r.text}")
    data = r.json()
    if not data.get("success"):
        raise AssertionError(f"expected success=True, got {data}")
    if data.get("capability_id") != "repo_analyzer":
        raise AssertionError(f"expected capability_id=repo_analyzer, got {data.get('capability_id')}")
    return f"success={data['success']}, result={data.get('result')}"


async def test_repo_analyzer_real_output(client: httpx.AsyncClient) -> bool:
    r = await client.post(
        f"{BASE}/api/v1/execute",
        json={"capability_id": "repo_analyzer", "input": {"repo_path": "."}},
    )
    if r.status_code != 200:
        raise AssertionError(f"status={r.status_code}, body={r.text}")
    data = r.json()
    if not data.get("success"):
        raise AssertionError(f"expected success=True, got {data}")
    result = data.get("result", {})
    if "modules" not in result:
        raise AssertionError(f"expected 'modules' in result, got keys {list(result.keys())}")
    if len(result["modules"]) <= 0:
        raise AssertionError(f"expected len(modules) > 0, got {len(result['modules'])}")
    if "dependencies" not in result:
        raise AssertionError(f"expected 'dependencies' in result, got keys {list(result.keys())}")
    if "architecture_summary" not in result:
        raise AssertionError(f"expected 'architecture_summary' in result, got keys {list(result.keys())}")
    stats = result.get("stats", {})
    if stats.get("total_files", 0) <= 0:
        raise AssertionError(f"expected result['stats']['total_files'] > 0, got {stats.get('total_files')}")
    module_count = len(result["modules"])
    dep_count = len(result["dependencies"]) if isinstance(result["dependencies"], (list, dict)) else 0
    return f"{module_count} modules, {dep_count} dependencies"


async def test_execute_nonexistent(client: httpx.AsyncClient) -> bool:
    r = await client.post(
        f"{BASE}/api/v1/execute",
        json={"capability_id": "nonexistent", "input": {}},
    )
    if r.status_code != 404:
        raise AssertionError(f"expected status=404, got {r.status_code}, body={r.text}")
    return f"404 as expected"


async def main() -> int:
    print(f"Smoke tests against {BASE}\n")
    results = []
    async with httpx.AsyncClient(timeout=10.0) as client:
        results.append(await run_test("GET /health -> status=ok", test_health(client)))
        results.append(await run_test("GET /api/v1/capabilities -> 5 items", test_list_capabilities(client)))
        results.append(
            await run_test(
                "GET /api/v1/capabilities?task=security -> security_scanner",
                test_search_security(client),
            )
        )
        results.append(
            await run_test(
                "POST /api/v1/execute repo_analyzer -> success=True",
                test_execute_repo_analyzer(client),
            )
        )
        results.append(
            await run_test(
                "POST /api/v1/execute nonexistent -> 404",
                test_execute_nonexistent(client),
            )
        )
        results.append(
            await run_test(
                "POST /api/v1/execute repo_analyzer real output",
                test_repo_analyzer_real_output(client),
            )
        )
    passed = sum(results)
    total = len(results)
    print(f"\n{passed}/{total} tests passed")
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
