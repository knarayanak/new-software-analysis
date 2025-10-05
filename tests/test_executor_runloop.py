import json
import importlib
from pathlib import Path

def test_preflight_ok_with_non_protected_paths(tmp_path, monkeypatch):
    # Build minimal "app" so import succeeds from tmp root
    (tmp_path / "app").mkdir(parents=True, exist_ok=True)
    (tmp_path / "app" / "__init__.py").write_text("", encoding="utf-8")

    rl = importlib.import_module("app.executor.runloop")
    pre = rl.preflight_checks(
        root=str(tmp_path),
        allowed_paths=["app/executor/runloop.py"],
        protected_paths=["app/orchestrator/workflow.py"],
        run_commands=["py -m pytest -q"],
        env_vars_available=[]
    )
    assert pre["ok"] is True
    assert pre["import_ok"] is True
    assert pre["conflicts"] == []
    assert pre["classification"] is None

def test_preflight_blocked_needs_override_on_protected_conflict(tmp_path):
    # Minimal app for import OK
    (tmp_path / "app").mkdir(parents=True, exist_ok=True)
    (tmp_path / "app" / "__init__.py").write_text("", encoding="utf-8")

    rl = importlib.import_module("app.executor.runloop")
    pre = rl.preflight_checks(
        root=str(tmp_path),
        allowed_paths=["app/orchestrator/workflow.py"],  # conflict
        protected_paths=["app/orchestrator/workflow.py", "tests/test_orchestrator_workflow.py"]
    )
    assert pre["ok"] is False
    assert pre["classification"] == "blocked_needs_override"
    assert "workflow.py" in (pre["issues"][0] if pre["issues"] else "")

def test_preflight_environment_mismatch_when_import_fails(tmp_path):
    # Do NOT create app/ -> import must fail
    rl = importlib.import_module("app.executor.runloop")
    pre = rl.preflight_checks(
        root=str(tmp_path),
        allowed_paths=[],
        protected_paths=[]
    )
    assert pre["ok"] is False
    assert pre["import_ok"] is False
    assert pre["classification"] == "environment_mismatch"

def test_plan_next_item_and_thin_run_loop_selects_highest_priority_ready(tmp_path):
    # Create a small backlog and minimal app for import OK
    (tmp_path / "app").mkdir(parents=True, exist_ok=True)
    (tmp_path / "app" / "__init__.py").write_text("", encoding="utf-8")
    b = tmp_path / "backlog"; b.mkdir(parents=True, exist_ok=True)

    def write(p: Path, d: dict): p.write_text(json.dumps(d), encoding="utf-8")

    write(b / "a.json", {
        "id": "A", "title": "A", "priority": 2, "status": "ready",
        "dependencies": [], "allowed_paths": ["app/executor/runloop.py"]
    })
    write(b / "b.json", {
        "id": "B", "title": "B", "priority": 1, "status": "ready",
        "dependencies": ["A"], "allowed_paths": ["app/executor/runloop.py"]
    })

    wf = importlib.import_module("app.orchestrator.workflow")
    rl = importlib.import_module("app.executor.runloop")

    plan = rl.plan_next_item(str(tmp_path))
    assert plan and plan["story_id"] == "A"  # A first (deps satisfied)

    # thin_run_loop should be ready_to_execute with non-conflicting protected zone
    out = rl.thin_run_loop(str(tmp_path), protected_paths=["app/orchestrator/workflow.py"])
    assert out["status"] == "ready_to_execute"
    assert out["selected"]["story_id"] == "A"

def test_thin_run_loop_no_ready_story(tmp_path):
    # Minimal app + empty backlog dir
    (tmp_path / "app").mkdir(parents=True, exist_ok=True)
    (tmp_path / "app" / "__init__.py").write_text("", encoding="utf-8")
    (tmp_path / "backlog").mkdir(parents=True, exist_ok=True)

    rl = importlib.import_module("app.executor.runloop")
    out = rl.thin_run_loop(str(tmp_path), protected_paths=[])
    assert out["status"] == "no_ready_story"
    assert out["selected"] is None and out["preflight"] is None
