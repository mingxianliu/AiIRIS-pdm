"""
ErSlice 風格 design-assets 輔助

可選：將 push 產出對齊 ErSlice 的 design-assets 目錄結構，
並產生 erslice-manifest.json、completeness 風格 metadata。
"""

import json
import os
from datetime import datetime, timezone
from typing import Any, Optional


def write_erslice_manifest(
    output_dir: str,
    module_name: str,
    page_slug: str,
    ir_doc: dict,
    source_url: str = "",
) -> str:
    """
    在 output_dir 寫入 erslice-manifest.json（ErSlice 風格）。

    目錄結構建議：design-assets/<module>/pages/<slug>/
    或 .figma-sync/ 內子目錄。
    """
    manifest = {
        "module": module_name,
        "page": page_slug,
        "source": "airis_pdm",
        "sourceUrl": source_url,
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "framework": ir_doc.get("source", {}).get("framework", "html"),
        "viewport": ir_doc.get("viewport", {}),
        "nodeCount": _count_nodes(ir_doc.get("tree")),
    }
    path = os.path.join(output_dir, "erslice-manifest.json")
    os.makedirs(output_dir, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)
    return path


def write_completeness(
    output_dir: str,
    ir_doc: dict,
    has_screenshot: bool = True,
) -> str:
    """
    寫入 completeness.json（簡化版完整度指標，對齊 ErSlice）。
    """
    tree = ir_doc.get("tree") or {}
    node_count = _count_nodes(tree)
    has_styles = _has_any_styles(tree)
    has_text = _has_any_text(tree)

    completeness = {
        "score": min(100, (node_count * 2 + (10 if has_styles else 0) + (10 if has_text else 0) + (10 if has_screenshot else 0))),
        "nodeCount": node_count,
        "hasStyles": has_styles,
        "hasText": has_text,
        "hasScreenshot": has_screenshot,
        "generatedAt": datetime.now(timezone.utc).isoformat(),
    }
    path = os.path.join(output_dir, "completeness.json")
    os.makedirs(output_dir, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(completeness, f, indent=2, ensure_ascii=False)
    return path


def extract_design_tokens_from_ir(ir_tree: dict) -> dict:
    """
    從 IR 樹擷取簡易設計 token 索引（顏色、字級）。
    可寫入 tokens.css 或 tokens.merge.json 供 ErSlice / 設計系統使用。
    """
    tokens: dict[str, list[str]] = {"colors": [], "fontSizes": [], "fontFamilies": []}
    _collect_tokens(ir_tree, tokens)
    # 去重
    tokens["colors"] = list(dict.fromkeys(tokens["colors"]))
    tokens["fontSizes"] = list(dict.fromkeys(tokens["fontSizes"]))
    tokens["fontFamilies"] = list(dict.fromkeys(tokens["fontFamilies"]))
    return tokens


def _count_nodes(node: Optional[dict]) -> int:
    if not node:
        return 0
    n = 1
    for child in node.get("children", []):
        n += _count_nodes(child)
    return n


def _has_any_styles(node: dict) -> bool:
    if node.get("styles"):
        return True
    for child in node.get("children", []):
        if _has_any_styles(child):
            return True
    return False


def _has_any_text(node: dict) -> bool:
    if node.get("text", {}).get("characters"):
        return True
    for child in node.get("children", []):
        if _has_any_text(child):
            return True
    return False


def _collect_tokens(node: dict, tokens: dict) -> None:
    styles = node.get("styles") or {}
    if styles.get("backgroundColor"):
        tokens["colors"].append(styles["backgroundColor"])
    if styles.get("color"):
        tokens["colors"].append(styles["color"])
    text = node.get("text") or {}
    if text.get("fontSize"):
        tokens["fontSizes"].append(str(int(text["fontSize"])))
    if text.get("fontFamily"):
        tokens["fontFamilies"].append(text["fontFamily"])
    if text.get("color"):
        tokens["colors"].append(text["color"])
    for child in node.get("children", []):
        _collect_tokens(child, tokens)
