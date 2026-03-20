"""
UiIR（FigmAI 風格）↔ AiIRIS codegen 用 IR 的往返轉換。

UiIR 節點在保留扁平 style（CSS 對照）的同時，攜帶 layout / styles / text / autoLayout
等結構化欄位，確保可無損還原給 generate_from_ir。
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional


def airis_ir_to_ui_ir(airis_node: dict) -> dict:
    """將 FigmaToIR／codegen 子樹轉成 UiIR 節點（多帶一份扁平 style）。"""
    from airis_pdm.generator import _style_dict

    layout = airis_node.get("layout") or {}
    styles = airis_node.get("styles") or {}
    auto_layout = airis_node.get("autoLayout") or {}
    text = airis_node.get("text")
    figma_type = airis_node.get("figmaType") or "FRAME"

    style_flat = _style_dict(
        {
            "layout": layout,
            "styles": styles,
            "autoLayout": auto_layout,
            "text": text,
            "figmaType": figma_type,
        }
    )

    ui: dict[str, Any] = {
        "name": airis_node.get("figmaName", "Unnamed"),
        "sourceType": figma_type,
        "type": str(figma_type).lower(),
        "style": style_flat,
        "layout": layout,
        "children": [airis_ir_to_ui_ir(c) for c in airis_node.get("children") or []],
    }

    if airis_node.get("styles") is not None:
        ui["styles"] = airis_node.get("styles")
    if text is not None:
        ui["text"] = text
    if airis_node.get("autoLayout"):
        ui["autoLayout"] = airis_node["autoLayout"]

    plugin = airis_node.get("pluginData")
    if plugin is not None:
        ui["metadata"] = plugin
    if airis_node.get("metadata") is not None:
        ui["metadata"] = airis_node["metadata"]

    if airis_node.get("_layoutWarning"):
        ui["_layoutWarning"] = airis_node["_layoutWarning"]

    return ui


def ui_ir_to_airis_ir(ui_node: dict) -> dict:
    """將 UiIR 節點還原為 generate_from_ir 可用的 IR 子樹。"""
    out: Dict[str, Any] = {
        "figmaName": ui_node.get("name", "Unnamed"),
        "figmaType": ui_node.get("sourceType", "FRAME"),
        "layout": ui_node.get("layout") or {},
        "children": [ui_ir_to_airis_ir(c) for c in ui_node.get("children") or []],
    }

    styles = ui_node.get("styles")
    if styles:
        out["styles"] = styles

    text = ui_node.get("text")
    if text:
        out["text"] = text

    auto_layout = ui_node.get("autoLayout")
    if auto_layout:
        out["autoLayout"] = auto_layout

    meta = ui_node.get("metadata")
    if meta is not None:
        out["metadata"] = meta
        out["pluginData"] = meta

    if ui_node.get("_layoutWarning"):
        out["_layoutWarning"] = ui_node["_layoutWarning"]

    return out


def ui_ir_roots_to_airis_pages(ui_roots: List[dict]) -> Dict[str, Any]:
    """多頁 UiIR 根節點 → generate_from_ir 接受的 {\"pages\": [...]} 包裝。"""
    pages: list[dict] = []
    for root in ui_roots:
        if not root:
            continue
        pages.append(ui_ir_to_airis_ir(root))
    return {"pages": pages}
