"""
State discovery & rebuild utilities for the file-driven orchestrator.

Rules:
- File system is the source of truth; no hidden state.
- Persist ONLY under <root>/.orchestrator/state.json.
- Deterministic & idempotent outputs; UTF-8 (no BOM).
- No network; stdlib only.

Public API:
- load_state(root:str) -> dict
- rebuild_state(root:str) -> dict
- compute_artifacts_manifest(root:str) -> list[dict]
- compute_environment_fingerprint(run_commands:list[str]|None) -> dict
"""
from __future__ import annotations

import hashlib
import json
import os
import platform
import sys
import time
import uuid
from typing import Iterable, List, Dict, Any

ORCH_DIR = ".orchestrator"
STATE_FILENAME = "state.json"

_REQUIRED_KEYS = {
    "version",
    "last_updated",
    "environment_fingerprint",
    "stories",
    "artifacts_manifest",
    "coverage_history",
    "protected_zone",
    "resume_token",
    "quarantine_tests",
    "container_fingerprint",
    "metrics",
    "role_progress",
}

_OMIT_DIRS = {
    ORCH_DIR,
    ".git",
    ".svn",
    ".hg",
    ".venv",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
}
_OMIT_FILE_PATTERNS = {".pyc", ".pyo", ".pyd", ".db", ".sqlite", ".sqlite3", ".coverage"}

def _is_omitted(path: str) -> bool:
    parts = path.replace("\\", "/").split("/")
    if any(p in _OMIT_DIRS for p in parts):
        return True
    base = os.path.basename(path)
    for suffix in _OMIT_FILE_PATTERNS:
        if base.endswith(suffix):
            return True
    return False

def _sha256_file(fp: str) -> str:
    h = hashlib.sha256()
    with open(fp, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()

def _write_json_no_bom(fp: str, data: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(fp), exist_ok=True)
    # ensure UTF-8 without BOM
    payload = json.dumps(data, ensure_ascii=False, separators=(",", ":"), sort_keys=False, indent=2)
    with open(fp, "w", encoding="utf-8") as f:
        f.write(payload)

def compute_artifacts_manifest(root: str) -> List[Dict[str, Any]]:
    """
    Walk the repository rooted at `root` and return a stable list of file artifacts:
    [{ "path": "<relpath>", "checksum": "<sha256>" }, ...]
    Excludes orchestrator internals and typical ephemeral dirs.
    """
    artifacts: List[Dict[str, Any]] = []
    for dirpath, dirnames, filenames in os.walk(root):
        # prune omitted dirs in-place for speed
        dirnames[:] = [d for d in dirnames if d not in _OMIT_DIRS]
        for name in filenames:
            abspath = os.path.join(dirpath, name)
            rel = os.path.relpath(abspath, root)
            if _is_omitted(rel):
                continue
            try:
                checksum = _sha256_file(abspath)
            except (PermissionError, FileNotFoundError):
                # Skip locked or transient files (Windows/OneDrive friendly)
                continue
            artifacts.append({"path": rel.replace("\\", "/"), "checksum": checksum})
    # sort for determinism
    artifacts.sort(key=lambda x: x["path"])
    return artifacts

def compute_environment_fingerprint(run_commands: Iterable[str] | None = None) -> Dict[str, Any]:
    return {
        "os": platform.platform(),
        "python": sys.version.split()[0],
        "libs": {},  # intentionally empty; can be enriched later
        "run_commands": list(run_commands) if run_commands else [],
    }

def _new_state_skeleton(root: str) -> Dict[str, Any]:
    now_iso = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    state: Dict[str, Any] = {
        "version": 1,
        "last_updated": now_iso,
        "environment_fingerprint": compute_environment_fingerprint(),
        "stories": [],
        "artifacts_manifest": compute_artifacts_manifest(root),
        "coverage_history": [],
        "protected_zone": {"paths": []},
        "resume_token": str(uuid.uuid4()),
        "quarantine_tests": [],
        "container_fingerprint": None,
        "metrics": {"throughput": 0, "error_rate": 0},
        "role_progress": {},
    }
    return state

def _state_path(root: str) -> str:
    return os.path.join(root, ORCH_DIR, STATE_FILENAME)

def _valid_state(obj: Dict[str, Any]) -> bool:
    return isinstance(obj, dict) and _REQUIRED_KEYS.issubset(set(obj.keys()))

def rebuild_state(root: str) -> Dict[str, Any]:
    """
    Rebuild state.json from the live workspace on disk, then persist it.
    Deterministic and idempotent: safe to call repeatedly.
    """
    state = _new_state_skeleton(root)
    _write_json_no_bom(_state_path(root), state)
    return state

def load_state(root: str) -> Dict[str, Any]:
    """
    Load state if present and minimally valid, else rebuild it.
    Always returns a dict in the canonical shape.
    """
    fp = _state_path(root)
    if not os.path.exists(fp):
        return rebuild_state(root)
    try:
        with open(fp, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        # Corrupt or unreadable → rebuild
        return rebuild_state(root)
    if not _valid_state(data):
        return rebuild_state(root)
    return data
