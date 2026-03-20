from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List

from .base import SkillInput, SkillOutput, normalize_ui_ir_root


@dataclass
class ApiSpecSkill:
    name: str = "api-spec"

    def execute(self, input_data: SkillInput, ui_ir_root: Dict[str, Any]) -> SkillOutput:
        ui_ir_root = normalize_ui_ir_root(ui_ir_root)
        props = (ui_ir_root.get("metadata") or {}).get("componentProperties") or {}
        items: List[Dict[str, Any]] = []
        for k in sorted(props.keys(), key=str):
            v = props[k]
            kind = "boolean" if isinstance(v, bool) else "string"
            items.append(
                {
                    "name": str(k),
                    "type": kind,
                    "defaultValue": str(v),
                    "values": ["true", "false"] if kind == "boolean" else [],
                    "description": f"{k} property",
                    "isRequired": kind != "boolean",
                }
            )
        markdown = f"# {ui_ir_root.get('name','Component')} — API Spec\n\n- 屬性數: {len(items)}\n"
        return SkillOutput(spec={"api": {"properties": items}}, markdown=markdown)
