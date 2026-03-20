import json
from pathlib import Path

from airis_pdm.figmai import run_chain_pipeline, run_flow_via_console
from airis_pdm.figmai.renderers import render_pixel_react_component, render_pixel_vue_sfc


GOLDEN = Path(__file__).parent / "golden"


def _load(name: str):
    return json.loads((GOLDEN / name).read_text(encoding="utf-8"))


def test_golden_spec_auth_login(tmp_path: Path):
    spec = _load("spec_auth_login.json")
    spec_path = tmp_path / "spec_auth_login.json"
    spec_path.write_text(json.dumps(spec), encoding="utf-8")
    result = run_chain_pipeline(spec_path=str(spec_path), output_dir=str(tmp_path / "out"), target="html")
    html = (tmp_path / "out" / "index.html").read_text(encoding="utf-8")
    assert result["success"] is True
    assert "Welcome Back" in html
    assert "Sign In" in html


def test_golden_spec_dashboard_cards(tmp_path: Path):
    spec = _load("spec_dashboard_cards.json")
    spec_path = tmp_path / "spec_dashboard_cards.json"
    spec_path.write_text(json.dumps(spec), encoding="utf-8")
    result = run_chain_pipeline(spec_path=str(spec_path), output_dir=str(tmp_path / "out"), target="html")
    html = (tmp_path / "out" / "index.html").read_text(encoding="utf-8")
    assert result["success"] is True
    assert "Analytics Overview" in html
    assert "Revenue" in html and "Conversion" in html


def test_golden_flow_multi_page_collision(monkeypatch, tmp_path: Path):
    matches = [
        {"id": "1:1", "name": "[Page] Login", "type": "FRAME"},
        {"id": "1:2", "name": "[Page] Login", "type": "FRAME"},
        {"id": "1:3", "name": "[Page] Login", "type": "FRAME"},
    ]

    def fake_request_sync(method, params=None, **kwargs):
        params = params or {}
        if method == "searchNodes":
            return matches
        if method == "getNode":
            name = next(x["name"] for x in matches if x["id"] == params["nodeId"])
            return {
                "id": params["nodeId"],
                "name": name,
                "type": "FRAME",
                "visible": True,
                "absoluteBoundingBox": {"x": 0, "y": 0, "width": 320, "height": 640},
                "children": [],
            }
        return True

    monkeypatch.setattr("airis_pdm.figmai.flow.request_sync", fake_request_sync)
    m = run_flow_via_console(
        output_dir=str(tmp_path / "flow"),
        pattern="[Page]",
        framework="vue",
        fidelity="semantic",
    )
    slugs = [p["slug"] for p in m["pages"]]
    assert slugs == ["login", "login-2", "login-3"]


def test_golden_flow_include_exclude(monkeypatch, tmp_path: Path):
    matches = [
        {"id": "2:1", "name": "[Page] Login", "type": "FRAME"},
        {"id": "2:2", "name": "[Page] Register", "type": "FRAME"},
        {"id": "2:3", "name": "[Page] DraftLogin", "type": "FRAME"},
    ]

    def fake_request_sync(method, params=None, **kwargs):
        params = params or {}
        if method == "searchNodes":
            return matches
        if method == "getNode":
            name = next(x["name"] for x in matches if x["id"] == params["nodeId"])
            return {
                "id": params["nodeId"],
                "name": name,
                "type": "FRAME",
                "visible": True,
                "absoluteBoundingBox": {"x": 0, "y": 0, "width": 320, "height": 640},
                "children": [],
            }
        return True

    monkeypatch.setattr("airis_pdm.figmai.flow.request_sync", fake_request_sync)
    m = run_flow_via_console(
        output_dir=str(tmp_path / "flow"),
        pattern="[Page]",
        include=["login"],
        exclude=["draft"],
        framework="vue",
        fidelity="semantic",
    )
    assert m["counts"]["generated"] == 1
    assert m["pages"][0]["displayName"] == "Login"


def test_golden_pixel_gradient_shadow():
    node = _load("pixel_gradient_shadow_node.json")
    react = render_pixel_react_component(node)
    vue = render_pixel_vue_sfc(node)
    assert "linear-gradient(" in react["css"]
    assert "box-shadow:" in react["css"]
    assert "linear-gradient(" in vue


def test_golden_pixel_text_typography():
    node = _load("pixel_text_typography_node.json")
    react = render_pixel_react_component(node)
    vue = render_pixel_vue_sfc(node)
    assert "font-size: 30px;" in react["css"]
    assert "font-style: italic;" in react["css"]
    assert "letter-spacing: 0.5px;" in react["css"]
    assert "color:rgba(" in react["css"].replace(" ", "")
    assert "color:rgba(" in vue.replace(" ", "")
    assert "Golden Typography" in react["tsx"]
    assert "Golden Typography" in vue
