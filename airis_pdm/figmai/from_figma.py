"""
Figma REST API 節點／檔案 JSON → UiIR。

實作上先經 FigmaToIR 取得與 AiIRIS 完全一致的結構化 IR，再套上 UiIR 包裝（扁平 style）。
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Union

from airis_pdm.figma_reader import FigmaToIR

from .ui_ir_to_airis import airis_ir_to_ui_ir


def figma_node_to_ui_ir(
    figma_node: dict,
    *,
    plugin_namespace: str = "figma-code-sync",
) -> dict:
    """單一 Figma 節點字典（例如 FRAME／TEXT）→ UiIR 子樹。"""
    converter = FigmaToIR(plugin_namespace=plugin_namespace)
    airis = converter.convert(figma_node)
    return airis_ir_to_ui_ir(airis)


def select_figma_canvas(
    file_payload: dict,
    *,
    page_index: int = 0,
    page_name: Optional[str] = None,
) -> dict:
    """從 `GET /v1/files/:key` 回應中選出某頁（Canvas 節點）。"""
    doc = file_payload.get("document")
    if not doc or not isinstance(doc, dict):
        raise ValueError("JSON 缺少 document 或型別不正確（預期為 Figma file API 回應）。")

    canvases: List[dict] = doc.get("children") or []
    if not canvases:
        raise ValueError("document 底下沒有任何頁面（Canvas）。")

    if page_name:
        for c in canvases:
            if c.get("name") == page_name:
                return c
        names = [c.get("name") for c in canvases]
        raise ValueError(f"找不到名為 {page_name!r} 的頁面。可用頁面：{names}")

    if page_index < 0 or page_index >= len(canvases):
        raise ValueError(f"page_index={page_index} 超出範圍（0..{len(canvases) - 1}）。")
    return canvases[page_index]


def figma_api_file_to_ui_ir_document(
    file_payload: dict,
    *,
    page_index: int = 0,
    page_name: Optional[str] = None,
    plugin_namespace: str = "figma-code-sync",
) -> dict:
    """整份 file JSON → 帶註冊格式的 UiIR 文件（含 format / version / tree）。"""
    canvas = select_figma_canvas(
        file_payload, page_index=page_index, page_name=page_name
    )
    tree = figma_node_to_ui_ir(canvas, plugin_namespace=plugin_namespace)
    return {
        "format": "aipdm-ui-ir",
        "version": 1,
        "page": canvas.get("name") or "Page",
        "tree": tree,
    }


def load_ui_ir_tree_from_file_payload(data: Union[str, dict]) -> dict:
    """由檔案讀入的 JSON dict、或已載入的 dict，取得 UiIR 根節點。"""
    if isinstance(data, str):
        raise TypeError("請傳入已 parse 的 dict；路徑請在呼叫處讀檔。")

    if data.get("format") == "aipdm-ui-ir" and "tree" in data:
        return data["tree"]

    if "tree" in data and isinstance(data["tree"], dict):
        return data["tree"]

    if all(k in data for k in ("name", "sourceType", "layout")):
        return data

    raise ValueError("無法辨識 UiIR 格式：預期含 format=aipdm-ui-ir+tree，或直接為 UiIR 根節點。")
