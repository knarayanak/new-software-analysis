import json
import os
from pathlib import Path
import importlib

def _read_json(p: Path) -> dict:
    return json.loads(p.read_text(encoding="utf-8"))

def test_rebuild_when_missing(tmp_path):
    # Arrange: ensure a tangible artifact exists
    (tmp_path / "app").mkdir(parents=True, exist_ok=True)
    (tmp_path / "app" / "dummy.txt").write_text("hello", encoding="utf-8")

    state_mod = importlib.import_module("app.orchestrator.state")
    # Act: load_state should rebuild when state.json doesn't exist
    state = state_mod.load_state(str(tmp_path))

    # Assert: shape + file exists
    state_file = tmp_path / ".orchestrator" / "state.json"
    assert state_file.exists(), "state.json should be created on rebuild"
    assert set(state.keys()) >= {
        "version","last_updated","environment_fingerprint","stories",
        "artifacts_manifest","coverage_history","protected_zone","resume_token",
        "quarantine_tests","container_fingerprint","metrics","role_progress",
    }
    # Artifacts manifest contains dummy file
    assert any(a["path"].endswith("app/dummy.txt") for a in state["artifacts_manifest"])

def test_load_existing_valid_state(tmp_path):
    # Arrange: write a valid minimal state file
    (tmp_path / ".orchestrator").mkdir(parents=True, exist_ok=True)
    valid = {
        "version": 1,
        "last_updated": "2025-01-01T00:00:00Z",
        "environment_fingerprint": {"os":"x","python":"3.12","libs":{},"run_commands":[]},
        "stories": [],
        "artifacts_manifest": [],
        "coverage_history": [],
        "protected_zone": {"paths":[]},
        "resume_token": "abc",
        "quarantine_tests": [],
        "container_fingerprint": None,
        "metrics": {"throughput":0,"error_rate":0},
        "role_progress": {},
    }
    sf = tmp_path / ".orchestrator" / "state.json"
    sf.write_text(json.dumps(valid), encoding="utf-8")

    state_mod = importlib.import_module("app.orchestrator.state")
    loaded = state_mod.load_state(str(tmp_path))
    assert loaded["last_updated"] == "2025-01-01T00:00:00Z"

def test_load_corrupt_state_triggers_rebuild(tmp_path):
    # Write corrupt JSON → exercises json.JSONDecodeError branch
    orch = tmp_path / ".orchestrator"
    orch.mkdir(parents=True, exist_ok=True)
    (orch / "state.json").write_text("{ bad json", encoding="utf-8")
    state_mod = importlib.import_module("app.orchestrator.state")
    state = state_mod.load_state(str(tmp_path))
    # file rewritten to a valid minimal state
    new_json = json.loads((orch / "state.json").read_text(encoding="utf-8"))
    assert set(new_json.keys()) >= {
        "version","last_updated","environment_fingerprint","stories","artifacts_manifest",
        "protected_zone","resume_token","metrics","role_progress","coverage_history",
        "quarantine_tests","container_fingerprint"
    }
    assert isinstance(state, dict)

def test_load_invalid_state_triggers_rebuild(tmp_path):
    # Valid JSON but missing keys → exercises _valid_state failure branch
    orch = tmp_path / ".orchestrator"
    orch.mkdir(parents=True, exist_ok=True)
    (orch / "state.json").write_text(json.dumps({"foo":"bar"}), encoding="utf-8")
    state_mod = importlib.import_module("app.orchestrator.state")
    state = state_mod.load_state(str(tmp_path))
    assert set(state.keys()) >= {"version","environment_fingerprint","artifacts_manifest"}

def test_compute_environment_fingerprint_with_commands():
    state_mod = importlib.import_module("app.orchestrator.state")
    fp = state_mod.compute_environment_fingerprint(["py -V","pytest -q"])
    assert "python" in fp
    assert isinstance(fp["run_commands"], list)
    assert "pytest -q" in fp["run_commands"]

def test_artifacts_manifest_omits_dirs_and_suffixes(tmp_path):
    # Create files including omitted ones (dir + suffix)
    (tmp_path / "keep").mkdir(parents=True, exist_ok=True)
    (tmp_path / "keep" / "x.txt").write_text("hi", encoding="utf-8")
    omit_dir = tmp_path / ".pytest_cache"
    omit_dir.mkdir(parents=True, exist_ok=True)
    (omit_dir / "y.txt").write_text("dontcount", encoding="utf-8")
    (tmp_path / "z.pyc").write_text("compiled", encoding="utf-8")  # suffix omitted

    state_mod = importlib.import_module("app.orchestrator.state")
    artifacts = state_mod.compute_artifacts_manifest(str(tmp_path))
    paths = [a["path"] for a in artifacts]
    assert any(p.endswith("keep/x.txt") for p in paths)
    assert not any(".pytest_cache" in p for p in paths)
    assert not any(p.endswith("z.pyc") for p in paths)

def test_artifacts_manifest_handles_permissionerror(tmp_path, monkeypatch):
    # Simulate PermissionError for a specific file to exercise the except branch
    target = (tmp_path / "keep2")
    target.mkdir(parents=True, exist_ok=True)
    fpath = target / "blocked.txt"
    fpath.write_text("secret", encoding="utf-8")

    state_mod = importlib.import_module("app.orchestrator.state")
    real_sha = state_mod._sha256_file  # noqa: SLF001 (accessing internal for test)

    def fake_sha(path):
        # Raise only for our target to stay deterministic
        if str(path).replace("\\","/").endswith("keep2/blocked.txt"):
            raise PermissionError("nope")
        return real_sha(path)

    monkeypatch.setattr(state_mod, "_sha256_file", fake_sha)
    artifacts = state_mod.compute_artifacts_manifest(str(tmp_path))
    # The blocked file should be skipped (not present); the function must still succeed
    assert not any(p["path"].endswith("keep2/blocked.txt") for p in artifacts)
