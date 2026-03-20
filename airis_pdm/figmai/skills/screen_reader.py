from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict

from ._utils import collect_texts
from .base import SkillInput, SkillOutput, normalize_ui_ir_root


@dataclass
class ScreenReaderSkill:
    name: str = "screen-reader"

    def execute(self, input_data: SkillInput, ui_ir_root: Dict[str, Any]) -> SkillOutput:
        ui_ir_root = normalize_ui_ir_root(ui_ir_root)
        label = (collect_texts(ui_ir_root) or [ui_ir_root.get("name", "Component")])[0]
        spec = {
            "screenReader": {
                "platforms": {
                    "voiceover": {"role": "UIView", "label": label, "traits": [], "actions": ["activate"]},
                    "talkback": {"role": "android.view.View", "label": label, "traits": [], "actions": ["click"]},
                    "aria": {"role": "generic", "label": label, "traits": [], "actions": ["click", "keypress"]},
                }
            }
        }
        markdown = f"# {ui_ir_root.get('name','Component')} — Screen Reader\n\n- Label: {label}\n"
        return SkillOutput(spec=spec, markdown=markdown)
