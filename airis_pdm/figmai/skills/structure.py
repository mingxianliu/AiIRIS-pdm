from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List

from ._utils import to_int
from .base import SkillInput, SkillOutput, normalize_ui_ir_root


@dataclass
class StructureSkill:
    name: str = "structure"

    def execute(self, input_data: SkillInput, ui_ir_root: Dict[str, Any]) -> SkillOutput:
        ui_ir_root = normalize_ui_ir_root(ui_ir_root)
        layout = ui_ir_root.get("layout")
        if not isinstance(layout, dict):
            layout = {}
        styles = ui_ir_root.get("styles")
        if not isinstance(styles, dict):
            styles = {}
        auto_layout = ui_ir_root.get("autoLayout")
        if not isinstance(auto_layout, dict):
            auto_layout = {}
        
        br = styles.get("borderRadius")
        br_val = to_int(br.get("topLeft")) if isinstance(br, dict) else None
        
        variant = {
            "size": "default",
            "density": "default",
            "height": to_int(layout.get("height")),
            "padding": {"top": 0, "right": 0, "bottom": 0, "left": 0},
            "spacing": to_int(auto_layout.get("spacing")),
            "borderRadius": br_val,
        }
        markdown = f"# {ui_ir_root.get('name','Component')} — Structure\n\n- 高度: {variant['height']}\n"
        return SkillOutput(spec={"structure": {"variants": [variant]}}, markdown=markdown)
