"""
Backlog discovery, selection, and fix-gate detection (pure logic).

- discover_backlog(root) -> list[dict]
- pick_next(stories) -> dict|None
- synthesize_fix_gate(import_ok: bool, tests_ok: bool) -> dict|None
"""
from __future__ import annotations

import json
import os
from typing import Any, Dict, Iterable, List, Optional

BACKLOG_DIR = "backlog"
VALID_STATUSES = {"ready", "in_progress", "done", "blocked"}

def _load_any(fp: str) -> Dict[str, Any]:
    """Load a story file. JSON first; otherwise a tiny flat YAML parser."""
    with open(fp, "r", encoding="utf-8") as f:
        text = f.read()
    stripped = text.strip()
    if stripped.startswith(("{", "[")):
        return json.loads(stripped)

    # Ultra-minimal, flat "key: value" parser for .yml/.yaml
    data: Dict[str, Any] = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" not in line:
            continue
        k, v = line.split(":", 1)
        key = k.strip()
        raw = v.strip()
        # Try JSON-decode any scalar/list/dict (numbers, booleans, [], {})
        try:
            val = json.loads(raw)
        except Exception:
            # Fallback: unquote simple quoted scalars; else keep raw
            if (raw.startswith('"') and raw.endswith('"')) or (raw.startswith("'") and raw.endswith("'")):
                val = raw[1:-1]
            else:
                val = raw
        data[key] = val
    return data

def discover_backlog(root: str) -> List[Dict[str, Any]]:
    bdir = os.path.join(root, BACKLOG_DIR)
    if not os.path.isdir(bdir):
        return []
    out: List[Dict[str, Any]] = []
    for name in os.listdir(bdir):
        if not name.lower().endswith((".json", ".yml", ".yaml")):
            continue
        fp = os.path.join(bdir, name)
        try:
            story = _load_any(fp)
        except Exception:
            # skip unreadable/bad stories
            continue
        if not story or "id" not in story:
            continue
        # Normalize status and defaults
        if story.get("status") not in VALID_STATUSES:
            story["status"] = "ready"
        story.setdefault("dependencies", [])
        story.setdefault("priority", 999)
        out.append(story)
    # Deterministic order: (priority asc, title asc)
    out.sort(key=lambda s: (s.get("priority", 999), s.get("title", "")))
    return out

def _deps_satisfied(story: Dict[str, Any], status_index: Dict[str, str]) -> bool:
    deps: Iterable[str] = story.get("dependencies", [])
    for dep in deps:
        if status_index.get(dep) != "done":
            return False
    return True

def pick_next(stories: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not stories:
        return None
    status_index = {s["id"]: s.get("status", "ready") for s in stories}
    candidates = [
        s for s in stories
        if s.get("status") == "ready" and _deps_satisfied(s, status_index)
    ]
    if not candidates:
        return None
    return candidates[0]  # stories already sorted by discover_backlog

def synthesize_fix_gate(import_ok: bool, tests_ok: bool) -> Optional[Dict[str, Any]]:
    """Return a virtual highest-priority story if imports or tests are failing."""
    if import_ok and tests_ok:
        return None
    title_bits = []
    if not import_ok:
        title_bits.append("import errors")
    if not tests_ok:
        title_bits.append("failing tests/coverage")
    return {
        "id": "fix_gate_virtual",
        "title": "Fix Gate: " + " & ".join(title_bits),
        "priority": 0,
        "status": "ready",
        "dependencies": [],
        "acceptance_criteria": [
            "Imports succeed from WORKSPACE_ROOT",
            "Pytest suite passes with required coverage",
        ],
        "allowed_paths": [],
        "risk_level": "low",
        "auto_generated": True,
        "assigned_role": "QA Engineer/Tester",
    }
