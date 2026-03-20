"""
TASK2：pixel renderer 進階屬性 golden／回歸（React／Vue 共用 pixel_common）。
"""

from __future__ import annotations

import json
from pathlib import Path

from airis_pdm.figmai.renderers import render_pixel_react_component, render_pixel_vue_sfc

GOLDEN = Path(__file__).parent / "golden"


def _load(name: str) -> dict:
    return json.loads((GOLDEN / name).read_text(encoding="utf-8"))


def _norm(css: str) -> str:
    return css.replace(" ", "")


def test_golden_pixel_multi_shadow():
    node = _load("pixel_multi_shadow_node.json")
    react = render_pixel_react_component(node)
    vue = render_pixel_vue_sfc(node)
    rc = _norm(react["css"])
    assert "box-shadow:" in rc
    assert "2px2px4px0px" in rc and "0px12px8px1px" in rc
    assert rc.count("rgba(") >= 2
    assert "box-shadow:" in _norm(vue)


def test_golden_pixel_stroke_corner_opacity_chain():
    node = _load("pixel_stroke_corner_node.json")
    react = render_pixel_react_component(node)
    vue = render_pixel_vue_sfc(node)
    rc = _norm(react["css"])
    assert "border:2pxsolid" in rc or "border:2.0pxsolid" in rc
    assert "border-radius:12" in rc
    assert "background-color:rgba(" in rc
    assert "0.855" in react["css"] or "242" in react["css"]
    assert "border-radius:12" in _norm(vue)


def test_golden_pixel_multi_fill_layers():
    node = _load("pixel_multi_fill_node.json")
    react = render_pixel_react_component(node)
    vue = render_pixel_vue_sfc(node)
    rc = _norm(react["css"])
    assert "background:linear-gradient" in rc
    assert "),rgba(" in rc or "),rgba(230" in rc
    assert "linear-gradient" in _norm(vue)


def test_golden_pixel_image_fill_url_or_placeholder():
    node = _load("pixel_image_fill_node.json")
    react = render_pixel_react_component(node)
    vue = render_pixel_vue_sfc(node)
    assert "example.com/placeholder.png" in react["css"]
    assert "url(" in react["css"]
    assert "cover" in _norm(react["css"]).lower() or "no-repeat" in _norm(react["css"]).lower()
    assert "example.com" in vue


def test_golden_pixel_blend_clip_visibility_corner_radii():
    node = _load("pixel_blend_clip_node.json")
    react = render_pixel_react_component(node)
    vue = render_pixel_vue_sfc(node)
    rc = _norm(react["css"])
    assert "overflow:hidden" in rc
    assert "mix-blend-mode:multiply" in rc
    assert "visibility:hidden" in rc
    assert "border-radius:8" in rc and "0.0px0.0px" in rc
    assert "mix-blend-mode:multiply" in _norm(vue)


def test_pixel_stroke_outside_uses_outline():
    node = {
        "id": "o:1",
        "name": "Outside",
        "type": "FRAME",
        "visible": True,
        "absoluteBoundingBox": {"x": 0, "y": 0, "width": 50, "height": 50},
        "fills": [{"type": "SOLID", "color": {"r": 1, "g": 1, "b": 1, "a": 1}}],
        "strokes": [{"type": "SOLID", "visible": True, "color": {"r": 0, "g": 0, "b": 0, "a": 1}}],
        "strokeWeight": 3,
        "strokeAlign": "OUTSIDE",
        "children": [],
    }
    css = _norm(render_pixel_react_component(node)["css"])
    assert "outline:3pxsolid" in css or "outline:3.0pxsolid" in css


def test_pixel_unsupported_features_emit_warning_comment():
    node = {
        "id": "warn:1",
        "name": "WarnNode",
        "type": "TEXT",
        "visible": True,
        "absoluteBoundingBox": {"x": 0, "y": 0, "width": 50, "height": 20},
        "characters": "Hello",
        "fills": [
            {"type": "SOLID", "visible": True, "color": {"r": 0, "g": 0, "b": 0, "a": 1}},
            {"type": "SOLID", "visible": True, "color": {"r": 1, "g": 0, "b": 0, "a": 1}},
        ],
        "blendMode": "OVERLAY",
        "strokes": [{"type": "GRADIENT_LINEAR", "visible": True}],
        "strokeWeight": 1,
        "children": [],
    }
    react = render_pixel_react_component(node)
    vue = render_pixel_vue_sfc(node)
    assert "unsupported blendMode OVERLAY" in react["css"]
    assert "multi-fill TEXT uses first fill only" in react["css"]
    assert "unsupported stroke type GRADIENT_LINEAR" in react["css"]
    assert "unsupported blendMode OVERLAY" in vue
