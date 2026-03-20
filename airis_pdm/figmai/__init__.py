"""
FigmAI 對齊層（純 Python）：Figma JSON → UiIR → AiIRIS IR → codegen。

- **UiIR**：與舊 FigmAI 類似，節點含 `name` / `sourceType` / `style`（扁平 CSS）及結構化欄位。
- **與 FigmaToIR**：底層轉換沿用 `airis_pdm.figma_reader.FigmaToIR`，避免兩套語意分叉。
"""

from .from_figma import (
    figma_api_file_to_ui_ir_document,
    figma_node_to_ui_ir,
    load_ui_ir_tree_from_file_payload,
    select_figma_canvas,
)
from .flow import run_flow_from_file_json, run_flow_via_console
from .chain_remote import run_chain_remote
from .state_store import StateStore
from .chain_pipeline import run_chain_pipeline
from .ir_contract import IRValidationResult, validate_ui_ir
from .spec_to_design_ops import spec_to_design_ops
from .renderers import render_pixel_react_component, render_pixel_vue_sfc
from .skills import (
    AllInOneSkill,
    AnatomySkill,
    ApiSpecSkill,
    ColorAnnotationSkill,
    PropertiesSkill,
    ReactGeneratorSkill,
    ScreenReaderSkill,
    SkillInput,
    SkillOutput,
    StructureSkill,
    VueGeneratorSkill,
)
from .style_schema import compute_inline_style_map
from .ui_ir_to_airis import (
    airis_ir_to_ui_ir,
    ui_ir_roots_to_airis_pages,
    ui_ir_to_airis_ir,
)

__all__ = [
    "figma_node_to_ui_ir",
    "select_figma_canvas",
    "figma_api_file_to_ui_ir_document",
    "load_ui_ir_tree_from_file_payload",
    "airis_ir_to_ui_ir",
    "ui_ir_to_airis_ir",
    "ui_ir_roots_to_airis_pages",
    "compute_inline_style_map",
    "spec_to_design_ops",
    "run_chain_pipeline",
    "run_chain_remote",
    "validate_ui_ir",
    "IRValidationResult",
    "StateStore",
    "run_flow_from_file_json",
    "run_flow_via_console",
    "render_pixel_react_component",
    "render_pixel_vue_sfc",
    "SkillInput",
    "SkillOutput",
    "ReactGeneratorSkill",
    "VueGeneratorSkill",
    "AnatomySkill",
    "ApiSpecSkill",
    "ColorAnnotationSkill",
    "PropertiesSkill",
    "StructureSkill",
    "ScreenReaderSkill",
    "AllInOneSkill",
]
