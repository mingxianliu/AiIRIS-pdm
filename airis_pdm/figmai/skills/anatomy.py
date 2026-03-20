from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List

from ._utils import to_int, walk_ui_ir
from .base import SkillInput, SkillOutput, normalize_ui_ir_root


@dataclass
class AnatomySkill:
    name: str = "anatomy"

    def execute(self, input_data: SkillInput, ui_ir_root: Dict[str, Any]) -> SkillOutput:
        ui_ir_root = normalize_ui_ir_root(ui_ir_root)
        layers: List[Dict[str, Any]] = []
        idx = 1
        for n in walk_ui_ir(ui_ir_root):
            if n is ui_ir_root:
                continue
            layout = n.get("layout")
            if not isinstance(layout, dict):
                layout = {}
            layers.append(
                {
                    "index": idx,
                    "name": n.get("name", f"Layer{idx}"),
                    "type": n.get("sourceType", "FRAME"),
                    "x": to_int(layout.get("x")),
                    "y": to_int(layout.get("y")),
                    "isOptional": False,
                    "description": "文字圖層" if n.get("sourceType") == "TEXT" else "結構圖層",
                }
            )
            idx += 1
        markdown = (
            f"# {ui_ir_root.get('name','Component')} — Anatomy\n\n"
            f"- 圖層數: {len(layers)}\n"
        )
        return SkillOutput(spec={"anatomy": {"layers": layers}}, markdown=markdown)
