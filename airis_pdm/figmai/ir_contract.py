"""
IR contract 驗證與 auto-fix（Python 版）。
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Dict, List


@dataclass
class IRValidationResult:
    valid: bool
    errors: List[str]
    fixed: Dict[str, Any]


def validate_ui_ir(root: Dict[str, Any] | None) -> IRValidationResult:
    """
    驗證 UiIR 根節點並做最小必要 auto-fix。
    """
    errors: List[str] = []
    fixed = deepcopy(root) if isinstance(root, dict) else {}

    if not fixed:
        errors.append("IR root 必須存在")
        fixed = {
            "name": "Root",
            "type": "frame",
            "sourceType": "FRAME",
            "layout": {"x": 0, "y": 0, "width": 0, "height": 0},
            "children": [],
        }

    def visit(node: Dict[str, Any], is_root: bool) -> None:
        name = node.get("name")
        if not isinstance(name, str) or not name.strip():
            errors.append("IR node 缺少 name")
            node["name"] = "Unnamed"

        node_type = node.get("type")
        if not isinstance(node_type, str) or not node_type:
            errors.append(f"IR node {node.get('name','?')} 缺少 type")
            node["type"] = "frame"
            node_type = "frame"

        source_type = node.get("sourceType")
        if not isinstance(source_type, str) or not source_type:
            errors.append(f"IR node {node.get('name','?')} 缺少 sourceType")
            node["sourceType"] = "FRAME" if node_type != "text" else "TEXT"

        if is_root and str(node.get("type")).lower() == "text":
            errors.append("IR root 不能是 text，已修正為 frame")
            node["type"] = "frame"
            node["sourceType"] = "FRAME"

        layout = node.get("layout")
        if not isinstance(layout, dict):
            errors.append(f"IR node {node.get('name','?')} 缺少 layout")
            node["layout"] = {"x": 0, "y": 0, "width": 0, "height": 0}
        else:
            for k in ("x", "y", "width", "height"):
                if not isinstance(layout.get(k), (int, float)):
                    layout[k] = 0

        children = node.get("children")
        if not isinstance(children, list):
            errors.append(f"IR node {node.get('name','?')} 的 children 必須為陣列")
            node["children"] = []
            children = node["children"]

        if str(node.get("sourceType", "")).upper() == "TEXT":
            text = node.get("text")
            if not isinstance(text, dict):
                errors.append(f"IR TEXT node {node.get('name','?')} 缺少 text")
                node["text"] = {"characters": str(node.get("name", ""))}
            elif not isinstance(text.get("characters"), str):
                errors.append(f"IR TEXT node {node.get('name','?')} text.characters 非字串")
                text["characters"] = str(text.get("characters") or "")

        for child in children:
            if isinstance(child, dict):
                visit(child, False)

    visit(fixed, True)
    return IRValidationResult(valid=len(errors) == 0, errors=errors, fixed=fixed)
