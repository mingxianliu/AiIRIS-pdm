from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List

from ._utils import parse_variant_kv
from .base import SkillInput, SkillOutput, normalize_ui_ir_root


@dataclass
class PropertiesSkill:
    name: str = "properties"

    def execute(self, input_data: SkillInput, ui_ir_root: Dict[str, Any]) -> SkillOutput:
        ui_ir_root = normalize_ui_ir_root(ui_ir_root)
        kv = parse_variant_kv(ui_ir_root.get("name", ""))
        axes: List[Dict[str, Any]] = [{"name": k, "values": [kv[k]]} for k in sorted(kv.keys(), key=str)]
        toggles: List[Dict[str, Any]] = []
        markdown = f"# {ui_ir_root.get('name','Component')} — Properties\n\n- 軸數: {len(axes)}\n"
        return SkillOutput(spec={"properties": {"variantAxes": axes, "booleanToggles": toggles}}, markdown=markdown)
