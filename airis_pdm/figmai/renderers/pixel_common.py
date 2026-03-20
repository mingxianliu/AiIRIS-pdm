"""
Pixel renderer 共用邏輯（React / Vue 產出一致 CSS）。
涵蓋 TASK2：多層陰影、描邊、圓角、透明度鏈、圖片 fill 降級、混合模式、裁切、多層 fill。
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Tuple


def _safe_class(node_id: str) -> str:
    return "n_" + "".join(ch if ch.isalnum() or ch == "_" else "_" for ch in node_id)


def _node_box(node: Dict[str, Any]) -> Tuple[float, float, float, float]:
    box = node.get("absoluteBoundingBox") or {}
    if all(k in box for k in ("x", "y", "width", "height")):
        return float(box["x"]), float(box["y"]), float(box["width"]), float(box["height"])
    return 0.0, 0.0, 0.0, 0.0


def _node_opacity(node: Dict[str, Any]) -> float:
    v = node.get("opacity")
    if v is None:
        return 1.0
    return max(0.0, min(1.0, float(v)))


def _rgba(c: Dict[str, Any], alpha: float | None = None) -> str:
    r = round(float(c.get("r", 0)) * 255)
    g = round(float(c.get("g", 0)) * 255)
    b = round(float(c.get("b", 0)) * 255)
    if alpha is not None:
        a = max(0.0, min(1.0, float(alpha)))
    else:
        a = max(0.0, min(1.0, float(c.get("a", 1))))
    return f"rgba({r}, {g}, {b}, {a})"


def _effective_fill_alpha(color: Dict[str, Any], fill_opacity: float | None, node_opacity: float) -> float:
    """Figma：color.a × fill.opacity × node.opacity（clamp）。"""
    ca = float((color or {}).get("a", 1))
    fo = float(fill_opacity) if fill_opacity is not None else 1.0
    return max(0.0, min(1.0, ca * fo * node_opacity))


def _gradient_css(fill: Dict[str, Any], node_opacity: float = 1.0) -> str | None:
    ftype = str(fill.get("type", "")).upper()
    stops = fill.get("gradientStops") or []
    if not stops:
        return None
    parts: List[str] = []
    for s in stops:
        if not isinstance(s, dict):
            continue
        col = s.get("color") or {}
        fo = s.get("opacity")
        a_eff = _effective_fill_alpha(col, float(fo) if fo is not None else None, node_opacity)
        parts.append(
            f"{_rgba(col, a_eff)} {round(float(s.get('position', 0)) * 100, 2)}%"
        )
    if not parts:
        return None
    if ftype == "GRADIENT_RADIAL":
        return f"radial-gradient(circle, {', '.join(parts)})"
    return f"linear-gradient(135deg, {', '.join(parts)})"


def _image_background_shorthand(fill: Dict[str, Any]) -> str:
    """
    單層背景 token：可與其他層用逗號串成多層 background。
    有 imageUrl 時為 cover；否則半透明灰占位（無 URL 時不猜真實圖檔）。
    """
    url = fill.get("imageUrl")
    if isinstance(url, str) and url.strip():
        quoted = json.dumps(url.strip())
        return f"url({quoted}) center / cover no-repeat"
    return "rgba(170, 170, 170, 0.35)"


def _image_fill_background(fill: Dict[str, Any]) -> str:
    """單一 IMAGE fill 的完整 background 宣告。"""
    return f"background:{_image_background_shorthand(fill)};"


def _blend_mode_css(fill_or_node: Dict[str, Any]) -> str | None:
    raw = str(fill_or_node.get("blendMode") or "NORMAL").upper()
    if raw in ("NORMAL", "PASS_THROUGH"):
        return None
    if raw == "MULTIPLY":
        return "mix-blend-mode:multiply;"
    if raw == "SCREEN":
        return "mix-blend-mode:screen;"
    # 其餘模式不猜測，避免假一致
    return None


def _unsupported_blend_mode_warning(fill_or_node: Dict[str, Any], node_name: str) -> str | None:
    raw = str(fill_or_node.get("blendMode") or "NORMAL").upper()
    if raw in ("", "NORMAL", "PASS_THROUGH", "MULTIPLY", "SCREEN"):
        return None
    return f"figmai-pixel warning: unsupported blendMode {raw} on {node_name}"


def _box_shadows_from_effects(effects: List[Any], node_opacity: float) -> str | None:
    """合併所有可見 DROP_SHADOW（多層陰影）。"""
    parts: List[str] = []
    for e in effects or []:
        if not isinstance(e, dict):
            continue
        if str(e.get("type", "")).upper() != "DROP_SHADOW":
            continue
        if e.get("visible") is False:
            continue
        off = e.get("offset") or {}
        col = e.get("color") or {}
        eff_op = e.get("opacity")
        a_eff = _effective_fill_alpha(col, float(eff_op) if eff_op is not None else None, node_opacity)
        cstr = _rgba(col, a_eff)
        parts.append(
            f"{off.get('x', 0)}px {off.get('y', 0)}px {e.get('radius', 0)}px {e.get('spread', 0)}px {cstr}"
        )
    if not parts:
        return None
    return f"box-shadow:{', '.join(parts)};"


def _stroke_border_css(node: Dict[str, Any], node_opacity: float) -> str | None:
    strokes = node.get("strokes") or []
    sw = float(node.get("strokeWeight") or 0)
    if sw <= 0 or not strokes:
        return None
    st = strokes[0]
    if not isinstance(st, dict) or st.get("visible") is False:
        return None
    if str(st.get("type", "")).upper() != "SOLID":
        return None
    col = st.get("color") or {}
    fo = st.get("opacity")
    a_eff = _effective_fill_alpha(col, float(fo) if fo is not None else None, node_opacity)
    cstr = _rgba(col, a_eff)
    align = str(node.get("strokeAlign") or "CENTER").upper()
    # INSIDE / OUTSIDE：border 與 outline 近似（bbox 仍用 absoluteBoundingBox）
    if align == "INSIDE":
        return f"border:{sw}px solid {cstr};"
    if align == "OUTSIDE":
        return f"outline:{sw}px solid {cstr};outline-offset:0;"
    return f"border:{sw}px solid {cstr};"


def _corner_radius_css(node: Dict[str, Any]) -> str | None:
    rcr = node.get("rectangleCornerRadii")
    if isinstance(rcr, (list, tuple)) and len(rcr) >= 4:
        tl, tr, br, bl = (float(rcr[i]) for i in range(4))
        return f"border-radius:{tl}px {tr}px {br}px {bl}px;"
    cr = node.get("cornerRadius")
    if isinstance(cr, (int, float)) and cr > 0:
        return f"border-radius:{float(cr)}px;"
    return None


def _fills_background_layers(node: Dict[str, Any], fills: List[Dict[str, Any]], node_op: float) -> str | None:
    """多層 fill：Figma 底層在前，CSS 前景層在前 → reversed。"""
    layers: List[str] = []
    for fill in reversed(fills):
        if not isinstance(fill, dict) or fill.get("visible") is False:
            continue
        ftype = str(fill.get("type", "")).upper()
        if ftype == "SOLID":
            col = fill.get("color") or {}
            fo = fill.get("opacity")
            a_eff = _effective_fill_alpha(col, float(fo) if fo is not None else None, node_op)
            layers.append(_rgba(col, a_eff))
        else:
            grad = _gradient_css(fill, node_op)
            if grad:
                layers.append(grad)
            elif ftype == "IMAGE":
                layers.append(_image_background_shorthand(fill))
    if not layers:
        return None
    return f"background:{', '.join(layers)};"


def _single_fill_css(
    node: Dict[str, Any],
    fill: Dict[str, Any],
    node_op: float,
    *,
    is_text: bool,
) -> Tuple[str | None, str | None]:
    """
    回傳 (background_line_or_none, color_line_or_none)。
    TEXT + SOLID 用 color，其餘用 background / background-color。
    """
    ftype = str(fill.get("type", "")).upper()
    fo = fill.get("opacity")
    if ftype == "SOLID":
        col = fill.get("color") or {}
        a_eff = _effective_fill_alpha(col, float(fo) if fo is not None else None, node_op)
        if is_text:
            return None, f"color:{_rgba(col, a_eff)};"
        return f"background-color:{_rgba(col, a_eff)};", None
    if ftype == "IMAGE":
        return _image_fill_background(fill), None
    grad = _gradient_css(fill, node_op)
    if grad:
        return f"background:{grad};", None
    return None, None


def build_pixel_css_rule(node: Dict[str, Any], cls: str, rx: float, ry: float) -> str:
    """單一節點的一行 CSS 規則（與 class 選擇器）。"""
    x, y, w, h = _node_box(node)
    lines: List[str] = [
        f".{cls}{{position:absolute;left:{x - rx}px;top:{y - ry}px;width:{w}px;height:{h}px;box-sizing:border-box;"
    ]
    node_op = _node_opacity(node)
    is_text = str(node.get("type", "")).upper() == "TEXT"

    if node.get("visible") is False:
        lines.append("visibility:hidden;")

    if str(node.get("type", "")).upper() == "FRAME" and node.get("clipsContent") is True:
        lines.append("overflow:hidden;")

    fills = [f for f in (node.get("fills") or []) if isinstance(f, dict) and f.get("visible") is not False]
    blend_line = _blend_mode_css(fills[0]) if fills else None
    if not blend_line:
        blend_line = _blend_mode_css(node)
    if blend_line:
        lines.append(blend_line)
    if fills:
        if len(fills) == 1:
            bg, color_ln = _single_fill_css(node, fills[0], node_op, is_text=is_text)
            if bg:
                lines.append(bg)
            if color_ln:
                lines.append(color_ln)
        elif len(fills) > 1 and not is_text:
            multi = _fills_background_layers(node, fills, node_op)
            if multi:
                lines.append(multi)
        else:
            bg, color_ln = _single_fill_css(node, fills[0], node_op, is_text=is_text)
            if bg:
                lines.append(bg)
            if color_ln:
                lines.append(color_ln)

    shadows = _box_shadows_from_effects(node.get("effects") or [], node_op)
    if shadows:
        lines.append(shadows)

    stroke_css = _stroke_border_css(node, node_op)
    if stroke_css:
        lines.append(stroke_css)

    cr = _corner_radius_css(node)
    if cr:
        lines.append(cr)

    if is_text:
        if isinstance(node.get("fontSize"), (int, float)):
            lines.append(f"font-size: {node['fontSize']}px;")
        font_name = node.get("fontName") or {}
        if isinstance(font_name, dict) and font_name.get("family"):
            lines.append(f"font-family: \"{font_name.get('family')}\";")
        style = str((font_name or {}).get("style") or "").lower()
        if "bold" in style:
            lines.append("font-weight: 700;")
        if "italic" in style:
            lines.append("font-style: italic;")
        ls = node.get("letterSpacing") or {}
        if isinstance(ls, dict) and ls.get("value") is not None:
            lines.append(f"letter-spacing: {ls.get('value')}px;")
        lh = node.get("lineHeight") or {}
        if isinstance(lh, dict) and lh.get("value") is not None:
            lines.append(f"line-height: {lh.get('value')}px;")

    lines.append("}")
    return "".join(lines)


def collect_pixel_warnings(root: Dict[str, Any]) -> List[str]:
    warnings: List[str] = []

    def walk(node: Dict[str, Any]) -> None:
        node_name = str(node.get("name") or node.get("id") or "node")
        blend_warning = _unsupported_blend_mode_warning(node, node_name)
        if blend_warning:
            warnings.append(blend_warning)

        fills = [f for f in (node.get("fills") or []) if isinstance(f, dict) and f.get("visible") is not False]
        for fill in fills:
            fill_warning = _unsupported_blend_mode_warning(fill, node_name)
            if fill_warning:
                warnings.append(fill_warning)

        if str(node.get("type", "")).upper() == "TEXT" and len(fills) > 1:
            warnings.append(f"figmai-pixel warning: multi-fill TEXT uses first fill only on {node_name}")

        strokes = node.get("strokes") or []
        if strokes:
            first = strokes[0]
            if isinstance(first, dict) and str(first.get("type", "")).upper() not in ("", "SOLID"):
                warnings.append(
                    f"figmai-pixel warning: unsupported stroke type {str(first.get('type')).upper()} on {node_name}"
                )

        for child in node.get("children") or []:
            if isinstance(child, dict):
                walk(child)

    walk(root)
    return warnings


def pixel_warning_comment(warnings: List[str]) -> str:
    if not warnings:
        return ""
    unique = list(dict.fromkeys(warnings))
    lines = [f"/* {msg} */" for msg in unique]
    return "\n".join(lines) + "\n"


def pixel_root_css_rule(root: Dict[str, Any]) -> str:
    """根容器（相對定位與畫布尺寸）。"""
    _, _, rw, rh = _node_box(root)
    return f".pixel-root{{position:relative;width:{rw}px;height:{rh}px;}}"
