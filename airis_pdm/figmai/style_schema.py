"""
UiIR 的樣式層：將 AiIRIS 產生器使用的結構化 IR 片段轉成「扁平 CSS 屬性 → 值」對照。

此對照與 generator._style_dict 一致，供 FigmAI 風格的 UiIR 節點使用（node["style"]）。
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict

if TYPE_CHECKING:
    pass


def compute_inline_style_map(airis_fragment: dict) -> Dict[str, str]:
    """依產生器規則計算單一節點的 CSS 映射（與 StyleSheet 使用同一套邏輯）。"""
    from airis_pdm.generator import _style_dict

    # 僅傳入 _style_dict 會讀取的欄位，避免依賴完整 IR
    # 繁體中文註：盒模型與主題解析在此與 codegen 路徑一致
    dummy: dict[str, Any] = {
        "layout": airis_fragment.get("layout") or {},
        "styles": airis_fragment.get("styles") or {},
        "autoLayout": airis_fragment.get("autoLayout") or {},
        "text": airis_fragment.get("text"),
        "figmaType": airis_fragment.get("figmaType") or "FRAME",
    }
    return _style_dict(dummy)
