"""
TASK 1 — 產物級 Parity：Chain／Flow／Codegen 輸出「可對拍、可封閉」

綜合對拍測試：
- chain-local 多 target 檔案樹 + 內容穩定性
- chain-remote mock：RPC 序列、validation、state.json schema
- flow 離線 manifest 正規形
- flow live 五頁碰撞 manifest + router 字串對拍
- codegen 同一輸入兩次位元組級一致（正規化下 0 diff）
- manifest 鍵序、include/exclude 排序護欄
"""

import json
import os
from pathlib import Path

from airis_pdm.figmai import (
    run_chain_pipeline,
    run_chain_remote,
    run_flow_from_file_json,
    run_flow_via_console,
    validate_ui_ir,
)
from airis_pdm.figmai.flow import (
    _dump_flow_manifest_json,
    _flow_manifest_for_disk,
)

GOLDEN = Path(__file__).parent / "golden"
GOLDEN_FLOW_DISK = GOLDEN / "flow_disk"


def _load(name: str):
    return json.loads((GOLDEN / name).read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# A. Chain-local：多 target 檔案樹與內容穩定性
# ---------------------------------------------------------------------------


def _file_tree(root: Path) -> list[str]:
    """回傳排序後的相對路徑清單。"""
    out = []
    for dirpath, _dirs, fnames in os.walk(str(root)):
        for fn in fnames:
            out.append(os.path.relpath(os.path.join(dirpath, fn), str(root)))
    return sorted(out)


def test_chain_local_file_tree_html(tmp_path: Path):
    golden = _load("chain_local_file_trees.json")
    spec = _load("spec_auth_login.json")
    spec_path = tmp_path / "spec.json"
    spec_path.write_text(json.dumps(spec), encoding="utf-8")
    out = tmp_path / "out"
    run_chain_pipeline(spec_path=str(spec_path), output_dir=str(out), target="html")
    assert _file_tree(out) == golden["html"]


def test_chain_local_file_tree_vue(tmp_path: Path):
    golden = _load("chain_local_file_trees.json")
    spec = _load("spec_auth_login.json")
    spec_path = tmp_path / "spec.json"
    spec_path.write_text(json.dumps(spec), encoding="utf-8")
    out = tmp_path / "out"
    run_chain_pipeline(spec_path=str(spec_path), output_dir=str(out), target="vue")
    assert _file_tree(out) == golden["vue"]


def test_chain_local_file_tree_react(tmp_path: Path):
    golden = _load("chain_local_file_trees.json")
    spec = _load("spec_auth_login.json")
    spec_path = tmp_path / "spec.json"
    spec_path.write_text(json.dumps(spec), encoding="utf-8")
    out = tmp_path / "out"
    run_chain_pipeline(spec_path=str(spec_path), output_dir=str(out), target="react")
    assert _file_tree(out) == golden["react"]


def test_chain_local_multi_section_spec(tmp_path: Path):
    """大 spec（3 sections）chain-local 成功且產物含預期文字。"""
    spec = _load("spec_multi_section.json")
    spec_path = tmp_path / "spec.json"
    spec_path.write_text(json.dumps(spec), encoding="utf-8")
    result = run_chain_pipeline(spec_path=str(spec_path), output_dir=str(tmp_path / "out"), target="html")
    assert result["success"] is True
    html = (tmp_path / "out" / "index.html").read_text(encoding="utf-8")
    assert "Welcome to AiIRIS" in html
    assert "Get Started" in html
    assert "Fast" in html
    assert "Accurate" in html
    assert "2026 AiIRIS Team" in html


def test_chain_local_minimal_spec(tmp_path: Path):
    """最小 spec chain-local 成功且產物含預期文字。"""
    spec = _load("spec_minimal.json")
    spec_path = tmp_path / "spec.json"
    spec_path.write_text(json.dumps(spec), encoding="utf-8")
    result = run_chain_pipeline(spec_path=str(spec_path), output_dir=str(tmp_path / "out"), target="html")
    assert result["success"] is True
    html = (tmp_path / "out" / "index.html").read_text(encoding="utf-8")
    assert "Hello World" in html


# ---------------------------------------------------------------------------
# B. Codegen 同一輸入兩次穩定：位元組級一致
# ---------------------------------------------------------------------------


def test_codegen_html_idempotent(tmp_path: Path):
    """同一 spec 跑兩次 chain-local html，全部檔案位元組級一致。"""
    spec = _load("spec_auth_login.json")
    spec_path = tmp_path / "spec.json"
    spec_path.write_text(json.dumps(spec), encoding="utf-8")
    run1 = tmp_path / "run1"
    run2 = tmp_path / "run2"
    run_chain_pipeline(spec_path=str(spec_path), output_dir=str(run1), target="html")
    run_chain_pipeline(spec_path=str(spec_path), output_dir=str(run2), target="html")
    tree1 = _file_tree(run1)
    tree2 = _file_tree(run2)
    assert tree1 == tree2, f"File tree mismatch: {tree1} vs {tree2}"
    for rel in tree1:
        c1 = (run1 / rel).read_bytes()
        c2 = (run2 / rel).read_bytes()
        assert c1 == c2, f"Content diff in {rel}"


def test_codegen_vue_idempotent(tmp_path: Path):
    """同一 spec 跑兩次 chain-local vue，全部檔案位元組級一致。"""
    spec = _load("spec_auth_login.json")
    spec_path = tmp_path / "spec.json"
    spec_path.write_text(json.dumps(spec), encoding="utf-8")
    run1 = tmp_path / "run1"
    run2 = tmp_path / "run2"
    run_chain_pipeline(spec_path=str(spec_path), output_dir=str(run1), target="vue")
    run_chain_pipeline(spec_path=str(spec_path), output_dir=str(run2), target="vue")
    tree1 = _file_tree(run1)
    tree2 = _file_tree(run2)
    assert tree1 == tree2
    for rel in tree1:
        assert (run1 / rel).read_bytes() == (run2 / rel).read_bytes(), f"Content diff in {rel}"


def test_codegen_react_idempotent(tmp_path: Path):
    """同一 spec 跑兩次 chain-local react，全部檔案位元組級一致。"""
    spec = _load("spec_dashboard_cards.json")
    spec_path = tmp_path / "spec.json"
    spec_path.write_text(json.dumps(spec), encoding="utf-8")
    run1 = tmp_path / "run1"
    run2 = tmp_path / "run2"
    run_chain_pipeline(spec_path=str(spec_path), output_dir=str(run1), target="react")
    run_chain_pipeline(spec_path=str(spec_path), output_dir=str(run2), target="react")
    tree1 = _file_tree(run1)
    tree2 = _file_tree(run2)
    assert tree1 == tree2
    for rel in tree1:
        assert (run1 / rel).read_bytes() == (run2 / rel).read_bytes(), f"Content diff in {rel}"


def test_codegen_multi_section_idempotent(tmp_path: Path):
    """大 spec 兩次 html 產物位元組級一致。"""
    spec = _load("spec_multi_section.json")
    spec_path = tmp_path / "spec.json"
    spec_path.write_text(json.dumps(spec), encoding="utf-8")
    run1 = tmp_path / "run1"
    run2 = tmp_path / "run2"
    run_chain_pipeline(spec_path=str(spec_path), output_dir=str(run1), target="html")
    run_chain_pipeline(spec_path=str(spec_path), output_dir=str(run2), target="html")
    for rel in _file_tree(run1):
        assert (run1 / rel).read_bytes() == (run2 / rel).read_bytes(), f"Content diff in {rel}"


# ---------------------------------------------------------------------------
# C. Chain-remote mock：RPC 序列、validation、state.json schema
# ---------------------------------------------------------------------------


def _basic_figma_node(node_id="1:1", name="Root"):
    return {
        "id": node_id,
        "name": name,
        "type": "FRAME",
        "visible": True,
        "absoluteBoundingBox": {"x": 0, "y": 0, "width": 320, "height": 640},
        "children": [],
    }


def test_chain_remote_golden_pull_only(tmp_path: Path, monkeypatch):
    golden = _load("chain_remote_golden.json")["pull_only"]
    spec = {"name": "Auth", "meta": {"figmaNodeId": "1:1"}, "sections": []}
    spec_path = tmp_path / "spec.json"
    spec_path.write_text(json.dumps(spec), encoding="utf-8")
    calls = []

    def fake_rpc(method, params=None, **kw):
        calls.append(method)
        if method == "getNode":
            return _basic_figma_node()
        raise AssertionError(f"unexpected {method}")

    monkeypatch.setattr("airis_pdm.figmai.chain_remote.request_sync", fake_rpc)
    result = run_chain_remote(spec_path=str(spec_path), output_dir=str(tmp_path / "out"), target="html", sync=False)
    assert result["success"] is golden["success"]
    assert result["target_node_id"] == golden["target_node_id"]
    assert result["synced_root_id"] is None
    assert result["deleted_count"] == golden["deleted_count"]
    assert result["orphaned_count"] == golden["orphaned_count"]
    assert result["validation"]["valid"] is golden["validation_valid"]
    assert calls == golden["expected_rpc_sequence"]


def test_chain_remote_golden_sync_then_pull(tmp_path: Path, monkeypatch):
    golden = _load("chain_remote_golden.json")["sync_then_pull"]
    spec = {"name": "Auth", "sections": [{"type": "card", "name": "Login"}]}
    spec_path = tmp_path / "spec.json"
    spec_path.write_text(json.dumps(spec), encoding="utf-8")
    calls = []

    def fake_rpc(method, params=None, **kw):
        calls.append(method)
        if method == "createNode":
            return {"id": "9:9"}
        if method == "getNode":
            return _basic_figma_node("9:9", "Synced")
        raise AssertionError(f"unexpected {method}")

    monkeypatch.setattr("airis_pdm.figmai.chain_remote.request_sync", fake_rpc)
    result = run_chain_remote(spec_path=str(spec_path), output_dir=str(tmp_path / "out"), target="html", sync=True)
    assert result["success"] is golden["success"]
    assert result["synced_root_id"] is not None
    for rpc in golden["expected_rpc_includes"]:
        assert rpc in calls, f"expected {rpc} in calls"


def test_chain_remote_state_json_schema(tmp_path: Path, monkeypatch):
    """state.json 寫出後 schema 符合 golden 約定的必要鍵與型別。"""
    golden = _load("chain_remote_golden.json")["state_json_schema"]
    spec = {"name": "Auth", "sections": [{"type": "card", "name": "Login"}]}
    spec_path = tmp_path / "spec.json"
    spec_path.write_text(json.dumps(spec), encoding="utf-8")

    def fake_rpc(method, params=None, **kw):
        if method == "createNode":
            return {"id": "9:9"}
        if method == "getNode":
            return _basic_figma_node("9:9")
        raise AssertionError(method)

    monkeypatch.setattr("airis_pdm.figmai.chain_remote.request_sync", fake_rpc)
    run_chain_remote(spec_path=str(spec_path), output_dir=str(tmp_path / "out"), target="html", sync=True)
    state = json.loads((tmp_path / "out" / "state.json").read_text(encoding="utf-8"))
    for k in golden["required_keys"]:
        assert k in state, f"missing key {k}"
    assert isinstance(state["nodes"], dict)
    assert isinstance(state["orphans"], dict)
    assert isinstance(state["lastSync"], str)


def test_chain_remote_generated_files_field(tmp_path: Path, monkeypatch):
    """chain-remote result 的 generated_files 為 list。"""
    spec = {"name": "Auth", "meta": {"figmaNodeId": "1:1"}, "sections": []}
    spec_path = tmp_path / "spec.json"
    spec_path.write_text(json.dumps(spec), encoding="utf-8")

    def fake_rpc(method, params=None, **kw):
        if method == "getNode":
            return _basic_figma_node()
        raise AssertionError(method)

    monkeypatch.setattr("airis_pdm.figmai.chain_remote.request_sync", fake_rpc)
    result = run_chain_remote(spec_path=str(spec_path), output_dir=str(tmp_path / "out"), target="html", sync=False)
    assert isinstance(result["generated_files"], list)


# ---------------------------------------------------------------------------
# D. Flow 離線 manifest 正規形
# ---------------------------------------------------------------------------


def _figma_file_json(pages):
    """建構 Figma file JSON fixture。"""
    return {
        "document": {
            "children": [
                {
                    "name": "Canvas",
                    "type": "CANVAS",
                    "children": [
                        {
                            "id": p["id"],
                            "name": p["name"],
                            "type": "FRAME",
                            "visible": True,
                            "absoluteBoundingBox": {"x": i * 400, "y": 0, "width": 320, "height": 640},
                            "children": [],
                        }
                        for i, p in enumerate(pages)
                    ],
                }
            ]
        }
    }


def test_flow_offline_manifest_golden(tmp_path: Path):
    """離線 flow 的 manifest 與 golden 逐字一致。"""
    pages = [
        {"id": "1:1", "name": "[Page] Login"},
        {"id": "1:2", "name": "[Page] Register"},
    ]
    fpath = tmp_path / "figma.json"
    fpath.write_text(json.dumps(_figma_file_json(pages)), encoding="utf-8")
    run_flow_from_file_json(
        figma_file_json_path=str(fpath),
        output_dir=str(tmp_path / "out"),
        pattern="[Page]",
        framework="both",
        fidelity="semantic",
    )
    got = (tmp_path / "out" / "flow" / "manifest.json").read_text(encoding="utf-8")
    exp = (GOLDEN_FLOW_DISK / "manifest_offline_two_pages.json").read_text(encoding="utf-8")
    assert got == exp


def test_flow_offline_manifest_keys_sorted(tmp_path: Path):
    """離線 flow manifest 頂層鍵字母序。"""
    pages = [{"id": "1:1", "name": "[Page] Login"}]
    fpath = tmp_path / "figma.json"
    fpath.write_text(json.dumps(_figma_file_json(pages)), encoding="utf-8")
    run_flow_from_file_json(
        figma_file_json_path=str(fpath),
        output_dir=str(tmp_path / "out"),
        pattern="[Page]",
        framework="vue",
        fidelity="semantic",
    )
    loaded = json.loads((tmp_path / "out" / "flow" / "manifest.json").read_text(encoding="utf-8"))
    assert list(loaded.keys()) == sorted(loaded.keys())


def test_flow_offline_idempotent(tmp_path: Path):
    """離線 flow 跑兩次，manifest 位元組級一致。"""
    pages = [
        {"id": "1:1", "name": "[Page] Login"},
        {"id": "1:2", "name": "[Page] Register"},
    ]
    fpath = tmp_path / "figma.json"
    fpath.write_text(json.dumps(_figma_file_json(pages)), encoding="utf-8")
    for run_name in ("run1", "run2"):
        run_flow_from_file_json(
            figma_file_json_path=str(fpath),
            output_dir=str(tmp_path / run_name),
            pattern="[Page]",
            framework="both",
            fidelity="semantic",
        )
    m1 = (tmp_path / "run1" / "flow" / "manifest.json").read_text(encoding="utf-8")
    m2 = (tmp_path / "run2" / "flow" / "manifest.json").read_text(encoding="utf-8")
    assert m1 == m2


# ---------------------------------------------------------------------------
# E. Flow live 五頁碰撞：manifest + router 字串級對拍
# ---------------------------------------------------------------------------


def _make_five_page_fake_rpc(nodes):
    def fake_request_sync(method, params=None, **kw):
        params = params or {}
        if method == "searchNodes":
            return nodes
        if method == "getNode":
            name = next(x["name"] for x in nodes if x["id"] == params["nodeId"])
            return _basic_figma_node(params["nodeId"], name)
        raise AssertionError(f"unexpected {method}")
    return fake_request_sync


def test_flow_live_five_pages_collision_manifest(monkeypatch, tmp_path: Path):
    """五頁碰撞 live flow manifest 與 golden 逐字一致。"""
    nodes = [
        {"id": "1:1", "name": "[Page] Dashboard", "type": "FRAME"},
        {"id": "1:2", "name": "[Page] Dashboard", "type": "FRAME"},
        {"id": "1:3", "name": "[Page] Dashboard", "type": "FRAME"},
        {"id": "1:4", "name": "[Page] Dashboard", "type": "FRAME"},
        {"id": "1:5", "name": "[Page] Settings", "type": "FRAME"},
    ]
    monkeypatch.setattr("airis_pdm.figmai.flow.request_sync", _make_five_page_fake_rpc(nodes))
    run_flow_via_console(
        output_dir=str(tmp_path / "out"),
        host="localhost",
        port=3055,
        pattern="[Page]",
        framework="vue",
        fidelity="semantic",
    )
    got = (tmp_path / "out" / "flow" / "manifest.json").read_text(encoding="utf-8")
    exp = (GOLDEN_FLOW_DISK / "manifest_live_five_pages_collision.json").read_text(encoding="utf-8")
    assert got == exp


def test_flow_live_five_pages_collision_router(monkeypatch, tmp_path: Path):
    """五頁碰撞 live flow router.ts 與 golden 逐字一致。"""
    nodes = [
        {"id": "1:1", "name": "[Page] Dashboard", "type": "FRAME"},
        {"id": "1:2", "name": "[Page] Dashboard", "type": "FRAME"},
        {"id": "1:3", "name": "[Page] Dashboard", "type": "FRAME"},
        {"id": "1:4", "name": "[Page] Dashboard", "type": "FRAME"},
        {"id": "1:5", "name": "[Page] Settings", "type": "FRAME"},
    ]
    monkeypatch.setattr("airis_pdm.figmai.flow.request_sync", _make_five_page_fake_rpc(nodes))
    run_flow_via_console(
        output_dir=str(tmp_path / "out"),
        host="localhost",
        port=3055,
        pattern="[Page]",
        framework="vue",
        fidelity="semantic",
    )
    got = (tmp_path / "out" / "flow" / "vue" / "router.ts").read_text(encoding="utf-8")
    exp = (GOLDEN_FLOW_DISK / "router_vue_five_pages_collision.ts").read_text(encoding="utf-8")
    assert got == exp


def test_flow_live_five_pages_collision_router_react(monkeypatch, tmp_path: Path):
    """五頁碰撞 live flow router.tsx（React）與 golden 逐字一致。"""
    nodes = [
        {"id": "1:1", "name": "[Page] Dashboard", "type": "FRAME"},
        {"id": "1:2", "name": "[Page] Dashboard", "type": "FRAME"},
        {"id": "1:3", "name": "[Page] Dashboard", "type": "FRAME"},
        {"id": "1:4", "name": "[Page] Dashboard", "type": "FRAME"},
        {"id": "1:5", "name": "[Page] Settings", "type": "FRAME"},
    ]
    monkeypatch.setattr("airis_pdm.figmai.flow.request_sync", _make_five_page_fake_rpc(nodes))
    run_flow_via_console(
        output_dir=str(tmp_path / "out"),
        host="localhost",
        port=3055,
        pattern="[Page]",
        framework="react",
        fidelity="semantic",
    )
    got = (tmp_path / "out" / "flow" / "react" / "router.tsx").read_text(encoding="utf-8")
    exp = (GOLDEN_FLOW_DISK / "router_react_five_pages_collision.tsx").read_text(encoding="utf-8")
    assert got == exp


def test_flow_live_collision_count_matches_pages(monkeypatch, tmp_path: Path):
    """manifest.counts.collisions == 有 collisions > 0 的頁面數。"""
    nodes = [
        {"id": "1:1", "name": "[Page] Dashboard", "type": "FRAME"},
        {"id": "1:2", "name": "[Page] Dashboard", "type": "FRAME"},
        {"id": "1:3", "name": "[Page] Dashboard", "type": "FRAME"},
        {"id": "1:4", "name": "[Page] Dashboard", "type": "FRAME"},
        {"id": "1:5", "name": "[Page] Settings", "type": "FRAME"},
    ]
    monkeypatch.setattr("airis_pdm.figmai.flow.request_sync", _make_five_page_fake_rpc(nodes))
    m = run_flow_via_console(
        output_dir=str(tmp_path / "out"),
        host="localhost",
        port=3055,
        pattern="[Page]",
        framework="vue",
        fidelity="semantic",
    )
    collision_pages = [p for p in m["pages"] if p["collisions"] > 0]
    assert m["counts"]["collisions"] == len(collision_pages)


# ---------------------------------------------------------------------------
# F. Flow live 多頁 include/exclude 擴充
# ---------------------------------------------------------------------------


def test_flow_live_include_exclude_multi(monkeypatch, tmp_path: Path):
    """多關鍵字 include/exclude 篩選。"""
    nodes = [
        {"id": "3:1", "name": "[Page] Login", "type": "FRAME"},
        {"id": "3:2", "name": "[Page] Register", "type": "FRAME"},
        {"id": "3:3", "name": "[Page] Profile", "type": "FRAME"},
        {"id": "3:4", "name": "[Page] DraftSettings", "type": "FRAME"},
        {"id": "3:5", "name": "[Page] AdminPanel", "type": "FRAME"},
    ]

    def fake_rpc(method, params=None, **kw):
        params = params or {}
        if method == "searchNodes":
            return nodes
        if method == "getNode":
            name = next(x["name"] for x in nodes if x["id"] == params["nodeId"])
            return _basic_figma_node(params["nodeId"], name)
        raise AssertionError(method)

    monkeypatch.setattr("airis_pdm.figmai.flow.request_sync", fake_rpc)
    m = run_flow_via_console(
        output_dir=str(tmp_path / "out"),
        host="localhost",
        port=3055,
        pattern="[Page]",
        include=["login", "register"],
        exclude=["draft"],
        framework="vue",
        fidelity="semantic",
    )
    slugs = [p["slug"] for p in m["pages"]]
    assert "login" in slugs
    assert "register" in slugs
    assert "draft" not in "".join(slugs).lower()
    assert m["counts"]["filtered"] == 2


# ---------------------------------------------------------------------------
# G. manifest 結構護欄
# ---------------------------------------------------------------------------


def test_manifest_page_row_keys_sorted(monkeypatch, tmp_path: Path):
    """manifest 每個 page row 的鍵都是字母序。"""
    nodes = [{"id": "1:1", "name": "[Page] Login", "type": "FRAME"}]

    def fake_rpc(method, params=None, **kw):
        params = params or {}
        if method == "searchNodes":
            return nodes
        if method == "getNode":
            return _basic_figma_node()
        raise AssertionError(method)

    monkeypatch.setattr("airis_pdm.figmai.flow.request_sync", fake_rpc)
    m = run_flow_via_console(
        output_dir=str(tmp_path / "out"),
        host="localhost",
        port=3055,
        pattern="[Page]",
        framework="vue",
        fidelity="semantic",
    )
    for page in m["pages"]:
        assert list(page.keys()) == sorted(page.keys()), f"unsorted keys: {list(page.keys())}"
    for gen in m["generated"]:
        assert list(gen.keys()) == sorted(gen.keys())


def test_manifest_counts_keys_sorted(monkeypatch, tmp_path: Path):
    """manifest.counts 鍵字母序。"""
    nodes = [{"id": "1:1", "name": "[Page] Login", "type": "FRAME"}]

    def fake_rpc(method, params=None, **kw):
        if method == "searchNodes":
            return nodes
        if method == "getNode":
            return _basic_figma_node()
        raise AssertionError(method)

    monkeypatch.setattr("airis_pdm.figmai.flow.request_sync", fake_rpc)
    m = run_flow_via_console(
        output_dir=str(tmp_path / "out"),
        host="localhost",
        port=3055,
        pattern="[Page]",
        framework="vue",
        fidelity="semantic",
    )
    assert list(m["counts"].keys()) == sorted(m["counts"].keys())


def test_manifest_include_exclude_always_sorted(monkeypatch, tmp_path: Path):
    """include/exclude 寫入 manifest 前排序。"""
    nodes = [{"id": "1:1", "name": "[Page] Login", "type": "FRAME"}]

    def fake_rpc(method, params=None, **kw):
        if method == "searchNodes":
            return nodes
        if method == "getNode":
            return _basic_figma_node()
        raise AssertionError(method)

    monkeypatch.setattr("airis_pdm.figmai.flow.request_sync", fake_rpc)
    m = run_flow_via_console(
        output_dir=str(tmp_path / "out"),
        host="localhost",
        port=3055,
        pattern="[Page]",
        framework="vue",
        fidelity="semantic",
        include=["zebra", "apple", "mango"],
        exclude=["cherry", "banana"],
    )
    assert m["include"] == sorted(m["include"])
    assert m["exclude"] == sorted(m["exclude"])


# ---------------------------------------------------------------------------
# H. IR contract 護欄
# ---------------------------------------------------------------------------


def test_ir_autofix_missing_layout():
    """layout 欄位缺漏時 auto-fix 補齊。"""
    root = {
        "name": "NoLayout",
        "type": "frame",
        "sourceType": "FRAME",
        "children": [],
    }
    result = validate_ui_ir(root)
    assert "layout" in result.fixed
    assert isinstance(result.fixed["layout"], dict)


def test_ir_autofix_text_type_coercion():
    """type=text 但 sourceType 不合法時修正。"""
    root = {
        "name": "Title",
        "type": "text",
        "sourceType": "INVALID",
        "layout": {"x": 0, "y": 0, "width": 100, "height": 20},
        "text": {"characters": "Hello"},
        "children": [],
    }
    result = validate_ui_ir(root)
    assert result.fixed["sourceType"] in ("TEXT", "FRAME")


# ---------------------------------------------------------------------------
# I. CSS class/property 排序穩定性
# ---------------------------------------------------------------------------


def test_css_class_names_sorted(tmp_path: Path):
    """CSS output 中 class name 按字母序排列。"""
    spec = _load("spec_dashboard_cards.json")
    spec_path = tmp_path / "spec.json"
    spec_path.write_text(json.dumps(spec), encoding="utf-8")
    run_chain_pipeline(spec_path=str(spec_path), output_dir=str(tmp_path / "out"), target="html")
    css = (tmp_path / "out" / "styles" / "app.css").read_text(encoding="utf-8")
    # Extract class names from CSS
    import re
    classes = re.findall(r"\.([a-zA-Z0-9_-]+)\s*\{", css)
    assert classes == sorted(classes), f"CSS classes not sorted: {classes}"


def test_css_property_order_consistent(tmp_path: Path):
    """CSS 屬性順序遵循 _CSS_PROP_ORDER。"""
    spec = _load("spec_auth_login.json")
    spec_path = tmp_path / "spec.json"
    spec_path.write_text(json.dumps(spec), encoding="utf-8")
    run_chain_pipeline(spec_path=str(spec_path), output_dir=str(tmp_path / "out"), target="html")
    css = (tmp_path / "out" / "styles" / "app.css").read_text(encoding="utf-8")
    import re
    # For each CSS block, check property order matches _CSS_PROP_ORDER
    from airis_pdm.generator import _CSS_PROP_ORDER
    blocks = re.findall(r"\{([^}]+)\}", css)
    for block in blocks:
        props = re.findall(r"^\s*([a-z-]+):", block, re.MULTILINE)
        if len(props) <= 1:
            continue
        # Each pair should be in order according to _CSS_PROP_ORDER
        def sort_key(p):
            try:
                return _CSS_PROP_ORDER.index(p)
            except ValueError:
                return len(_CSS_PROP_ORDER)
        assert props == sorted(props, key=sort_key), f"CSS props not in order: {props}"
