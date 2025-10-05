"""
Executor pre-flight checks + thin run loop (logic-only, no edits).
"""
from __future__ import annotations

import importlib
import os
import sys
from typing import Any, Dict, Iterable, List, Optional

# --- helpers -----------------------------------------------------------------

def _normalize_paths(paths: Iterable[str]) -> List[str]:
    norm: List[str] = []
    for p in paths or []:
        p = p.replace("\\", "/")
        if p.startswith("./"):
            p = p[2:]
        norm.append(p)
    return norm


def _check_protected_conflicts(allowed_paths: Iterable[str], protected_paths: Iterable[str]) -> List[str]:
    allowed = set(_normalize_paths(allowed_paths))
    protected = set(_normalize_paths(protected_paths))
    return sorted(list(allowed.intersection(protected)))


def _can_import_app(root: str):
    """Try importing 'app' and ensure it resolves from *root* (not a global install)."""
    from importlib.machinery import PathFinder
    import importlib.util

    root = os.path.abspath(root)
    added = False
    # Save and purge any preloaded "app" modules so resolution comes from `root`.
    saved_modules = {k: v for k, v in list(sys.modules.items()) if k == "app" or k.startswith("app.")}
    try:
        for k in list(saved_modules.keys()):
            sys.modules.pop(k, None)

        if root not in sys.path:
            sys.path.insert(0, root)
            added = True
        importlib.invalidate_caches()

        # Force spec discovery using ONLY the given root
        spec = PathFinder.find_spec("app", [root])
        if spec is None:
            return False, "ModuleNotFoundError: app"

        root_norm = root.replace("\\", "/")
        origin_ok = False

        if spec.origin:
            origin = os.path.abspath(spec.origin).replace("\\", "/")
            origin_ok = origin.startswith(root_norm)
            if not origin_ok:  # pragma: no cover
                return False, f"environment mismatch: resolved app outside root -> {origin}"  # pragma: no cover"
        else:  # pragma: no cover
            locations = list(spec.submodule_search_locations or [])
            if any(os.path.abspath(p).replace("\\", "/").startswith(root_norm) for p in locations):
                origin_ok = True
            if not origin_ok:  # pragma: no cover
                return False, f"environment mismatch: resolved app outside root -> {locations}"  # pragma: no cover"

        # Actually import to ensure it loads
        importlib.import_module("app")
        return True, None
    except Exception as exc:
        return False, f"{type(exc).__name__}: {exc}"
    finally:
        # Restore search path
        if added and root in sys.path:
            try:
                sys.path.remove(root)
            except ValueError:
                pass
        # Restore any previously loaded app modules to avoid side effects
        # First remove any app/app.* modules created during this check,
        # then put the originals back.
        for k in list(sys.modules.keys()):
            if k == "app" or k.startswith("app."):
                sys.modules.pop(k, None)
        for k, v in saved_modules.items():
            sys.modules[k] = v

# --- public API --------------------------------------------------------------

def preflight_checks(
    root: str,
    allowed_paths: Iterable[str],
    protected_paths: Iterable[str],
    run_commands: Optional[Iterable[str]] = None,
    env_vars_available: Optional[Iterable[str]] = None,
) -> Dict[str, Any]:
    """
    Validate environment and path safety.
    Returns a dict:
    {
      "ok": bool,
      "import_ok": bool,
      "conflicts": [<paths>],
      "classification": null | "blocked_needs_override" | "environment_mismatch",
      "issues": [<notes>]
    }
    """
    issues: List[str] = []

    # 1) Import check
    import_ok, err = _can_import_app(root)
    if not import_ok:
        issues.append(f"Import check failed: {err}")

    # 2) Protected paths check
    conflicts = _check_protected_conflicts(allowed_paths or [], protected_paths or [])
    if conflicts:
        issues.append("Allowed paths intersect Protected Zone: " + ", ".join(conflicts))

    classification = None
    if conflicts:
        classification = "blocked_needs_override"
    elif not import_ok:
        classification = "environment_mismatch"

    ok = (classification is None)
    return {
        "ok": ok,
        "import_ok": import_ok,
        "conflicts": conflicts,
        "classification": classification,
        "issues": issues,
        "run_commands": list(run_commands or []),
        "env_vars_available": list(env_vars_available or []),
    }


def plan_next_item(root: str) -> Optional[Dict[str, Any]]:
    """
    Discover backlog and pick the next story (no edits).
    Returns an execution plan dict or None when nothing is ready.
    """
    wf = importlib.import_module("app.orchestrator.workflow")
    stories = wf.discover_backlog(root)
    nxt = wf.pick_next(stories)
    if not nxt:
        return None
    return {
        "story_id": nxt["id"],
        "title": nxt.get("title", ""),
        "priority": nxt.get("priority", 999),
        "allowed_paths": nxt.get("allowed_paths", []),
        "risk_level": nxt.get("risk_level", "low"),
        "assigned_role": nxt.get("assigned_role", ""),
        "status": "ready",
    }


def thin_run_loop(root: str, protected_paths: Iterable[str]) -> Dict[str, Any]:
    """
    Thin, non-editing run loop:
      1) pick next story
      2) run preflight (using that story's allowed_paths)
      3) return payload
    """
    plan = plan_next_item(root)
    if not plan:
        return {"selected": None, "preflight": None, "status": "no_ready_story"}

    pre = preflight_checks(
        root=root,
        allowed_paths=plan.get("allowed_paths", []),
        protected_paths=protected_paths or [],
    )
    status = "ready_to_execute" if pre["ok"] else pre.get("classification") or "blocked"
    return {"selected": plan, "preflight": pre, "status": status}



