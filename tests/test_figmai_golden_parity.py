import json
from pathlib import Path

from airis_pdm.figmai import run_chain_pipeline, run_flow_via_console, validate_ui_ir


def _golden() -> dict:
    p = Path(__file__).parent / "golden" / "figmai_parity_matrix.json"
    return json.loads(p.read_text(encoding="utf-8"))


GOLDEN_FLOW_DISK = Path(__file__).parent / "golden" / "flow_disk"


def test_golden_flow_live_slug_collision(monkeypatch, tmp_path: Path):
    golden = _golden()["flow_live_slug_collision"]

    nodes = [
        {"id": "1:1", "name": "[Page] Login", "type": "FRAME"},
        {"id": "1:2", "name": "[Page] Login", "type": "FRAME"},
        {"id": "1:3", "name": "[Page] Login", "type": "FRAME"},
        {"id": "1:4", "name": "[Page] Draft", "type": "FRAME"},
    ]

    def fake_request_sync(method, params=None, **kwargs):
        params = params or {}
        if method == "searchNodes":
            return nodes
        if method == "getNode":
            return {
                "id": params["nodeId"],
                "name": next(n["name"] for n in nodes if n["id"] == params["nodeId"]),
                "type": "FRAME",
                "visible": True,
                "absoluteBoundingBox": {"x": 0, "y": 0, "width": 320, "height": 640},
                "children": [],
            }
        if method == "notify":
            return True
        raise AssertionError(f"unexpected method {method}")

    monkeypatch.setattr("airis_pdm.figmai.flow.request_sync", fake_request_sync)
    manifest = run_flow_via_console(
        output_dir=str(tmp_path / "out"),
        host="localhost",
        port=3055,
        pattern="[Page]",
        include=["login"],
        exclude=["draft"],
        framework="vue",
        fidelity="semantic",
        notify=True,
    )

    assert manifest["counts"] == golden["counts"]
    stripped_pages = [
        {
            "nodeName": p["nodeName"],
            "slug": p["slug"],
            "routePath": p["routePath"],
            "displayName": p["displayName"],
            "collisions": p["collisions"],
        }
        for p in manifest["pages"]
    ]
    assert stripped_pages == golden["pages"]


def test_golden_ir_contract_autofix():
    golden = _golden()["ir_contract_autofix"]
    root = {
        "name": "Title",
        "type": "text",
        "sourceType": "TEXT",
        "layout": {"x": 1, "y": 2, "width": 3, "height": 4},
        "children": [
            {
                "name": "Label",
                "type": "text",
                "sourceType": "TEXT",
                "layout": {"x": 0, "y": 0, "width": 10, "height": 10},
                "children": [],
                "text": {"characters": 123},
            }
        ],
        "text": {"characters": "Title"},
    }
    result = validate_ui_ir(root)
    assert result.fixed["type"] == golden["root_type"]
    assert result.fixed["sourceType"] == golden["root_source_type"]
    assert result.fixed["children"][0]["text"]["characters"] == golden["child_text_characters"]


def test_golden_flow_disk_manifest_and_router_ts_literals(monkeypatch, tmp_path: Path):
    """manifest.json 鍵序 / 巢狀排序與 router.ts(x) 字面格式與 golden 字串逐字對拍。"""
    nodes = [
        {"id": "1:1", "name": "[Page] Login", "type": "FRAME"},
        {"id": "1:2", "name": "[Page] Register", "type": "FRAME"},
    ]

    def fake_request_sync(method, params=None, **kwargs):
        params = params or {}
        if method == "searchNodes":
            return nodes
        if method == "getNode":
            name = next(x["name"] for x in nodes if x["id"] == params["nodeId"])
            return {
                "id": params["nodeId"],
                "name": name,
                "type": "FRAME",
                "visible": True,
                "absoluteBoundingBox": {"x": 0, "y": 0, "width": 320, "height": 640},
                "children": [],
            }
        raise AssertionError(f"unexpected method {method}")

    monkeypatch.setattr("airis_pdm.figmai.flow.request_sync", fake_request_sync)
    run_flow_via_console(
        output_dir=str(tmp_path / "out"),
        host="localhost",
        port=3055,
        pattern="[Page]",
        framework="both",
        fidelity="semantic",
    )
    root = tmp_path / "out" / "flow"
    got_manifest = (root / "manifest.json").read_text(encoding="utf-8")
    exp_manifest = (GOLDEN_FLOW_DISK / "manifest_live_two_pages_both.json").read_text(encoding="utf-8")
    assert got_manifest == exp_manifest
    got_vue = (root / "vue" / "router.ts").read_text(encoding="utf-8")
    exp_vue = (GOLDEN_FLOW_DISK / "router_vue_two_pages.ts").read_text(encoding="utf-8")
    assert got_vue == exp_vue
    got_react = (root / "react" / "router.tsx").read_text(encoding="utf-8")
    exp_react = (GOLDEN_FLOW_DISK / "router_react_two_pages.tsx").read_text(encoding="utf-8")
    assert got_react == exp_react


