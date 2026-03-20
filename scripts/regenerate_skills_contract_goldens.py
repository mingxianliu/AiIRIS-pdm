#!/usr/bin/env python3
"""
依 test_figmai_skills.py 的 ROOT_CASES／假 generate_from_ir，重新寫入：
  tests/golden/skills_leaf_contracts.json
  tests/golden/skills_aggregate_contracts.json

用途：契約測試 baseline 遺失或 skill 輸出刻意變更後，於 PR 內更新 golden。
執行：專案根目錄下  python scripts/regenerate_skills_contract_goldens.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from airis_pdm.figmai.skills import (  # noqa: E402
    AllInOneSkill,
    AnatomySkill,
    ApiSpecSkill,
    ColorAnnotationSkill,
    PropertiesSkill,
    ReactGeneratorSkill,
    ScreenReaderSkill,
    SkillInput,
    StructureSkill,
    VueGeneratorSkill,
)
import airis_pdm.figmai.skills.react_generator as react_gen  # noqa: E402
import airis_pdm.figmai.skills.vue_generator as vue_gen  # noqa: E402


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
                "children": [],
            }
        ],
    }


def _fake_generate_from_ir(ir: dict, target: str, output_dir: str) -> dict:
    assert ir["figmaType"] == "FRAME"
    assert isinstance(ir.get("children"), list)
    if ir["figmaName"] == "Badge":
        return {"files": []}
    if target == "react":
        return {"files": ["src/components/Button.tsx", "src/components/Button.css"]}
    return {"files": ["src/components/Button.vue", "src/components/Button.css"]}


def main() -> int:
    LEAF_SKILLS = {
        "anatomy": AnatomySkill,
        "api-spec": ApiSpecSkill,
        "color-annotation": ColorAnnotationSkill,
        "properties": PropertiesSkill,
        "structure": StructureSkill,
        "screen-reader": ScreenReaderSkill,
    }

    leaf: dict = {}
    for name, cls in LEAF_SKILLS.items():
        leaf[name] = {}
        for rn, fn in [("normal", _normal_root), ("edge", _edge_root)]:
            out = cls().execute(SkillInput(), fn())
            leaf[name][rn] = {"spec": out.spec, "markdown": out.markdown}

    react_gen.generate_from_ir = _fake_generate_from_ir
    vue_gen.generate_from_ir = _fake_generate_from_ir

    agg: dict = {}
    for skill_name, cls in [("react", ReactGeneratorSkill), ("vue", VueGeneratorSkill)]:
        agg[skill_name] = {}
        for rn, fn in [("normal", _normal_root), ("edge", _edge_root)]:
            out = cls().execute(SkillInput(), fn())
            agg[skill_name][rn] = {"spec": out.spec, "markdown": out.markdown}

    agg["all-in-one"] = {}
    for rn, fn in [("normal", _normal_root), ("edge", _edge_root)]:
        out = AllInOneSkill().execute(SkillInput(), fn())
        agg["all-in-one"][rn] = {
            "spec": out["spec"],
            "markdowns": out["markdowns"],
            "errors": out["errors"],
        }

    gdir = PROJECT_ROOT / "tests" / "golden"
    gdir.mkdir(parents=True, exist_ok=True)
    (gdir / "skills_leaf_contracts.json").write_text(
        json.dumps(leaf, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    (gdir / "skills_aggregate_contracts.json").write_text(
        json.dumps(agg, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print("Wrote:", gdir / "skills_leaf_contracts.json")
    print("Wrote:", gdir / "skills_aggregate_contracts.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
