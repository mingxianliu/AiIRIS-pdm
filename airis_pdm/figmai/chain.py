"""
FigmAI Chain（純 Python）核心：Pencil/UiIR -> codegen 產物。
"""

from __future__ import annotations

from typing import Any, Dict

from airis_pdm.generator import generate_from_ir

from .from_figma import figma_node_to_ui_ir
from .ir_contract import validate_ui_ir
from .ui_ir_to_airis import ui_ir_to_airis_ir


def from_pencil_node(node: Dict[str, Any]) -> Dict[str, Any]:
    """把 PencilNode 形狀節點轉成 UiIR；以既有 from_figma 規則統一輸出。"""
    # 這裡重用 figma_node_to_ui_ir 的 mapping 習慣：先轉成接近 FigmaToIR 輸入的形狀
    figma_like = {
        "type": "FRAME",
        "name": node.get("name", "Root"),
        "absoluteBoundingBox": {
            "x": 0,
            "y": 0,
            "width": node.get("width", 0) or 0,
            "height": node.get("height", 0) or 0,
        },
        "children": [],
    }
    return figma_node_to_ui_ir(figma_like)


def generate_code_artifacts(
    ui_ir_root: Dict[str, Any],
    *,
    target: str,
    output_dir: str,
    page_name: str | None = None,
    with_utility_css: bool = False,
) -> Dict[str, Any]:
    """UiIR 根節點 -> 既有生成器輸出。"""
    validation = validate_ui_ir(ui_ir_root)
    airis_ir = ui_ir_to_airis_ir(validation.fixed)
    if page_name:
        airis_ir["figmaName"] = page_name
    out = generate_from_ir(
        ir_data=airis_ir,
        target=target,
        output_dir=output_dir,
        page_name=page_name,
        with_utility_css=with_utility_css,
    )
    out["validation"] = {
        "valid": validation.valid,
        "issues": [
            {"level": "error", "code": "IR_VALIDATION_ERROR", "message": msg}
            for msg in validation.errors
        ],
    }
    return out
