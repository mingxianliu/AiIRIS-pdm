"""
ThemeManager — 設計標記 (Design Tokens) 抽象化

從 Pencil / IR 讀取全域變數或萃取的 tokens，產生 :root { --primary-color: #137333; } 等 CSS 變數，
供生成器輸出時使用變數取代硬編碼顏色與尺寸，提升可維護性並與 Tailwind/設計系統對齊。
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from .token_export import extract_tokens_from_ir, tokens_to_css
from .design_assets import extract_design_tokens_from_ir

# 語義化 token 名稱對應（顏色序號 → 常見命名）
SEMANTIC_COLOR_NAMES = ["primary", "secondary", "success", "warning", "error", "surface", "text", "text-muted"]


def _normalize_color_for_key(c: Any) -> Optional[str]:
    """將顏色正規化為可當 key 的字串（與 token_export 一致，便於對照）。"""
    if c is None:
        return None
    if isinstance(c, str):
        s = c.strip()
        if s.startswith("rgba") or s.startswith("rgb"):
            return s.lower()
        if s.startswith("#"):
            h = s[1:].strip()
            if len(h) == 3:
                h = "".join(x * 2 for x in h)
            if len(h) == 6:
                r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
                return f"rgba({r},{g},{b},1)"
            if len(h) == 8:
                r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
                a = round(int(h[6:8], 16) / 255, 2)
                return f"rgba({r},{g},{b},{a})"
            return s.lower()
        return s.lower()
    if isinstance(c, dict):
        r, g, b = c.get("r", 0), c.get("g", 0), c.get("b", 0)
        a = c.get("a", 1)
        if isinstance(r, float) and r <= 1:
            r, g, b = int(r * 255), int(g * 255), int(b * 255)
        return f"rgba({r},{g},{b},{a})"
    return None


class ThemeManager:
    """
    主題/Design Tokens 管理器。
    從 IR 或 Pencil variables 建立 CSS 變數表，並提供「數值 → var(--token)」查詢。
    """

    def __init__(self, css_prefix: str = "--token"):
        self.css_prefix = css_prefix
        self._color_to_var: Dict[str, str] = {}
        self._font_size_to_var: Dict[Any, str] = {}
        self._spacing_to_var: Dict[Any, str] = {}
        self._raw_tokens: Dict[str, Any] = {}

    def load_from_ir(self, ir_doc: dict) -> None:
        """從 IR 文件萃取出 tokens 並建立 數值 → CSS 變數 對照。"""
        self._raw_tokens = extract_tokens_from_ir(ir_doc)
        colors = self._raw_tokens.get("colors") or []
        for i, c in enumerate(colors):
            key = _normalize_color_for_key(c)
            if key is not None:
                name = SEMANTIC_COLOR_NAMES[i] if i < len(SEMANTIC_COLOR_NAMES) else f"color-{i + 1}"
                self._color_to_var[key] = f"var({self.css_prefix}-{name})"
        typo = self._raw_tokens.get("typography") or {}
        for i, fs in enumerate(typo.get("fontSizes") or []):
            self._font_size_to_var[fs] = f"var({self.css_prefix}-font-size-{i + 1})"
        for i, s in enumerate(self._raw_tokens.get("spacing") or []):
            self._spacing_to_var[s] = f"var({self.css_prefix}-spacing-{i + 1})"

    def load_from_pen_variables(self, variables: List[dict]) -> None:
        """
        從 Pencil AI 的 variables（若有）載入全域變數。
        預期格式例如 [{"name": "primaryColor", "value": "#137333"}, ...]。
        """
        for v in variables or []:
            name = v.get("name", "").replace(" ", "-").lower()
            if not name:
                continue
            val = v.get("value")
            if isinstance(val, str) and (val.startswith("#") or val.startswith("rgb")):
                key = _normalize_color_for_key(val)
                if key:
                    self._color_to_var[key] = f"var({self.css_prefix}-{name})"
                    self._raw_tokens.setdefault("colors", []).append(val)

    def resolve_color(self, color_value: str) -> str:
        """若該顏色已註冊為 token，回傳 var(--token-xxx)，否則回傳原值。"""
        key = _normalize_color_for_key(color_value)
        return self._color_to_var.get(key, color_value) if key else color_value

    def resolve_font_size(self, value: Any) -> str:
        """若該字級已註冊，回傳 var(--token-font-size-x)，否則回傳原值（含單位）。"""
        if value in self._font_size_to_var:
            return self._font_size_to_var[value]
        if isinstance(value, (int, float)):
            return f"{int(value)}px"
        return str(value)

    def resolve_spacing(self, value: Any) -> str:
        """若該間距已註冊，回傳 var(--token-spacing-x)，否則回傳原值（含單位）。"""
        if value in self._spacing_to_var:
            return self._spacing_to_var[value]
        if isinstance(value, (int, float)):
            return f"{int(value)}px"
        return str(value)

    def to_css_root(self) -> str:
        """產出 :root { ... } CSS 變數區塊。"""
        return tokens_to_css(self._raw_tokens, prefix=self.css_prefix)

    def write_css_file(self, path: str | Path) -> str:
        """將 :root 變數寫入檔案。"""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.to_css_root(), encoding="utf-8")
        return str(path.resolve())
