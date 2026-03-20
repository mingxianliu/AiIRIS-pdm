import json
from pathlib import Path

from airis_pdm.figmai.chain_remote import run_chain_remote


def test_chain_remote_pull_only(tmp_path: Path, monkeypatch):
    spec = {"name": "Auth", "meta": {"figmaNodeId": "1:1"}, "sections": [{"type": "card", "name": "Login"}]}
    spec_path = tmp_path / "spec.json"
    spec_path.write_text(json.dumps(spec), encoding="utf-8")

    def fake_request_sync(method, params=None, **kwargs):
        if method == "getNode":
            return {
                "id": "1:1",
                "name": "RemoteRoot",
                "type": "FRAME",
                "visible": True,
                "absoluteBoundingBox": {"x": 0, "y": 0, "width": 320, "height": 640},
                "children": [],
            }
        raise AssertionError(f"unexpected method {method}")

    monkeypatch.setattr("airis_pdm.figmai.chain_remote.request_sync", fake_request_sync)
    result = run_chain_remote(
        spec_path=str(spec_path),
        output_dir=str(tmp_path / "out"),
        target="html",
        sync=False,
    )
    assert result["success"] is True
    assert result["target_node_id"] == "1:1"


def test_chain_remote_sync_then_pull(tmp_path: Path, monkeypatch):
    spec = {"name": "Auth", "sections": [{"type": "card", "name": "Login"}]}
    spec_path = tmp_path / "spec.json"
    spec_path.write_text(json.dumps(spec), encoding="utf-8")

    calls = []

    def fake_request_sync(method, params=None, **kwargs):
        calls.append(method)
        if method == "createNode":
            return {"id": "9:9"}
        if method == "getNode":
            return {
                "id": "9:9",
                "name": "SyncedRoot",
                "type": "FRAME",
                "visible": True,
                "absoluteBoundingBox": {"x": 0, "y": 0, "width": 300, "height": 600},
                "children": [],
            }
        raise AssertionError(f"unexpected method {method}")

    monkeypatch.setattr("airis_pdm.figmai.chain_remote.request_sync", fake_request_sync)
    result = run_chain_remote(
        spec_path=str(spec_path),
        output_dir=str(tmp_path / "out"),
        target="html",
        sync=True,
    )
    assert result["success"] is True
    assert result["target_node_id"] == "9:9"
    assert "createNode" in calls and "getNode" in calls


def test_chain_remote_idempotent_update_first(tmp_path: Path, monkeypatch):
    spec = {
        "name": "Auth",
        "id": "root-1",
        "sections": [{"id": "child-1", "type": "card", "name": "Login"}],
    }
    spec_path = tmp_path / "spec.json"
    spec_path.write_text(json.dumps(spec), encoding="utf-8")

    # 先建立一份既有 mapping，模擬第二次 sync
    state_dir = tmp_path / "state"
    state_dir.mkdir(parents=True, exist_ok=True)
    (state_dir / "state.json").write_text(
        json.dumps({"nodes": {"root-1": "10:10"}, "lastSync": "2026-01-01T00:00:00Z"}),
        encoding="utf-8",
    )

    calls = []

    def fake_request_sync(method, params=None, **kwargs):
        calls.append((method, params or {}))
        if method == "updateNode":
            return True
        if method == "createNode":
            return {"id": "11:11"}
        if method == "getNode":
            return {
                "id": "10:10",
                "name": "UpdatedRoot",
                "type": "FRAME",
                "visible": True,
                "absoluteBoundingBox": {"x": 0, "y": 0, "width": 300, "height": 600},
                "children": [],
            }
        raise AssertionError(f"unexpected method {method}")

    monkeypatch.setattr("airis_pdm.figmai.chain_remote.request_sync", fake_request_sync)
    result = run_chain_remote(
        spec_path=str(spec_path),
        output_dir=str(tmp_path / "out"),
        target="html",
        sync=True,
        state_dir=str(state_dir),
    )
    assert result["success"] is True
    assert result["target_node_id"] == "10:10"
    # 驗證先走 updateNode，不會重建 root
    assert calls[0][0] == "updateNode"


def test_chain_remote_missing_node_orphan_strategy(tmp_path: Path, monkeypatch):
    spec = {"name": "Auth", "id": "root-1", "sections": []}
    spec_path = tmp_path / "spec.json"
    spec_path.write_text(json.dumps(spec), encoding="utf-8")
    state_dir = tmp_path / "state"
    state_dir.mkdir(parents=True, exist_ok=True)
    (state_dir / "state.json").write_text(
        json.dumps(
            {
                "nodes": {"root-1": "10:10", "removed-1": "11:11"},
                "orphans": {},
                "lastSync": "2026-01-01T00:00:00Z",
            }
        ),
        encoding="utf-8",
    )

    def fake_request_sync(method, params=None, **kwargs):
        if method == "updateNode":
            return True
        if method == "getNode":
            return {
                "id": "10:10",
                "name": "UpdatedRoot",
                "type": "FRAME",
                "visible": True,
                "absoluteBoundingBox": {"x": 0, "y": 0, "width": 300, "height": 600},
                "children": [],
            }
        raise AssertionError(f"unexpected method {method}")

    monkeypatch.setattr("airis_pdm.figmai.chain_remote.request_sync", fake_request_sync)
    result = run_chain_remote(
        spec_path=str(spec_path),
        output_dir=str(tmp_path / "out"),
        target="html",
        sync=True,
        state_dir=str(state_dir),
        missing_node_strategy="orphan",
    )
    assert result["orphaned_count"] == 1
    saved = json.loads((state_dir / "state.json").read_text(encoding="utf-8"))
    assert "removed-1" not in saved["nodes"]
    assert saved["orphans"]["removed-1"] == "11:11"


