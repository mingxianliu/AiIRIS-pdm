import json
from pathlib import Path

import pytest
from airis_pdm.figmai.skills import (
    AllInOneSkill,
    AnatomySkill,
    ApiSpecSkill,
    ColorAnnotationSkill,
    PropertiesSkill,
    ScreenReaderSkill,
    SkillInput,
    StructureSkill,
)


GOLDEN = Path(__file__).parent / "golden"


def _load_fixtures():
    return json.loads((GOLDEN / "skills_fixtures.json").read_text(encoding="utf-8"))


SKILLS = [
    AnatomySkill(),
    ApiSpecSkill(),
    ColorAnnotationSkill(),
    PropertiesSkill(),
    ScreenReaderSkill(),
    StructureSkill(),
]


BOUNDARY_FIXTURES = {
    "anatomy": "anatomy_boundary",
    "api-spec": "api_spec_boundary",
    "color-annotation": "color_annotation_boundary",
    "properties": "properties_boundary",
    "screen-reader": "screen_reader_boundary",
    "structure": "structure_boundary",
}


@pytest.mark.parametrize("skill", SKILLS, ids=lambda s: s.name)
@pytest.mark.parametrize("fixture_name", ["simple_button", "complex_node", "empty_node", "malformed_node"])
def test_skill_golden(skill, fixture_name):
    fixtures = _load_fixtures()
    ui_ir = fixtures[fixture_name]
    inp = SkillInput()
    out = skill.execute(inp, ui_ir)
    
    # Golden file path: skills_{skill_name}_{fixture_name}.json
    golden_file = GOLDEN / f"skills_{skill.name}_{fixture_name}.json"
    
    # If the golden file doesn't exist, we save the result as the baseline.
    if not golden_file.exists():
        data = {"spec": out.spec, "markdown": out.markdown}
        golden_file.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    
    golden_data = json.loads(golden_file.read_text(encoding="utf-8"))
    assert out.spec == golden_data["spec"]
    assert out.markdown == golden_data["markdown"]


@pytest.mark.parametrize("skill", SKILLS, ids=lambda s: s.name)
def test_skill_boundary_golden(skill):
    fixture_name = BOUNDARY_FIXTURES.get(skill.name)
    if not fixture_name:
        pytest.skip(f"No specialized boundary fixture for {skill.name}")
        
    fixtures = _load_fixtures()
    ui_ir = fixtures[fixture_name]
    inp = SkillInput()
    out = skill.execute(inp, ui_ir)
    
    # Specialized boundary golden file path
    golden_file = GOLDEN / f"skills_{skill.name}_boundary.json"
    
    if not golden_file.exists():
        data = {"spec": out.spec, "markdown": out.markdown}
        golden_file.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        
    golden_data = json.loads(golden_file.read_text(encoding="utf-8"))
    assert out.spec == golden_data["spec"]
    assert out.markdown == golden_data["markdown"]


def test_all_in_one_golden():
    fixtures = _load_fixtures()
    ui_ir = fixtures["simple_button"]
    inp = SkillInput()
    out = AllInOneSkill().execute(inp, ui_ir)
    
    golden_file = GOLDEN / "skills_all_in_one_simple_button.json"
    if not golden_file.exists():
        golden_file.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
        
    golden_data = json.loads(golden_file.read_text(encoding="utf-8"))
    
    # Compare structure, ignore "fullMarkdown" for exact byte-level match 
    # as it's just a join of others.
    assert out["spec"] == golden_data["spec"]
    assert out["markdowns"] == golden_data["markdowns"]
    assert out["errors"] == golden_data["errors"]
