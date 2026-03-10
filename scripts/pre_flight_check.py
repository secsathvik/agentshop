import asyncio
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

async def run_checks():
    results = []

    # Check 1: Schemas serialize correctly
    try:
        from app.capabilities.repo_analyzer.schemas import DependencyEdge
        e = DependencyEdge(
            from_module="app.main",
            to_module="app.db",
            import_type="import"
        )
        data = e.model_dump()
        assert "from" in data and "to" in data, "Wrong field names"
        assert "from_module" not in data, "from_module should not appear"
        results.append(("Schema serialization", True, "from/to keys correct"))
    except Exception as ex:
        results.append(("Schema serialization", False, str(ex)))

    # Check 2: File walker excludes alembic and scripts
    try:
        from app.capabilities.repo_analyzer.file_walker import collect_python_files
        files = collect_python_files(".")
        paths = [path for _, path in files]
        alembic_files = [p for p in paths if p.startswith("alembic/")]
        script_files = [p for p in paths if p.startswith("scripts/")]
        assert len(alembic_files) == 0, f"alembic files found: {alembic_files}"
        assert len(script_files) == 0, f"script files found: {script_files}"
        results.append(("Alembic/scripts excluded", True, f"{len(files)} files found"))
    except Exception as ex:
        results.append(("Alembic/scripts excluded", False, str(ex)))

    # Check 3: Module names use dots not backslashes
    try:
        from app.capabilities.repo_analyzer.file_walker import collect_python_files
        files = collect_python_files(".")
        bad = [name for name, _ in files if "\\" in name]
        assert len(bad) == 0, f"Backslashes in module names: {bad}"
        results.append(("Module name format", True, "All dots, no backslashes"))
    except Exception as ex:
        results.append(("Module name format", False, str(ex)))

    # Check 4: Analyzer runs and returns success
    try:
        from app.capabilities.repo_analyzer.analyzer import analyze_async
        result = await analyze_async({"repo_path": "."})
        assert result["success"] == True, f"success=False: {result.get('error')}"
        assert len(result["modules"]) > 0, "No modules found"
        assert len(result["dependencies"]) > 0, "No dependencies found"
        results.append(("Analyzer runs", True,
            f"{len(result['modules'])} modules, "
            f"{len(result['dependencies'])} deps"))
    except Exception as ex:
        results.append(("Analyzer runs", False, str(ex)))

    # Check 5: Refactor suggestions are non-empty
    try:
        from app.capabilities.repo_analyzer.analyzer import analyze_async
        result = await analyze_async({"repo_path": "."})
        suggestions = result.get("refactor_suggestions", [])
        assert len(suggestions) > 0, "No refactor suggestions generated"
        results.append(("Refactor suggestions", True,
            f"{len(suggestions)} suggestion(s): {suggestions[0][:60]}..."))
    except Exception as ex:
        results.append(("Refactor suggestions", False, str(ex)))

    # Check 6: Architecture summary mentions FastAPI
    try:
        from app.capabilities.repo_analyzer.analyzer import analyze_async
        result = await analyze_async({"repo_path": "."})
        summary = result.get("architecture_summary", "")
        assert "FastAPI" in summary or "layered" in summary.lower(), \
            f"Summary too generic: {summary}"
        results.append(("Architecture summary", True, summary[:80] + "..."))
    except Exception as ex:
        results.append(("Architecture summary", False, str(ex)))

    # Check 7: Empty modules filtered out
    try:
        from app.capabilities.repo_analyzer.analyzer import analyze_async
        result = await analyze_async({"repo_path": "."})
        empty = [
            m for m in result["modules"]
            if m["line_count"] == 0
            and len(m["functions"]) == 0
            and len(m["classes"]) == 0
        ]
        assert len(empty) == 0, f"Empty modules still present: {[m['name'] for m in empty]}"
        results.append(("Empty modules filtered", True, "No empty modules in output"))
    except Exception as ex:
        results.append(("Empty modules filtered", False, str(ex)))

    # Print results
    print("\n=== Pre-Flight Check Results ===\n")
    passed = 0
    failed = 0
    for name, ok, detail in results:
        status = "PASS" if ok else "FAIL"
        print(f"  [{status}] {name}")
        print(f"         {detail}")
        if ok:
            passed += 1
        else:
            failed += 1

    print(f"\n  {passed} passed, {failed} failed")

    if failed > 0:
        print("\n  Fix all failures before running Phase 2 prompts.")
        sys.exit(1)
    else:
        print("\n  All checks passed. Safe to proceed with Phase 2.")
        sys.exit(0)

if __name__ == "__main__":
    asyncio.run(run_checks())
