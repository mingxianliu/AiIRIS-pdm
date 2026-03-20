"""
Pixel renderer（React）：以絕對定位近似 Figma 幾何（CSS 與 pixel_vue 共用 pixel_common）。
"""

from __future__ import annotations

from typing import Any, Dict, List

from .pixel_common import (
    _node_box,
    _safe_class,
    build_pixel_css_rule,
    collect_pixel_warnings,
    pixel_root_css_rule,
    pixel_warning_comment,
)


def render_pixel_react_component(root: Dict[str, Any]) -> Dict[str, str]:
    """輸出 {tsx, css}。"""
    rx, ry, _, _ = _node_box(root)
    warnings = collect_pixel_warnings(root)
    css_parts: List[str] = [pixel_warning_comment(warnings) + pixel_root_css_rule(root)]

    def walk(node: Dict[str, Any]) -> str:
        nid = str(node.get("id") or node.get("name") or "node")
        cls = _safe_class(nid)
        css_parts.append(build_pixel_css_rule(node, cls, rx, ry))
        children = "".join(walk(c) for c in (node.get("children") or []))
        if str(node.get("type", "")).upper() == "TEXT":
            txt = str(node.get("characters") or "")
            return f"<span className=\"{cls}\">{txt}</span>"
        return f"<div className=\"{cls}\">{children}</div>"

    body = walk(root)
    tsx = (
        "import React from 'react';\n"
        "import './Component.css';\n\n"
        "export default function Component() {\n"
        "  return (\n"
        "    <div className=\"pixel-root\">"
        + body
        + "</div>\n"
        "  );\n"
        "}\n"
    )
    return {"tsx": tsx, "css": "\n".join(css_parts) + "\n", "warnings": warnings}
