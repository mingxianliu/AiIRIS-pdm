from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List

from ._utils import walk_ui_ir
from .base import SkillInput, SkillOutput, normalize_ui_ir_root


@dataclass
class ColorAnnotationSkill:
    name: str = "color-annotation"

    def execute(self, input_data: SkillInput, ui_ir_root: Dict[str, Any]) -> SkillOutput:
        ui_ir_root = normalize_ui_ir_root(ui_ir_root)
        elements: List[Dict[str, Any]] = []
        for n in walk_ui_ir(ui_ir_root):
            styles = n.get("styles")
            if not isinstance(styles, dict):
                styles = {}
            if styles.get("backgroundColor"):
                elements.append(
                    {
                        "layerName": n.get("name", "Layer"),
                        "property": "backgroundColor",
                        "states": [
                            {
                                "state": "default",
                                "tokenName": "(no token)",
                                "resolvedValue": styles["backgroundColor"],
                            }
                        ],
                    }
                )
        markdown = f"# {ui_ir_root.get('name','Component')} — Color Annotation\n\n- 色彩元素: {len(elements)}\n"
        return SkillOutput(spec={"colorAnnotation": {"elements": elements}}, markdown=markdown)
