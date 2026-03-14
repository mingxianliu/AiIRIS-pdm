"""
Pencil Reader — .pen → IR v2.0 轉換器

將 Pencil AI 的節點結構轉換為 AiIRIS-pdm 的 IR 中間表示格式，
使後續可直接用 generator.py 產生 React/Vue/HTML/Flutter 程式碼。

用法：
    from airis_pdm.pencil_reader import PencilToIR

    # pen_data 來自 Pencil MCP batch_get 回傳
    converter = PencilToIR()
    ir_doc = converter.convert(pen_data)
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any, Optional


class PencilToIR:
    """將 Pencil AI (.pen) 節點資料轉為 IR v2.0 格式。

    支援的 .pen 節點類型：
        frame      → FRAME / AUTO_LAYOUT
        text       → TEXT
        icon_font  → TEXT（icon）
        rectangle  → FRAME（視覺裝飾）
        ref        → INSTANCE（組件實例）
    """

    def __init__(self, page_name: str = "Page") -> None:
        self._page_name = page_name
        self._node_count = 0

    def convert(self, pen_nodes: list[dict] | dict) -> dict:
        """主入口：將 batch_get 的回傳轉為完整 IR 文件。

        Args:
            pen_nodes: 單一節點 dict 或節點列表（batch_get 回傳格式）。

        Returns:
            IR v2.0 頂層文件結構。
        """
        self._node_count = 0

        if isinstance(pen_nodes, dict):
            pen_nodes = [pen_nodes]

        # 若只有一個根節點，直接轉換
        if len(pen_nodes) == 1:
            tree = self._convert_node(pen_nodes[0])
        else:
            # 多個根節點包裝成頁面
            children = [self._convert_node(n) for n in pen_nodes]
            children = [c for c in children if c is not None]
            tree = {
                "figmaName": self._page_name,
                "figmaType": "FRAME",
                "layout": {"x": 0, "y": 0, "width": 1440, "height": 900},
                "children": children,
            }
            self._node_count += 1

        return {
            "version": "2.0.0",
            "source": {
                "framework": "pencil",
                "entryFile": "",
                "styleStrategy": "css-modules",
                "generatedAt": datetime.now(timezone.utc).isoformat(),
                "tool": "pencil-ai",
            },
            "viewport": self._detect_viewport(tree),
            "nameMapping": {},
            "stats": {"nodeCount": self._node_count},
            "tree": tree,
        }

    def convert_node_only(self, pen_node: dict) -> Optional[dict]:
        """只轉換單一節點（不含頂層 IR 包裝），用於局部更新。"""
        self._node_count = 0
        return self._convert_node(pen_node)

    # ──────────────────────────────────────────────
    # 節點轉換（遞迴）
    # ──────────────────────────────────────────────

    def _convert_node(self, node: dict) -> Optional[dict]:
        if not node or not isinstance(node, dict):
            return None

        self._node_count += 1
        node_type = node.get("type", "frame")

        if node_type == "text":
            return self._convert_text(node)
        if node_type == "icon_font":
            return self._convert_icon(node)
        if node_type == "rectangle":
            return self._convert_rectangle(node)
        if node_type == "ref":
            return self._convert_ref(node)
        # frame 或未知類型
        return self._convert_frame(node)

    def _convert_frame(self, node: dict) -> dict:
        """frame → FRAME / AUTO_LAYOUT"""
        has_layout = self._has_auto_layout(node)
        figma_type = "AUTO_LAYOUT" if has_layout else "FRAME"

        result: dict[str, Any] = {
            "figmaName": node.get("name", "Frame"),
            "figmaType": figma_type,
            "layout": self._extract_layout(node),
        }

        auto_layout = self._extract_auto_layout(node)
        if auto_layout:
            result["autoLayout"] = auto_layout

        styles = self._extract_styles(node)
        if styles:
            result["styles"] = styles

        if node.get("clip"):
            result["clipsContent"] = True

        # 遞迴處理子節點
        children_raw = node.get("children")
        if children_raw == "...":
            # batch_get 未展開，標記需要深層讀取
            result["children"] = []
        elif isinstance(children_raw, list):
            children = [self._convert_node(c) for c in children_raw]
            result["children"] = [c for c in children if c is not None]

        return result

    def _convert_text(self, node: dict) -> dict:
        """text → TEXT"""
        result: dict[str, Any] = {
            "figmaName": node.get("name", "Text"),
            "figmaType": "TEXT",
            "layout": self._extract_layout(node),
            "text": self._extract_text_props(node),
        }

        styles = self._extract_styles(node)
        if styles:
            result["styles"] = styles

        return result

    def _convert_icon(self, node: dict) -> dict:
        """icon_font → TEXT（以 icon 字型呈現）"""
        icon_name = node.get("icon", "")
        font_family = node.get("fontFamily", "Material Icons")

        result: dict[str, Any] = {
            "figmaName": node.get("name", f"Icon-{icon_name}"),
            "figmaType": "TEXT",
            "layout": self._extract_layout(node),
            "text": {
                "characters": icon_name,
                "fontSize": node.get("fontSize", 24),
                "fontFamily": font_family,
                "fontWeight": node.get("fontWeight", 400),
                "color": node.get("color", "#000000"),
                "textAlign": "CENTER",
            },
            "pluginData": {"isIcon": True, "iconFont": font_family},
        }

        return result

    def _convert_rectangle(self, node: dict) -> dict:
        """rectangle → FRAME（純視覺裝飾）"""
        result: dict[str, Any] = {
            "figmaName": node.get("name", "Rectangle"),
            "figmaType": "FRAME",
            "layout": self._extract_layout(node),
        }

        styles = self._extract_styles(node)
        if styles:
            result["styles"] = styles

        return result

    def _convert_ref(self, node: dict) -> dict:
        """ref → INSTANCE（組件實例引用）"""
        result: dict[str, Any] = {
            "figmaName": node.get("name", "Instance"),
            "figmaType": "INSTANCE",
            "componentRef": node.get("ref", ""),
            "layout": self._extract_layout(node),
        }

        styles = self._extract_styles(node)
        if styles:
            result["styles"] = styles

        children_raw = node.get("children")
        if isinstance(children_raw, list):
            children = [self._convert_node(c) for c in children_raw]
            result["children"] = [c for c in children if c is not None]

        return result

    # ──────────────────────────────────────────────
    # 屬性擷取
    # ──────────────────────────────────────────────

    def _extract_layout(self, node: dict) -> dict:
        """擷取佈局位置與尺寸。"""
        layout: dict[str, Any] = {}

        x = node.get("x")
        y = node.get("y")
        if x is not None:
            layout["x"] = x
        if y is not None:
            layout["y"] = y

        width = node.get("width")
        height = node.get("height")

        # fill_container → 特殊標記
        if width == "fill_container":
            layout["width"] = "FILL"
            layout["fillWidth"] = True
        elif width is not None:
            layout["width"] = width

        if height == "fill_container":
            layout["height"] = "FILL"
            layout["fillHeight"] = True
        elif height is not None:
            layout["height"] = height

        return layout

    def _has_auto_layout(self, node: dict) -> bool:
        """判斷節點是否有 auto layout 設定。"""
        return bool(
            node.get("layout") in ("vertical", "horizontal")
            or node.get("gap") is not None
            or node.get("justifyContent")
            or node.get("alignItems")
        )

    def _extract_auto_layout(self, node: dict) -> Optional[dict]:
        """擷取 auto layout 屬性。"""
        if not self._has_auto_layout(node):
            return None

        layout_dir = node.get("layout", "horizontal")
        direction = "VERTICAL" if layout_dir == "vertical" else "HORIZONTAL"

        al: dict[str, Any] = {"direction": direction}

        gap = node.get("gap")
        if gap is not None:
            al["spacing"] = gap

        # Padding
        padding = node.get("padding")
        if isinstance(padding, dict):
            al["paddingTop"] = padding.get("top", 0)
            al["paddingRight"] = padding.get("right", 0)
            al["paddingBottom"] = padding.get("bottom", 0)
            al["paddingLeft"] = padding.get("left", 0)
        elif isinstance(padding, (int, float)):
            al["paddingTop"] = padding
            al["paddingRight"] = padding
            al["paddingBottom"] = padding
            al["paddingLeft"] = padding

        # Alignment → IR 的 primaryAlign / counterAlign
        jc = node.get("justifyContent", "")
        if jc:
            al["primaryAlign"] = self._map_alignment(jc)

        ai = node.get("alignItems", "")
        if ai:
            al["counterAlign"] = self._map_alignment(ai)

        wrap = node.get("wrap")
        if wrap is not None:
            al["wrap"] = wrap

        return al

    def _map_alignment(self, value: str) -> str:
        """Pencil alignment → IR alignment。"""
        mapping = {
            "start": "MIN",
            "flex-start": "MIN",
            "center": "CENTER",
            "end": "MAX",
            "flex-end": "MAX",
            "space_between": "SPACE_BETWEEN",
            "space-between": "SPACE_BETWEEN",
            "space_around": "SPACE_AROUND",
            "stretch": "STRETCH",
        }
        return mapping.get(value.lower(), "MIN")

    def _extract_styles(self, node: dict) -> Optional[dict]:
        """擷取視覺樣式。"""
        styles: dict[str, Any] = {}

        # Fill → SOLID
        fill = node.get("fill")
        if fill:
            parsed_fill = self._parse_fill(fill)
            styles["fills"] = [parsed_fill]
            if parsed_fill["type"] == "SOLID":
                styles["backgroundColor"] = parsed_fill["color"]

        # Opacity
        opacity = node.get("opacity")
        if opacity is not None:
            styles["opacity"] = opacity

        # Border radius
        cr = node.get("cornerRadius")
        if cr is not None:
            if isinstance(cr, dict):
                styles["borderRadius"] = {
                    "topLeft": cr.get("topLeft", 0),
                    "topRight": cr.get("topRight", 0),
                    "bottomRight": cr.get("bottomRight", 0),
                    "bottomLeft": cr.get("bottomLeft", 0),
                }
            else:
                styles["borderRadius"] = {
                    "topLeft": cr, "topRight": cr,
                    "bottomRight": cr, "bottomLeft": cr,
                }

        # Border / stroke
        stroke = node.get("stroke")
        if stroke:
            styles["border"] = {
                "color": stroke.get("color", "#000"),
                "width": stroke.get("width", 1),
                "style": stroke.get("style", "SOLID").upper(),
            }

        # Shadow
        shadow = node.get("shadow")
        if shadow:
            if isinstance(shadow, dict):
                shadow = [shadow]
            styles["shadow"] = [
                {
                    "color": s.get("color", "rgba(0,0,0,0.2)"),
                    "offsetX": s.get("offsetX", s.get("x", 0)),
                    "offsetY": s.get("offsetY", s.get("y", 0)),
                    "blur": s.get("blur", 0),
                    "spread": s.get("spread", 0),
                }
                for s in shadow
            ]

        # Background color（別名）
        bg = node.get("backgroundColor")
        if bg and "fills" not in styles:
            styles["fills"] = [self._parse_fill(bg)]

        return styles if styles else None

    def _parse_fill(self, fill: Any) -> dict:
        """Parse fill value to IR fill format."""
        if isinstance(fill, str):
            return {"type": "SOLID", "color": self._normalize_color(fill)}
        if isinstance(fill, dict):
            fill_type = fill.get("type", "SOLID").upper()
            if fill_type == "SOLID":
                return {"type": "SOLID", "color": self._normalize_color(fill.get("color", "#000"))}
            if "GRADIENT" in fill_type:
                return {
                    "type": fill_type,
                    "stops": fill.get("stops", []),
                }
        return {"type": "SOLID", "color": "#000000"}

    def _normalize_color(self, color: str) -> str:
        """Normalize color string to consistent format."""
        if not color:
            return "rgba(0,0,0,1)"
        # Already rgba/rgb → keep as-is
        if color.startswith("rgb"):
            return color
        # Hex → rgba
        color = color.strip()
        if color.startswith("#"):
            hex_str = color[1:]
            if len(hex_str) == 3:
                hex_str = "".join(c * 2 for c in hex_str)
            if len(hex_str) == 6:
                r, g, b = int(hex_str[0:2], 16), int(hex_str[2:4], 16), int(hex_str[4:6], 16)
                return f"rgba({r},{g},{b},1)"
            if len(hex_str) == 8:
                r, g, b = int(hex_str[0:2], 16), int(hex_str[2:4], 16), int(hex_str[4:6], 16)
                a = round(int(hex_str[6:8], 16) / 255, 2)
                return f"rgba({r},{g},{b},{a})"
        return color

    def _extract_text_props(self, node: dict) -> dict:
        """擷取文字屬性。"""
        text: dict[str, Any] = {
            "characters": node.get("content", node.get("text", "")),
            "fontSize": node.get("fontSize", 14),
            "fontFamily": node.get("fontFamily", "Inter"),
            "fontWeight": node.get("fontWeight", 400),
            "color": self._normalize_color(node.get("color", node.get("fill", "#000000"))),
            "textAlign": (node.get("textAlign") or "LEFT").upper(),
        }

        line_height = node.get("lineHeight")
        if line_height is not None:
            text["lineHeight"] = line_height

        letter_spacing = node.get("letterSpacing")
        if letter_spacing is not None:
            text["letterSpacing"] = letter_spacing

        return text

    def _detect_viewport(self, tree: Optional[dict]) -> dict:
        """從根節點推測 viewport。"""
        if tree is None:
            return {"width": 1440, "height": 900}
        layout = tree.get("layout", {})
        width = layout.get("width", 1440)
        height = layout.get("height", 900)
        if isinstance(width, str):
            width = 1440
        if isinstance(height, str):
            height = 900
        return {"width": width, "height": height}
