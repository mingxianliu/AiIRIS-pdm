"""
Figma REST API 讀取與 IR Diff

讀取 Figma 檔案、轉回 IR 格式，並與 push 時快照做 diff。
"""

import json
from typing import Optional

import requests


class FigmaAPIClient:
    """Figma REST API 唯讀封裝."""

    BASE_URL = "https://api.figma.com/v1"

    def __init__(self, token: str):
        self.token = token
        self.session = requests.Session()
        self.session.headers.update({
            "X-Figma-Token": token,
            "Content-Type": "application/json",
        })

    def get_file(self, file_key: str, node_ids: Optional[list] = None) -> dict:
        url = f"{self.BASE_URL}/files/{file_key}"
        params = {}
        if node_ids:
            params["ids"] = ",".join(node_ids)
        resp = self.session.get(url, params=params)
        resp.raise_for_status()
        return resp.json()

    def get_file_nodes(self, file_key: str, node_ids: list) -> dict:
        url = f"{self.BASE_URL}/files/{file_key}/nodes"
        params = {"ids": ",".join(node_ids)}
        resp = self.session.get(url, params=params)
        resp.raise_for_status()
        return resp.json()

    def get_images(self, file_key: str, node_ids: list, format: str = "png", scale: int = 2) -> dict:
        url = f"{self.BASE_URL}/images/{file_key}"
        params = {"ids": ",".join(node_ids), "format": format, "scale": scale}
        resp = self.session.get(url, params=params)
        resp.raise_for_status()
        return resp.json()


class FigmaToIR:
    """將 Figma API 節點樹轉回 IR 格式，供 diff 使用."""

    def __init__(self, plugin_namespace: str = "figma-code-sync"):
        self.plugin_namespace = plugin_namespace

    def convert(self, figma_node: dict) -> dict:
        node_type = figma_node.get("type", "FRAME")
        name = figma_node.get("name", "Unnamed")
        bbox = figma_node.get("absoluteBoundingBox", {})

        ir_node = {
            "figmaName": name,
            "figmaType": self._normalize_type(node_type),
            "layout": {
                "x": bbox.get("x", 0),
                "y": bbox.get("y", 0),
                "width": bbox.get("width", 0),
                "height": bbox.get("height", 0),
            },
        }
        styles = self._extract_styles(figma_node)
        if styles:
            ir_node["styles"] = styles
        if node_type in ("FRAME", "COMPONENT", "INSTANCE"):
            auto_layout = self._extract_auto_layout(figma_node)
            if auto_layout:
                ir_node["autoLayout"] = auto_layout
                ir_node["figmaType"] = "AUTO_LAYOUT"
        if node_type == "TEXT":
            text_data = self._extract_text(figma_node)
            if text_data:
                ir_node["text"] = text_data
        shared_data = figma_node.get("sharedPluginData", {})
        our_data = shared_data.get(self.plugin_namespace, {})
        if our_data:
            ir_node["pluginData"] = our_data
        children = figma_node.get("children", [])
        if children:
            ir_node["children"] = [
                self.convert(c) for c in children
                if c.get("visible", True)
            ]
        return ir_node

    def _normalize_type(self, figma_type: str) -> str:
        type_map = {
            "FRAME": "FRAME", "GROUP": "GROUP", "COMPONENT": "COMPONENT",
            "COMPONENT_SET": "COMPONENT", "INSTANCE": "INSTANCE",
            "TEXT": "TEXT", "RECTANGLE": "RECTANGLE", "ELLIPSE": "ELLIPSE",
            "VECTOR": "IMAGE", "BOOLEAN_OPERATION": "IMAGE", "LINE": "RECTANGLE",
            "SECTION": "SECTION",
        }
        return type_map.get(figma_type, "FRAME")

    def _extract_styles(self, node: dict) -> Optional[dict]:
        result = {}
        for fill in node.get("fills", []):
            if fill.get("visible", True) and fill.get("type") == "SOLID":
                c = fill.get("color", {})
                r, g, b = int(c.get("r", 0) * 255), int(c.get("g", 0) * 255), int(c.get("b", 0) * 255)
                a = fill.get("opacity", c.get("a", 1))
                result["backgroundColor"] = f"rgba({r}, {g}, {b}, {a})"
                break
        if node.get("opacity") is not None and node["opacity"] < 1:
            result["opacity"] = node["opacity"]
        cr = node.get("cornerRadius")
        if cr and cr > 0:
            rc = node.get("rectangleCornerRadii")
            result["borderRadius"] = {
                "topLeft": rc[0] if rc else cr,
                "topRight": rc[1] if rc and len(rc) > 1 else cr,
                "bottomRight": rc[2] if rc and len(rc) > 2 else cr,
                "bottomLeft": rc[3] if rc and len(rc) > 3 else cr,
            }
        for stroke in node.get("strokes", []):
            if stroke.get("visible", True) and stroke.get("type") == "SOLID":
                c = stroke.get("color", {})
                r, g, b = int(c.get("r", 0) * 255), int(c.get("g", 0) * 255), int(c.get("b", 0) * 255)
                result["border"] = {
                    "color": f"rgb({r}, {g}, {b})",
                    "width": node.get("strokeWeight", 0),
                    "style": "SOLID",
                }
                break
        shadows = []
        for effect in node.get("effects", []):
            if effect.get("visible", True) and effect.get("type") == "DROP_SHADOW":
                c = effect.get("color", {})
                r, g, b = int(c.get("r", 0) * 255), int(c.get("g", 0) * 255), int(c.get("b", 0) * 255)
                a = c.get("a", 0.25)
                off = effect.get("offset", {})
                shadows.append({
                    "color": f"rgba({r}, {g}, {b}, {a})",
                    "offsetX": off.get("x", 0), "offsetY": off.get("y", 0),
                    "blur": effect.get("radius", 0), "spread": effect.get("spread", 0),
                })
        if shadows:
            result["shadow"] = shadows
        return result if result else None

    def _extract_auto_layout(self, node: dict) -> Optional[dict]:
        if node.get("layoutMode") in (None, "NONE"):
            return None
        return {
            "direction": node["layoutMode"],
            "spacing": node.get("itemSpacing", 0),
            "paddingTop": node.get("paddingTop", 0),
            "paddingRight": node.get("paddingRight", 0),
            "paddingBottom": node.get("paddingBottom", 0),
            "paddingLeft": node.get("paddingLeft", 0),
            "primaryAlign": node.get("primaryAxisAlignItems", "MIN"),
            "counterAlign": node.get("counterAxisAlignItems", "MIN"),
            "wrap": node.get("layoutWrap") == "WRAP",
        }

    def _extract_text(self, node: dict) -> Optional[dict]:
        characters = node.get("characters", "")
        if not characters:
            return None
        style = node.get("style", {})
        color = "rgb(0, 0, 0)"
        for fill in node.get("fills", []):
            if fill.get("visible", True) and fill.get("type") == "SOLID":
                c = fill.get("color", {})
                color = f"rgb({int(c.get('r',0)*255)}, {int(c.get('g',0)*255)}, {int(c.get('b',0)*255)})"
                break
        return {
            "characters": characters,
            "fontSize": style.get("fontSize", 14),
            "fontFamily": style.get("fontFamily", "Inter"),
            "fontWeight": style.get("fontWeight", 400),
            "lineHeight": style.get("lineHeightPx"),
            "letterSpacing": style.get("letterSpacing", 0),
            "textAlign": style.get("textAlignHorizontal", "LEFT"),
            "color": color,
        }


