import json
from pathlib import Path

import pytest

from airis_pdm.figmai.skills import (
    AllInOneSkill,
    AnatomySkill,
    ApiSpecSkill,
    ColorAnnotationSkill,
    PropertiesSkill,
    ReactGeneratorSkill,
    ScreenReaderSkill,
    SkillContractError,
    SkillInput,
    StructureSkill,
    VueGeneratorSkill,
)


GOLDEN_DIR = Path(__file__).parent / "golden"


def _load_golden(name: str) -> dict:
    return json.loads((GOLDEN_DIR / name).read_text(encoding="utf-8"))


LEAF_GOLDEN = _load_golden("skills_leaf_contracts.json")
AGGREGATE_GOLDEN = _load_golden("skills_aggregate_contracts.json")


def _normal_root() -> dict:
    return {
        "name": "Button,Size=md,State=default",
        "sourceType": "FRAME",
        "layout": {"x": 0, "y": 0, "width": 120, "height": 40},
        "styles": {
            "backgroundColor": "#3366ff",
            "borderRadius": {
                "topLeft": 8,
                "topRight": 8,
                "bottomRight": 8,
                "bottomLeft": 8,
            },
        },
        "autoLayout": {"spacing": 12},
        "metadata": {"componentProperties": {"variant": "primary", "disabled": False}},
        "children": [
            {
                "name": "Label",
                "sourceType": "TEXT",
                "layout": {"x": 10, "y": 10, "width": 60, "height": 20},
                "text": {"characters": "Submit"},
                "children": [],
            }
        ],
    }


def _edge_root() -> dict:
    return {
        "name": "Badge",
        "children": [
            {
                "sourceType": "TEXT",
                "text": {},
            }
        ],
    }


ROOT_CASES = {
    "normal": _normal_root,
    "edge": _edge_root,
}


LEAF_SKILLS = {
    "anatomy": AnatomySkill,
    "api-spec": ApiSpecSkill,
    "color-annotation": ColorAnnotationSkill,
    "properties": PropertiesSkill,
    "structure": StructureSkill,
    "screen-reader": ScreenReaderSkill,
}


GENERATOR_SKILLS = {
    "react": (ReactGeneratorSkill, "airis_pdm.figmai.skills.react_generator.generate_from_ir"),
    "vue": (VueGeneratorSkill, "airis_pdm.figmai.skills.vue_generator.generate_from_ir"),
}


@pytest.mark.parametrize("skill_name", sorted(LEAF_SKILLS.keys()))
@pytest.mark.parametrize("root_name", ["normal", "edge"])
def test_leaf_skills_match_golden_contract(skill_name: str, root_name: str):
    skill = LEAF_SKILLS[skill_name]()
    out = skill.execute(SkillInput(), ROOT_CASES[root_name]())
    assert {"spec": out.spec, "markdown": out.markdown} == LEAF_GOLDEN[skill_name][root_name]


@pytest.mark.parametrize(
    "skill_cls",
    [
        AnatomySkill,
        ApiSpecSkill,
        ColorAnnotationSkill,
        PropertiesSkill,
        StructureSkill,
        ScreenReaderSkill,
        ReactGeneratorSkill,
        VueGeneratorSkill,
    ],
)
def test_leaf_and_generator_skills_raise_contract_error_for_malformed_ui_ir(skill_cls):
    with pytest.raises(SkillContractError, match="ui_ir_root.children must be a list"):
        skill_cls().execute(SkillInput(), {"name": "Broken", "children": "oops"})


def _fake_generate_from_ir(ir: dict, target: str, output_dir: str) -> dict:
    assert ir["figmaType"] == "FRAME"
    assert isinstance(ir.get("children"), list)
    if ir["figmaName"] == "Badge":
        return {"files": []}
    if target == "react":
        return {"files": ["src/components/Button.tsx", "src/components/Button.css"]}
    return {"files": ["src/components/Button.vue", "src/components/Button.css"]}


@pytest.mark.parametrize("skill_name", ["react", "vue"])
@pytest.mark.parametrize("root_name", ["normal", "edge"])
def test_generator_skills_match_golden_contract(monkeypatch, skill_name: str, root_name: str):
    skill_cls, patch_target = GENERATOR_SKILLS[skill_name]
    monkeypatch.setattr(patch_target, _fake_generate_from_ir)
    out = skill_cls().execute(SkillInput(), ROOT_CASES[root_name]())
    assert {"spec": out.spec, "markdown": out.markdown} == AGGREGATE_GOLDEN[skill_name][root_name]


@pytest.mark.parametrize("root_name", ["normal", "edge"])
def test_all_in_one_skill_matches_golden_contract(root_name: str):
    out = AllInOneSkill().execute(SkillInput(), ROOT_CASES[root_name]())
    expected = AGGREGATE_GOLDEN["all-in-one"][root_name]
    assert out["spec"] == expected["spec"]
    assert out["markdowns"] == expected["markdowns"]
    assert out["errors"] == expected["errors"]
    assert out["fullMarkdown"] == "\n\n".join(out["markdowns"].values())


def test_all_in_one_skill_raises_contract_error_for_malformed_ui_ir():
    with pytest.raises(SkillContractError, match="ui_ir_root.children must be a list"):
        AllInOneSkill().execute(SkillInput(), {"name": "Broken", "children": "oops"})


def test_all_in_one_skill_reports_child_errors(monkeypatch):
    def boom(*args, **kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr("airis_pdm.figmai.skills.all_in_one.PropertiesSkill.execute", boom)
    out = AllInOneSkill().execute(SkillInput(), _normal_root())
    assert out["errors"] == {"properties": {"type": "RuntimeError", "message": "boom"}}
    assert "anatomy" in out["markdowns"]
    assert "screen-reader" in out["markdowns"]
