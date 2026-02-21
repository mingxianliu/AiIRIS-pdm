"""
IR 建構 — 將 Raw DOM 樹轉成具命名與樣式的 IR，供 Figma Plugin 使用
"""

import json
import os
from datetime import datetime, timezone
from typing import Optional

from .naming_engine import NamingEngine, NamingConfig


class IRBuilder:
    """從 raw DOM 樹建出 IR 文件，套用命名規則並記錄來源對應."""

    def __init__(
        self,
        naming_engine: Optional[NamingEngine] = None,
        framework: str = "vue",
        style_strategy: str = "tailwind",
        entry_file: str = "",
    ):
        self.namer = naming_engine or NamingEngine()
        self.framework = framework
        self.style_strategy = style_strategy
        self.entry_file = entry_file
        self.name_mapping: dict = {}

    def build(self, raw_tree: dict, viewport: dict) -> dict:
        """從 raw DOM 樹建出完整 IR 文件（符合 ir_schema）。"""
        ir_tree = self._convert_node(raw_tree, parent_path="")
        return {
            "version": "1.0.0",
            "source": {
                "framework": self.framework,
                "entryFile": self.entry_file,
                "styleStrategy": self.style_strategy,
                "generatedAt": datetime.now(timezone.utc).isoformat(),
            },
            "viewport": viewport,
            "nameMapping": self.name_mapping,
            "tree": ir_tree,
        }

    def _convert_node(self, raw: dict, parent_path: str) -> Optional[dict]:
        if not raw:
            return None
        tag = raw.get("tag", "div")
        attrs = raw.get("attrs", {})
        component_name = raw.get("componentName")

        figma_name = self.namer.resolve_name(
            parent_path=parent_path,
            tag=tag,
            attrs=attrs,
            component_name=component_name,
            sibling_index=raw.get("siblingIndex", 0),
            sibling_tag_count=raw.get("siblingTagCount", 1),
        )
        sep = self.namer.config.separator
        local_name = figma_name.split(sep)[-1] if sep in figma_name else figma_name

        figma_type = self._determine_type(raw)
        styles = raw.get("styles", {})

        ir_node = {
            "figmaName": local_name,
            "figmaType": figma_type,
            "htmlTag": tag,
            "layout": raw.get("layout", {"x": 0, "y": 0, "width": 100, "height": 100}),
        }
        if component_name:
            ir_node["componentRef"] = component_name
        if figma_type == "AUTO_LAYOUT" and raw.get("autoLayout"):
            ir_node["autoLayout"] = raw["autoLayout"]
        ir_styles = self._convert_styles(styles)
        if ir_styles:
            ir_node["styles"] = ir_styles
        if figma_type == "TEXT" and raw.get("textContent"):
            ir_node["text"] = {
                "characters": raw["textContent"].strip(),
                "fontSize": styles.get("fontSize", 14),
                "fontFamily": styles.get("fontFamily", "Inter"),
                "fontWeight": styles.get("fontWeight", 400),
                "lineHeight": styles.get("lineHeight"),
                "letterSpacing": styles.get("letterSpacing", 0),
                "textAlign": self._map_text_align(styles.get("textAlign", "left")),
                "color": styles.get("color", "rgb(0, 0, 0)"),
            }
        if figma_type == "IMAGE":
            ir_node["image"] = {"src": raw.get("imageSrc", ""), "scaleMode": "FILL"}

        ir_node["pluginData"] = {
            "sourceFile": self.entry_file,
            "selector": self._build_selector(tag, attrs),
            "cssClasses": attrs.get("class", ""),
            "originalTag": tag,
        }
        self.name_mapping[figma_name] = {
            "sourceFile": self.entry_file,
            "selector": ir_node["pluginData"]["selector"],
            "componentName": component_name or "",
        }

        raw_children = raw.get("children", [])
        if raw_children:
            ir_node["children"] = []
            for child in raw_children:
                child_ir = self._convert_node(child, parent_path=figma_name)
                if child_ir:
                    ir_node["children"].append(child_ir)
        return ir_node

    def _determine_type(self, raw: dict) -> str:
        if raw.get("isImage"):
            return "IMAGE"
        if raw.get("isTextNode"):
            return "TEXT"
        if raw.get("autoLayout"):
            return "AUTO_LAYOUT"
        if raw.get("tag", "").lower() == "svg":
            return "IMAGE"
        if raw.get("tag", "").lower() in ("input", "textarea", "select"):
            return "RECTANGLE"
        return "FRAME"

    def _convert_styles(self, styles: dict) -> Optional[dict]:
        result = {}
        if styles.get("backgroundColor"):
            result["backgroundColor"] = styles["backgroundColor"]
        if styles.get("opacity") is not None and styles["opacity"] < 1:
            result["opacity"] = styles["opacity"]
        if styles.get("borderRadius"):
            result["borderRadius"] = styles["borderRadius"]
        if styles.get("borderWidth", 0) > 0:
            result["border"] = {
                "color": styles.get("borderColor", "rgb(0,0,0)"),
                "width": styles["borderWidth"],
                "style": "DASHED" if styles.get("borderStyle") == "dashed" else "SOLID",
            }
        if styles.get("shadow"):
            result["shadow"] = styles["shadow"]
        return result if result else None

    def _map_text_align(self, css_align: str) -> str:
        m = {"left": "LEFT", "center": "CENTER", "right": "RIGHT", "justify": "JUSTIFIED", "start": "LEFT", "end": "RIGHT"}
        return m.get(css_align, "LEFT")

    def _build_selector(self, tag: str, attrs: dict) -> str:
        s = tag
        if attrs.get("id"):
            s += f"#{attrs['id']}"
        for cls in (attrs.get("class") or "").strip().split()[:3]:
            s += f".{cls}"
        return s


def build_ir_from_extraction(extraction_result: dict, config: dict) -> dict:
    """高層：擷取結果 + 設定 → 完整 IR 文件."""
    naming_config = NamingConfig()
    naming_section = config.get("naming", {})
    if naming_section.get("separator"):
        naming_config.separator = naming_section["separator"]
    if naming_section.get("ignoreClasses"):
        naming_config.ignore_class_prefixes = naming_section["ignoreClasses"]
    naming_engine = NamingEngine(naming_config)
    source_config = config.get("source", {})
    builder = IRBuilder(
        naming_engine=naming_engine,
        framework=source_config.get("framework", "html"),
        style_strategy=source_config.get("styleStrategy", "inline"),
        entry_file=source_config.get("entryUrl", ""),
    )
    return builder.build(
        raw_tree=extraction_result["tree"],
        viewport=extraction_result["viewport"],
    )


def save_ir(ir_doc: dict, output_dir: str = ".figma-sync") -> tuple:
    """將 IR 與 nameMapping 寫入檔案。回傳 (ir_path, mapping_path)。"""
    os.makedirs(output_dir, exist_ok=True)
    ir_path = os.path.join(output_dir, "figma-import-payload.json")
    with open(ir_path, "w", encoding="utf-8") as f:
        json.dump(ir_doc, f, indent=2, ensure_ascii=False)
    mapping_path = os.path.join(output_dir, "name-mapping.json")
    with open(mapping_path, "w", encoding="utf-8") as f:
        json.dump(ir_doc.get("nameMapping", {}), f, indent=2, ensure_ascii=False)
    plugin_path = os.path.join(output_dir, "plugin-payload.json")
    with open(plugin_path, "w", encoding="utf-8") as f:
        json.dump(ir_doc["tree"], f, indent=2, ensure_ascii=False)
    return ir_path, mapping_path