class IRDiffer:
    """比對 push 快照與 Figma 編輯後的 IR，產出變更清單."""

    def diff(self, before: dict, after: dict) -> dict:
        """回傳 { figmaName: { property: { before, after } } } 或 _status added/deleted."""
        before_flat = self._flatten(before)
        after_flat = self._flatten(after)
        changes = {}
        for name, after_node in after_flat.items():
            before_node = before_flat.get(name)
            if not before_node:
                changes[name] = {"_status": "added"}
                continue
            node_changes = self._diff_node(before_node, after_node)
            if node_changes:
                changes[name] = node_changes
        for name in before_flat:
            if name not in after_flat:
                changes[name] = {"_status": "deleted"}
        return changes

    def _flatten(self, node: dict, result: Optional[dict] = None, path: str = "") -> dict:
        if result is None:
            result = {}
        name = node.get("figmaName", "?")
        full_path = f"{path}/{name}" if path else name
        result[full_path] = node
        for child in node.get("children", []):
            self._flatten(child, result, full_path)
        return result

    def _diff_node(self, before: dict, after: dict) -> Optional[dict]:
        changes = {}
        for key in set(list((before.get("styles") or {}).keys()) + list((after.get("styles") or {}).keys())):
            b = (before.get("styles") or {}).get(key)
            a = (after.get("styles") or {}).get(key)
            if b != a:
                changes[f"styles.{key}"] = {"before": b, "after": a}
        for key in set(list((before.get("text") or {}).keys()) + list((after.get("text") or {}).keys())):
            b = (before.get("text") or {}).get(key)
            a = (after.get("text") or {}).get(key)
            if b != a:
                changes[f"text.{key}"] = {"before": b, "after": a}
        b_layout, a_layout = before.get("layout", {}), after.get("layout", {})
        for key in ("width", "height"):
            bv, av = b_layout.get(key), a_layout.get(key)
            if bv and av and abs(bv - av) > 1:
                changes[f"layout.{key}"] = {"before": bv, "after": av}
        b_al, a_al = before.get("autoLayout", {}) or {}, after.get("autoLayout", {}) or {}
        for key in set(list(b_al.keys()) + list(a_al.keys())):
            if b_al.get(key) != a_al.get(key):
                changes[f"autoLayout.{key}"] = {"before": b_al.get(key), "after": a_al.get(key)}
        return changes if changes else None
