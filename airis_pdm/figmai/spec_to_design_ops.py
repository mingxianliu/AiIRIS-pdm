"""
Spec -> DesignOps（PencilNode 形狀）轉換。
"""

from __future__ import annotations

from typing import Any, Dict, List


def spec_to_design_ops(spec: Dict[str, Any]) -> Dict[str, Any]:
    """將 component spec 轉為 PencilNode 風格樹。"""

    def _convert_section(section: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "id": section.get("id"),
            "type": section.get("type", "frame"),
            "name": section.get("name") or section.get("title") or section.get("type", "section"),
            "props": section.get("props") or {},
            "children": [_convert_section(c) for c in (section.get("children") or [])],
        }

    root_sections: List[Dict[str, Any]] = spec.get("sections") or []
    return {
        "id": spec.get("id"),
        "type": "component",
        "name": spec.get("name", "Component"),
        "props": spec.get("props") or {},
        "children": [_convert_section(sec) for sec in root_sections],
    }