def test_chain_remote_missing_node_delete_strategy(tmp_path: Path, monkeypatch):
    spec = {"name": "Auth", "id": "root-1", "sections": []}
    spec_path = tmp_path / "spec.json"
    spec_path.write_text(json.dumps(spec), encoding="utf-8")
    state_dir = tmp_path / "state"
    state_dir.mkdir(parents=True, exist_ok=True)
    (state_dir / "state.json").write_text(
        json.dumps({"nodes": {"root-1": "10:10", "removed-1": "11:11"}, "orphans": {}, "lastSync": ""}),
        encoding="utf-8",
    )
    calls = []

    def fake_request_sync(method, params=None, **kwargs):
        calls.append((method, params or {}))
        if method == "updateNode":
            return True
        if method == "deleteNode":
            return True
        if method == "getNode":
            return {
                "id": "10:10",
                "name": "UpdatedRoot",
                "type": "FRAME",
                "visible": True,
                "absoluteBoundingBox": {"x": 0, "y": 0, "width": 300, "height": 600},
                "children": [],
            }
        raise AssertionError(f"unexpected method {method}")

    monkeypatch.setattr("airis_pdm.figmai.chain_remote.request_sync", fake_request_sync)
    result = run_chain_remote(
        spec_path=str(spec_path),
        output_dir=str(tmp_path / "out"),
        target="html",
        sync=True,
        state_dir=str(state_dir),
        missing_node_strategy="delete",
    )
    assert result["deleted_count"] == 1
    assert any(m == "deleteNode" for m, _ in calls)


def test_chain_remote_parent_drift_move_node(tmp_path: Path, monkeypatch):
    spec = {
        "name": "Auth",
        "id": "root-1",
        "sections": [
            {"id": "parent-1", "type": "card", "name": "P"},
            {"id": "child-1", "type": "text", "name": "C"},
        ],
    }
    spec_path = tmp_path / "spec.json"
    spec_path.write_text(json.dumps(spec), encoding="utf-8")
    state_dir = tmp_path / "state"
    state_dir.mkdir(parents=True, exist_ok=True)
    (state_dir / "state.json").write_text(
        json.dumps(
            {
                "nodes": {
                    "root-1": "10:10",
                    "parent-1": "20:20",
                    "child-1": "30:30",
                },
                "orphans": {},
                "lastSync": "",
            }
        ),
        encoding="utf-8",
    )
    calls = []

    def fake_request_sync(method, params=None, **kwargs):
        params = params or {}
        calls.append((method, params))
        if method == "updateNode":
            return True
        if method == "getNode":
            # child-1 故意回報錯誤 parent，觸發 moveNode
            if params.get("nodeId") == "30:30":
                return {"id": "30:30", "parentId": "999:999", "type": "TEXT", "name": "C"}
            return {"id": params.get("nodeId"), "parentId": "10:10", "type": "FRAME", "name": "N"}
        if method == "moveNode":
            return True
        raise AssertionError(f"unexpected method {method}")

    monkeypatch.setattr("airis_pdm.figmai.chain_remote.request_sync", fake_request_sync)
    run_chain_remote(
        spec_path=str(spec_path),
        output_dir=str(tmp_path / "out"),
        target="html",
        sync=True,
        state_dir=str(state_dir),
        missing_node_strategy="keep",
    )
    assert any(m == "moveNode" and p.get("nodeId") == "30:30" for m, p in calls)


def test_chain_remote_sibling_index_drift_move_node_with_index(tmp_path: Path, monkeypatch):
    spec = {
        "name": "Auth",
        "id": "root-1",
        "sections": [
            {"id": "a", "type": "card", "name": "A"},
            {"id": "b", "type": "card", "name": "B"},
        ],
    }
    spec_path = tmp_path / "spec.json"
    spec_path.write_text(json.dumps(spec), encoding="utf-8")
    state_dir = tmp_path / "state"
    state_dir.mkdir(parents=True, exist_ok=True)
    (state_dir / "state.json").write_text(
        json.dumps(
            {
                "nodes": {"root-1": "10:10", "a": "20:20", "b": "30:30"},
                "orphans": {},
                "lastSync": "",
            }
        ),
        encoding="utf-8",
    )
    calls = []

    def fake_request_sync(method, params=None, **kwargs):
        params = params or {}
        calls.append((method, params))
        if method == "updateNode":
            return True
        if method == "getNode":
            # 節點父層都正確，但 parent children 順序是 [b, a]，應把 a 移到 index=0
            if params.get("nodeId") == "10:10" and params.get("depth") == 1:
                return {"id": "10:10", "children": [{"id": "30:30"}, {"id": "20:20"}]}
            if params.get("nodeId") in ("20:20", "30:30"):
                return {"id": params["nodeId"], "parentId": "10:10", "type": "FRAME", "name": "N"}
            return {"id": "10:10", "name": "Root", "type": "FRAME", "children": []}
        if method == "moveNode":
            return True
        raise AssertionError(f"unexpected method {method}")

    monkeypatch.setattr("airis_pdm.figmai.chain_remote.request_sync", fake_request_sync)
    run_chain_remote(
        spec_path=str(spec_path),
        output_dir=str(tmp_path / "out"),
        target="html",
        sync=True,
        state_dir=str(state_dir),
        missing_node_strategy="keep",
    )
    assert any(m == "moveNode" and p.get("nodeId") == "20:20" and p.get("index") == 0 for m, p in calls)
