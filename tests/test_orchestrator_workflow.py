import json
import os
from pathlib import Path
import importlib

def write_story(p: Path, data: dict):
    p.write_text(json.dumps(data), encoding="utf-8")

def test_discover_and_pick_next(tmp_path):
    # Arrange: three stories with priorities and deps
    b = tmp_path / "backlog"
    b.mkdir(parents=True, exist_ok=True)

    write_story(b / "a.json", {
        "id": "A", "title": "A", "priority": 2, "status": "ready", "dependencies": []
    })
    write_story(b / "b.json", {
        "id": "B", "title": "B", "priority": 1, "status": "ready", "dependencies": ["A"]
    })
    write_story(b / "c.json", {
        "id": "C", "title": "C", "priority": 1, "status": "blocked", "dependencies": []
    })

    wf = importlib.import_module("app.orchestrator.workflow")
    found = wf.discover_backlog(str(tmp_path))
    # Sorted by (priority,title) => B,C,A on priority, but B depends on A (not done)
    # Only A is ready with deps satisfied
    nxt = wf.pick_next(found)
    assert nxt and nxt["id"] == "A"

    # Simulate A done then pick again
    for s in found:
        if s["id"] == "A":
            s["status"] = "done"
    nxt2 = wf.pick_next(found)
    assert nxt2 and nxt2["id"] == "B"

def test_discover_skips_bad_and_non_story_files(tmp_path):
    b = tmp_path / "backlog"; b.mkdir(parents=True, exist_ok=True)
    (b / "not_a_story.txt").write_text("hello", encoding="utf-8")
    (b / "bad.json").write_text("{ broken", encoding="utf-8")
    (b / "ok.json").write_text(json.dumps({"id":"S1","status":"ready","priority":5}), encoding="utf-8")

    wf = importlib.import_module("app.orchestrator.workflow")
    found = wf.discover_backlog(str(tmp_path))
    assert len(found) == 1 and found[0]["id"] == "S1"

def test_synthesize_fix_gate_variants():
    wf = importlib.import_module("app.orchestrator.workflow")
    assert wf.synthesize_fix_gate(True, True) is None
    s = wf.synthesize_fix_gate(False, True); assert s and s["priority"] == 0
    s2 = wf.synthesize_fix_gate(True, False); assert s2 and "coverage" in s2["title"].lower()
    s3 = wf.synthesize_fix_gate(False, False); assert s3 and "import" in s3["title"].lower()
def test_yaml_loader_and_normalization(tmp_path):
    import importlib
    wf = importlib.import_module("app.orchestrator.workflow")
    b = tmp_path / "backlog"; b.mkdir(parents=True, exist_ok=True)
    # YAML-like (flat) story to exercise _load_any YAML branch + status normalization
    (b / "y1.yaml").write_text(
        'id: "Y1"\n'
        'title: "Yaml Story"\n'
        'priority: 3\n'
        'status: weird\n'
        'dependencies: []\n', encoding="utf-8"
    )
    found = wf.discover_backlog(str(tmp_path))
    assert len(found) == 1
    s = found[0]
    assert s["id"] == "Y1"
    assert s["status"] == "ready"        # invalid -> normalized
    assert s["priority"] == 3
    assert s["dependencies"] == []

def test_discover_backlog_returns_empty_when_missing_dir(tmp_path):
    import importlib
    wf = importlib.import_module("app.orchestrator.workflow")
    assert wf.discover_backlog(str(tmp_path)) == []

def test_discover_defaults_for_missing_fields(tmp_path):
    import json, importlib
    wf = importlib.import_module("app.orchestrator.workflow")
    b = tmp_path / "backlog"; b.mkdir(parents=True, exist_ok=True)
    # Minimal story missing status/priority/dependencies to hit defaults
    (b / "min.json").write_text(json.dumps({"id":"S2"}), encoding="utf-8")
    found = wf.discover_backlog(str(tmp_path))
    s = [x for x in found if x["id"]=="S2"][0]
    assert s["status"] == "ready"
    assert s["priority"] == 999
    assert s["dependencies"] == []

def test_pick_next_none_when_no_candidates_due_to_unsatisfied_deps():
    import importlib
    wf = importlib.import_module("app.orchestrator.workflow")
    stories = [ { "id":"A", "title":"A", "status":"ready", "priority":1, "dependencies":["B"] } ]
    assert wf.pick_next(stories) is None
def test_yaml_parser_ignores_comments_and_no_colon_lines(tmp_path):
    import importlib
    wf = importlib.import_module("app.orchestrator.workflow")
    b = tmp_path / "backlog"; b.mkdir(parents=True, exist_ok=True)
    (b / "y2.yaml").write_text(
        '# comment line\n'
        '   \n'                       # blank -> line 32
        'nonsense\n'                  # no colon -> line 30
        'id: \"Y2\"\n'
        'title: \"With Noise\"\n',
        encoding='utf-8'
    )
    found = wf.discover_backlog(str(tmp_path))
    assert any(s['id'] == 'Y2' for s in found)

def test_discover_skips_story_without_id(tmp_path):
    import json, importlib
    wf = importlib.import_module("app.orchestrator.workflow")
    b = tmp_path / "backlog"; b.mkdir(parents=True, exist_ok=True)
    # Missing 'id' -> hits line 42 (skip)
    (b / "noid.json").write_text(json.dumps({"title":"NoID","priority":1,"status":"ready"}), encoding="utf-8")
    (b / "ok.json").write_text(json.dumps({"id":"OK","title":"OK","priority":2,"status":"ready"}), encoding="utf-8")
    found = wf.discover_backlog(str(tmp_path))
    ids = [s['id'] for s in found]
    assert "OK" in ids and all("NoID" not in str(s) for s in found)

def test_pick_next_returns_none_for_empty_list():
    import importlib
    wf = importlib.import_module("app.orchestrator.workflow")
    # hits line 63: early return on empty list
    assert wf.pick_next([]) is None

def test_pick_next_deterministic_order_on_priority_tie(tmp_path):
    # covers tie ordering path (line 83)
    import json, importlib
    wf = importlib.import_module("app.orchestrator.workflow")
    b = tmp_path / "backlog"; b.mkdir(parents=True, exist_ok=True)
    (b / "b.json").write_text(json.dumps({"id":"B","title":"Bravo","priority":1,"status":"ready"}), encoding="utf-8")
    (b / "a.json").write_text(json.dumps({"id":"A","title":"Alpha","priority":1,"status":"ready"}), encoding="utf-8")
    found = wf.discover_backlog(str(tmp_path))
    assert [s["id"] for s in found][:2] == ["A","B"]
    assert wf.pick_next(found)["id"] == "A"