def test_flow_manifest_top_level_keys_sorted(monkeypatch, tmp_path: Path):
    """寫入磁碟的 manifest 頂層鍵應為字母序，便於與 TS 產物對 diff。"""
    nodes = [{"id": "1:1", "name": "[Page] Login", "type": "FRAME"}]

    def fake_request_sync(method, params=None, **kwargs):
        params = params or {}
        if method == "searchNodes":
            return nodes
        if method == "getNode":
            return {
                "id": params["nodeId"],
                "name": "[Page] Login",
                "type": "FRAME",
                "visible": True,
                "absoluteBoundingBox": {"x": 0, "y": 0, "width": 320, "height": 640},
                "children": [],
            }
        raise AssertionError(method)

    monkeypatch.setattr("airis_pdm.figmai.flow.request_sync", fake_request_sync)
    run_flow_via_console(
        output_dir=str(tmp_path / "out"),
        host="127.0.0.1",
        port=42,
        pattern="[Page]",
        framework="vue",
        fidelity="semantic",
        include=["zebra", "apple"],
        exclude=["banana", "citrus"],
    )
    loaded = json.loads((tmp_path / "out" / "flow" / "manifest.json").read_text(encoding="utf-8"))
    assert list(loaded.keys()) == sorted(loaded.keys())
    assert loaded["include"] == ["apple", "zebra"]
    assert loaded["exclude"] == ["banana", "citrus"]


def test_golden_chain_local_summary(tmp_path: Path):
    golden = _golden()["chain_local_summary"]
    spec = {
        "name": "GoldenAuth",
        "sections": [
            {
                "type": "form",
                "name": "LoginForm",
                "children": [{"type": "text", "name": "Title", "props": {"text": "Golden Login"}}],
            }
        ],
    }
    spec_path = tmp_path / "spec.json"
    spec_path.write_text(json.dumps(spec), encoding="utf-8")
    result = run_chain_pipeline(spec_path=str(spec_path), output_dir=str(tmp_path / "chain"), target="html")
    assert result["success"] is golden["success"]
    assert any(s["name"] == golden["must_have_stage"] and s["status"] == "completed" for s in result["stages"])
    html = (tmp_path / "chain" / "index.html").read_text(encoding="utf-8")
    assert golden["contains_text"] in html


def test_chain_local_css_serialization_stable(tmp_path: Path):
    spec = {
        "name": "StyleStable",
        "sections": [
            {
                "type": "card",
                "name": "Panel",
                "props": {
                    "fill": "#ffffff",
                    "cornerRadius": 8,
                    "padding": 12,
                },
                "children": [
                    {
                        "type": "text",
                        "name": "Title",
                        "props": {
                            "text": "Stable CSS",
                            "fontFamily": "Inter",
                            "fontWeight": 700,
                            "fontSize": 20,
                            "color": "rgb(10, 10, 10)",
                        },
                    }
                ],
            }
        ],
    }
    spec_path = tmp_path / "spec.json"
    spec_path.write_text(json.dumps(spec), encoding="utf-8")
    out1 = tmp_path / "run1"
    out2 = tmp_path / "run2"
    run_chain_pipeline(spec_path=str(spec_path), output_dir=str(out1), target="html")
    run_chain_pipeline(spec_path=str(spec_path), output_dir=str(out2), target="html")
    css1 = (out1 / "styles" / "app.css").read_text(encoding="utf-8")
    css2 = (out2 / "styles" / "app.css").read_text(encoding="utf-8")
    assert css1 == css2
