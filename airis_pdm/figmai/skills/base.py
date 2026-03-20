"""
FigmAI skills base（Python）。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Protocol


@dataclass
class SkillInput:
    figma_url: str | None = None
    node_id: str | None = None
    context: str | None = None
    pencil: bool = False


@dataclass
class SkillOutput:
    spec: Dict[str, Any]
    markdown: str


class SkillContractError(ValueError):
    """Raised when a skill receives malformed UiIR input."""


def normalize_ui_ir_root(ui_ir_root: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(ui_ir_root, dict):
        raise SkillContractError("ui_ir_root must be a dict")
    normalized = dict(ui_ir_root)
    normalized.setdefault("name", "Component")
    normalized.setdefault("sourceType", "FRAME")
    normalized["children"] = _normalize_children(normalized.get("children"), path="ui_ir_root.children")
    return normalized


def _normalize_children(children: Any, path: str) -> list[Dict[str, Any]]:
    if children is None:
        return []
    if not isinstance(children, list):
        raise SkillContractError(f"{path} must be a list")
    normalized_children: list[Dict[str, Any]] = []
    for index, child in enumerate(children):
        if not isinstance(child, dict):
            raise SkillContractError(f"{path}[{index}] must be a dict")
        normalized_child = dict(child)
        normalized_child["children"] = _normalize_children(
            normalized_child.get("children"),
            path=f"{path}[{index}].children",
        )
        normalized_children.append(normalized_child)
    return normalized_children


class Skill(Protocol):
    name: str

    def execute(self, input_data: SkillInput, ui_ir_root: Dict[str, Any]) -> SkillOutput:
        ...
