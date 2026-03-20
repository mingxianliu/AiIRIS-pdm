"""
React generator skill（Python 版）。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict

from airis_pdm.generator import generate_from_ir

from ..ui_ir_to_airis import ui_ir_to_airis_ir
from .base import SkillInput, SkillOutput, normalize_ui_ir_root


@dataclass
class ReactGeneratorSkill:
    name: str = "react"

    def execute(self, input_data: SkillInput, ui_ir_root: Dict[str, Any]) -> SkillOutput:
        ui_ir_root = normalize_ui_ir_root(ui_ir_root)
        ir = ui_ir_to_airis_ir(ui_ir_root)
        out = generate_from_ir(ir, target="react", output_dir="./generated/skill-react")
        markdown = (
            f"# {ui_ir_root.get('name', 'Component')} — React Component\n"
            f"Generated files: {', '.join(out.get('files', []))}\n"
        )
        return SkillOutput(spec={"react": {"files": out.get("files", [])}}, markdown=markdown)
