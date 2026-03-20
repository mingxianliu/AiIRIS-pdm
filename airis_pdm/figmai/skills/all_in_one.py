from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List

from .anatomy import AnatomySkill
from .api_spec import ApiSpecSkill
from .base import SkillInput, normalize_ui_ir_root
from .color_annotation import ColorAnnotationSkill
from .properties import PropertiesSkill
from .screen_reader import ScreenReaderSkill
from .structure import StructureSkill


@dataclass
class AllInOneSkill:
    name: str = "all-in-one"

    def execute(self, input_data: SkillInput, ui_ir_root: Dict[str, Any], skip_skills: List[str] | None = None) -> Dict[str, Any]:
        ui_ir_root = normalize_ui_ir_root(ui_ir_root)
        skip = set(skip_skills or [])
        skills = [
            AnatomySkill(),
            ApiSpecSkill(),
            ColorAnnotationSkill(),
            PropertiesSkill(),
            StructureSkill(),
            ScreenReaderSkill(),
        ]
        spec: Dict[str, Any] = {"meta": {"name": ui_ir_root.get("name", "Component")}}
        markdowns: Dict[str, str] = {}
        errors: Dict[str, Dict[str, str]] = {}
        for s in skills:
            if s.name in skip:
                continue
            try:
                out = s.execute(input_data, ui_ir_root)
                spec.update(out.spec)
                markdowns[s.name] = out.markdown
            except Exception as e:  # noqa: BLE001
                errors[s.name] = {"type": type(e).__name__, "message": str(e)}
        full_md = "\n\n".join(markdowns.values())
        return {"spec": spec, "markdowns": markdowns, "errors": errors, "fullMarkdown": full_md}
