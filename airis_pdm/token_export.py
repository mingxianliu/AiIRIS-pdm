"""
從 IR（figma-import-payload.json）萃取出 design tokens，產出 tokens.json 或 CSS 變數。

供 Phase 5 AI Prototype 輸入與 Phase 10 設計系統回寫使用。
"""

import json
import os
from typing import Any, Optional


def _normalize_color(c: Any) -> Optional[str]:
    """將顏色正規化為字串（支援 rgb/rgba 字串或 {r,g,b,a} 物件）。"""
    if c is None:
        return None
    if isinstance(c, str):
        return c.strip() or None
    if isinstance(c, dict):
        r = c.get("r", 0)
        g = c.get("g", 0)
        b = c.get("b", 0)
        a = c.get("a", 1)
        if isinstance(r, float) and r <= 1:
            r, g, b = int(r * 255), int(g * 255), int(b * 255)
        return f"rgba({r},{g},{b},{a})"
    return None


def _collect_tokens_from_node(node: dict, out: dict) -> None:
    """遞迴走訪 IR 節點，收集 colors / typography / spacing。"""
    # 顏色：styles.fills (SOLID)、styles.backgroundColor（舊格式）、text.color
    styles = node.get("styles") or {}
    fills = styles.get("fills") or []
    for f in fills:
        if f.get("type") == "SOLID":
            color = _normalize_color(f.get("color"))
            if color and color not in out["colors"]:
                out["colors"].append(color)
    bg = styles.get("backgroundColor")
    if isinstance(bg, str):
        bg = _normalize_color(bg)
        if bg and bg not in out["colors"]:
            out["colors"].append(bg)

    text = node.get("text")
    if text:
        color = _normalize_color(text.get("color"))
        if color and color not in out["colors"]:
            out["colors"].append(color)
        fs = text.get("fontSize")
        if fs is not None and fs not in out["typography"]["fontSizes"]:
            out["typography"]["fontSizes"].append(fs)
        ff = text.get("fontFamily")
        if ff and ff not in out["typography"]["fontFamilies"]:
            out["typography"]["fontFamilies"].append(ff)
        fw = text.get("fontWeight")
        if fw is not None and fw not in out["typography"]["fontWeights"]:
            out["typography"]["fontWeights"].append(fw)
        lh = text.get("lineHeight")
        if lh is not None and lh not in out["typography"]["lineHeights"]:
            out["typography"]["lineHeights"].append(lh)

    # 間距：autoLayout.spacing
    al = node.get("autoLayout")
    if al and "spacing" in al:
        s = al["spacing"]
        if s is not None and s not in out["spacing"]:
            out["spacing"].append(s)

    for child in node.get("children") or []:
        _collect_tokens_from_node(child, out)


def extract_tokens_from_ir(ir_doc: dict) -> dict:
    """
    從 IR 文件萃取出 design tokens（colors, typography, spacing）。
    回傳結構：{ colors: [], typography: { fontFamilies, fontSizes, fontWeights, lineHeights }, spacing: [] }
    """
    out = {
        "colors": [],
        "typography": {
            "fontFamilies": [],
            "fontSizes": [],
            "fontWeights": [],
            "lineHeights": [],
        },
        "spacing": [],
    }
    tree = ir_doc.get("tree")
    # 相容：若檔案為單一節點（無 version/tree），則整份當作根節點
    if not tree and ("children" in ir_doc or "styles" in ir_doc):
        tree = ir_doc
    if not tree:
        return out
    _collect_tokens_from_node(tree, out)
    # 排序以便輸出穩定
    out["typography"]["fontSizes"] = sorted(out["typography"]["fontSizes"])
    out["typography"]["fontWeights"] = sorted(out["typography"]["fontWeights"])
    def _line_height_key(x):
        if isinstance(x, (int, float)):
            return float(x)
        if isinstance(x, dict) and "value" in x:
            return float(x["value"])
        return 0

    out["typography"]["lineHeights"] = sorted(
        (x for x in out["typography"]["lineHeights"] if isinstance(x, (int, float)) or (isinstance(x, dict) and "value" in x)),
        key=_line_height_key,
    )
    out["spacing"] = sorted(set(out["spacing"]))
    return out


def tokens_to_css(tokens: dict, prefix: str = "--token") -> str:
    """將 tokens 轉成 CSS 變數區塊。"""
    lines = ["/* Design tokens from IR */", ":root {"]
    for i, c in enumerate(tokens.get("colors") or []):
        lines.append(f"  {prefix}-color-{i + 1}: {c};")
    for i, fs in enumerate(tokens.get("typography", {}).get("fontSizes") or []):
        lines.append(f"  {prefix}-font-size-{i + 1}: {fs}px;")
    for i, ff in enumerate(tokens.get("typography", {}).get("fontFamilies") or []):
        esc = ff.replace('"', '\\"')
        lines.append(f'  {prefix}-font-family-{i + 1}: "{esc}";')
    for i, s in enumerate(tokens.get("spacing") or []):
        lines.append(f"  {prefix}-spacing-{i + 1}: {s}px;")
    lines.append("}")
    return "\n".join(lines)


def export_tokens(
    ir_path_or_dir: str,
    output_path: str,
    format: str = "json",
    css_prefix: str = "--token",
) -> str:
    """
    從 IR 檔案或目錄（內含 figma-import-payload.json）讀取，萃出 tokens 並寫入 output_path。
    format: "json" | "css"
    回傳寫入的絕對路徑。
    """
    if os.path.isdir(ir_path_or_dir):
        ir_path = os.path.join(ir_path_or_dir, "figma-import-payload.json")
    else:
        ir_path = ir_path_or_dir
    if not os.path.isfile(ir_path):
        raise FileNotFoundError(f"IR 檔案不存在: {ir_path}")

    with open(ir_path, "r", encoding="utf-8") as f:
        ir_doc = json.load(f)

    tokens = extract_tokens_from_ir(ir_doc)
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

    if format == "css":
        content = tokens_to_css(tokens, prefix=css_prefix)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(content)
    else:
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(tokens, f, indent=2, ensure_ascii=False)

    return os.path.abspath(output_path)
