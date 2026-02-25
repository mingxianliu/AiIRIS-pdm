"""
ir_builder_v2.py — Convert DOM v2 Tree → IR with Full Style Coverage

Handles ALL data from dom_extractor_v2:
  ✅ Gradient → Figma GradientPaint
  ✅ Background image URL → Figma ImagePaint
  ✅ Individual borders → per-side strokes
  ✅ Inset shadow → INNER_SHADOW effect
  ✅ Text shadow → separate effect layer
  ✅ Text decoration → underline/strikethrough
  ✅ SVG markup → vector data or image fallback
  ✅ Pseudo ::before/::after → child nodes
  ✅ CSS transform → rotation + position offset
  ✅ Filter/backdrop-filter → Figma blur/brightness
  ✅ Overflow hidden → clip content
  ✅ Grid layout → Auto Layout WRAP approximation
  ✅ z-index → layer order
"""

import json
import os
from datetime import datetime, timezone
from typing import Optional

from .naming_engine import NamingEngine, NamingConfig


class IRBuilderV2:

    def __init__(
        self,
        naming_engine: Optional[NamingEngine] = None,
        framework: str = "vue",
        style_strategy: str = "tailwind",
        entry_file: str = "",
        smart_flatten: bool = True,
        cjk_font_family: "list[str] | str" = "Noto Sans TC",
    ):
        self.namer = naming_engine or NamingEngine()
        self.framework = framework
        self.style_strategy = style_strategy
        self.entry_file = entry_file
        self.smart_flatten = smart_flatten
        # Ensure it's a list for internal consistency
        if isinstance(cjk_font_family, str):
            self.cjk_font_family = [cjk_font_family]
        else:
            self.cjk_font_family = cjk_font_family
        self.name_mapping: dict[str, dict] = {}
        self._node_count = 0

    def build(self, raw_tree: dict, viewport: dict) -> dict:
        self.name_mapping = {}
        self._node_count = 0
        ir_tree = self._convert_node(raw_tree, parent_path="")

        return {
            "version": "2.0.0",
            "source": {
                "framework": self.framework,
                "entryFile": self.entry_file,
                "styleStrategy": self.style_strategy,
                "generatedAt": datetime.now(timezone.utc).isoformat(),
            },
            "viewport": viewport,
            "nameMapping": self.name_mapping,
            "stats": {"nodeCount": self._node_count},
            "tree": ir_tree,
        }

    # ════════════════════════════════════════════════════════════
    # Node Conversion
    # ════════════════════════════════════════════════════════════

    def _detect_cjk(self, text: str) -> bool:
        """Detect if text contains CJK characters."""
        if not text:
            return False
        for char in text:
            if '\u4e00' <= char <= '\u9fff':
                return True
        return False

    def _convert_node(self, raw: dict, parent_path: str) -> Optional[dict]:
        if not raw:
            return None

        # ─── Smart Flattening (Step 2) ───
        # If this node is a useless wrapper, skip it and process its child.
        if self.smart_flatten and self._should_flatten(raw):
            # Only one child (guaranteed by _should_flatten)
            # Use the SAME parent_path so the child takes this node's place in hierarchy
            return self._convert_node(raw["children"][0], parent_path)

        self._node_count += 1
        tag = raw.get("tag", "div")
        attrs = raw.get("attrs", {})
        component_name = raw.get("componentName")

        # ─── Naming ───
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

        # ─── Type ───
        figma_type = self._determine_type(raw)

        ir_node = {
            "figmaName": local_name,
            "figmaType": figma_type,
            "htmlTag": tag,
        }

        if component_name:
            ir_node["componentRef"] = component_name

        # ─── Layout ───
        layout = raw.get("layout", {"x": 0, "y": 0, "width": 100, "height": 100})
        ir_node["layout"] = layout

        # ─── Auto Layout (flex + grid) ───
        auto_layout = raw.get("autoLayout")
        if auto_layout:
            ir_node["autoLayout"] = auto_layout
            if figma_type not in ("TEXT", "IMAGE"):
                ir_node["figmaType"] = "AUTO_LAYOUT"

        # ─── Styles (comprehensive) ───
        styles = raw.get("styles", {})
        ir_styles = self._convert_styles(styles, raw)
        if ir_styles:
            ir_node["styles"] = ir_styles

        # ─── Text ───
        if figma_type == "TEXT" and raw.get("textContent"):
            ir_node["text"] = self._build_text(raw, styles)

        # ─── Image ───
        if figma_type == "IMAGE":
            ir_node["image"] = self._build_image(raw)

        # ─── SVG Vector ✨ NEW ───
        svg_data = raw.get("svgData")
        if svg_data:
            ir_node["svgData"] = svg_data

        # ─── Transform ✨ NEW ───
        transform = raw.get("transform")
        if transform:
            ir_node["transform"] = transform
            # Apply rotation to layout
            if transform.get("rotation"):
                ir_node["rotation"] = transform["rotation"]

        # ─── Overflow / Clip ✨ NEW ───
        overflow = styles.get("overflow") or styles.get("overflowX") or styles.get("overflowY")
        if overflow and overflow in ("hidden", "scroll", "auto", "clip"):
            ir_node["clipsContent"] = True

        # ─── Plugin data ───
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

        # ─── Pseudo elements → synthetic children ✨ NEW ───
        pseudo_children = self._convert_pseudos(raw.get("pseudoElements"), figma_name)

        # ─── Children ───
        raw_children = raw.get("children", [])

        # Sort by z-index if available
        z_indexed = [(c, c.get("styles", {}).get("zIndex") or 0) for c in raw_children]
        z_indexed.sort(key=lambda x: x[1])

        all_children = []

        # Prepend ::before pseudo
        for pc in pseudo_children:
            if pc.get("_pseudoType") == "::before":
                del pc["_pseudoType"]
                all_children.append(pc)

        # Real children
        for child_raw, _ in z_indexed:
            child_ir = self._convert_node(child_raw, parent_path=figma_name)
            if child_ir:
                all_children.append(child_ir)

        # Append ::after pseudo
        for pc in pseudo_children:
            if pc.get("_pseudoType") == "::after":
                del pc["_pseudoType"]
                all_children.append(pc)

        if all_children:
            ir_node["children"] = all_children

        return ir_node

    def _should_flatten(self, raw: dict) -> bool:
        """
        Smart Flattening: Determine if a node is a useless wrapper.
        Criteria:
        1. Has exactly one element child (and no text content).
        2. No visual styling (bg, border, shadow).
        3. No layout semantic (not a grid/flex container itself - or trivial one).
        4. Not a component root (preserve components).
        5. No explicit naming (data-figma-name).
        """
        # 1. Check children
        children = raw.get("children", [])
        if len(children) != 1:
            return False
        
        # If the single child is just text node, don't flatten (it might be a container for text)
        # unless it's a pure span wrapping text?
        # Let's be safe: only flatten if child is an element.
        if children[0].get("isTextNode"):
            return False

        # 2. Check type/semantics
        tag = raw.get("tag", "div")
        if tag not in ("div", "span", "section", "article"):
            return False
        
        # Don't flatten if it's a detected component root
        if raw.get("componentName"):
            return False
            
        # Don't flatten if explicitly named
        if raw.get("attrs", {}).get("data-figma-name"):
            return False

        # Don't flatten if it has an ID (usually significant)
        if raw.get("attrs", {}).get("id"):
            return False

        # 3. Check Visuals
        styles = raw.get("styles", {})
        
        # Background
        if styles.get("backgroundColor") or styles.get("backgroundImage") or styles.get("gradient"):
            return False
            
        # Border
        if styles.get("border"):
            return False
        if styles.get("borderRadius"):
            return False
            
        # Shadows
        if styles.get("boxShadow") or styles.get("textShadow"):
            return False
            
        # Overflow/Clip
        overflow = styles.get("overflow") or styles.get("overflowX") or styles.get("overflowY")
        if overflow in ("hidden", "scroll", "auto", "clip"):
            return False

        # 4. Check Layout
        # If it has grid/flex, it might be doing layout for its single child.
        # But if it has only ONE child, flex/grid properties on the parent might not matter much
        # UNLESS they add padding or alignment.
        
        # If it adds padding, we can't flatten (padding would be lost).
        if (styles.get("paddingTop") or styles.get("paddingRight") or 
            styles.get("paddingBottom") or styles.get("paddingLeft")):
            return False

        # If it has a specific width/height that constrains the child?
        # DOM extractor gives us computed width/height.
        # If we remove the parent, the child still has its own dimensions.
        # But if the parent was `position: relative` and child `absolute`?
        if styles.get("position", "static") != "static":
            return False
            
        # If it has transform/opacity
        if raw.get("transform") or (styles.get("opacity", 1) < 1):
            return False

        return True

    # ════════════════════════════════════════════════════════════
    # Type Determination
    # ════════════════════════════════════════════════════════════

    def _determine_type(self, raw: dict) -> str:
        tag = raw.get("tag", "div").lower()

        if raw.get("isTextNode"):
            return "TEXT"
        if raw.get("isImage") or tag == "img":
            return "IMAGE"
        if raw.get("isSVG") or tag == "svg":
            return "VECTOR" if raw.get("svgData") else "IMAGE"
        if raw.get("isCanvas") or raw.get("isVideo"):
            return "IMAGE"
        if raw.get("autoLayout"):
            return "AUTO_LAYOUT"
        if tag in ("input", "textarea", "select", "button"):
            return "RECTANGLE"
        if tag == "hr":
            return "RECTANGLE"
        return "FRAME"

    # ════════════════════════════════════════════════════════════
    # Style Conversion (comprehensive)
    # ════════════════════════════════════════════════════════════

    def _convert_styles(self, styles: dict, raw: dict) -> Optional[dict]:
        result = {}

        # ─── Fills (background) ───
        fills = self._build_fills(styles, raw)
        if fills:
            result["fills"] = fills

        # ─── Opacity ───
        opacity = styles.get("opacity")
        if opacity is not None and opacity < 1:
            result["opacity"] = opacity

        # ─── Blend mode ✨ NEW ───
        blend = styles.get("mixBlendMode")
        if blend:
            result["blendMode"] = blend.upper().replace("-", "_")

        # ─── Border radius ───
        br = styles.get("borderRadius")
        if br:
            result["borderRadius"] = br

        # ─── Borders (individual sides) ✨ ENHANCED ───
        border = styles.get("border")
        if border:
            result["border"] = border

        # ─── Shadows (box + inner) ✨ ENHANCED ───
        box_shadow = styles.get("boxShadow")
        if box_shadow:
            result["effects"] = []
            for s in box_shadow:
                result["effects"].append({
                    "type": s.get("type", "DROP_SHADOW"),
                    "color": s["color"],
                    "offsetX": s["offsetX"],
                    "offsetY": s["offsetY"],
                    "blur": s["blur"],
                    "spread": s.get("spread", 0),
                })

        # ─── Text shadow ✨ NEW ───
        text_shadow = styles.get("textShadow")
        if text_shadow:
            result["textShadow"] = text_shadow

        # ─── Text decoration ✨ NEW ───
        text_dec = styles.get("textDecoration")
        if text_dec:
            result["textDecoration"] = text_dec

        # ─── Text transform ✨ NEW ───
        text_transform = styles.get("textTransform")
        if text_transform:
            result["textTransform"] = text_transform

        # ─── Filter / backdrop-filter ✨ NEW ───
        filt = raw.get("filter")
        if filt:
            result["filter"] = filt
            # Extract blur for Figma layer blur
            if "blur" in filt:
                blur_val = float(filt["blur"].replace("px", ""))
                if "effects" not in result:
                    result["effects"] = []
                result["effects"].append({
                    "type": "LAYER_BLUR",
                    "blur": blur_val,
                })

        backdrop = raw.get("backdropFilter")
        if backdrop:
            result["backdropFilter"] = backdrop
            if "blur" in backdrop:
                blur_val = float(backdrop["blur"].replace("px", ""))
                if "effects" not in result:
                    result["effects"] = []
                result["effects"].append({
                    "type": "BACKGROUND_BLUR",
                    "blur": blur_val,
                })

        # ─── Overflow → clip ✨ NEW ───
        overflow = styles.get("overflow")
        if overflow and overflow in ("hidden", "scroll", "auto", "clip"):
            result["clipsContent"] = True

        # ─── Cursor (hint for interactivity) ✨ NEW ───
        cursor = styles.get("cursor")
        if cursor and cursor in ("pointer", "grab", "text"):
            result["interactive"] = True
            result["cursor"] = cursor

        return result if result else None

    def _build_fills(self, styles: dict, raw: dict) -> Optional[list]:
        """Build Figma fills array from CSS backgrounds."""
        fills = []

        # Solid background color
        bg_color = styles.get("backgroundColor")
        if bg_color:
            fills.append({
                "type": "SOLID",
                "color": bg_color,
            })

        # Gradient ✨ NEW
        gradients = styles.get("gradient")
        if gradients:
            for g in gradients:
                if g["type"].startswith("linear") or g["type"].startswith("repeating-linear"):
                    fills.append({
                        "type": "GRADIENT_LINEAR",
                        "angle": g.get("angle", 180),
                        "stops": g.get("stops", []),
                    })
                elif g["type"].startswith("radial") or g["type"].startswith("repeating-radial"):
                    fills.append({
                        "type": "GRADIENT_RADIAL",
                        "stops": g.get("stops", []),
                    })
                elif g["type"].startswith("conic"):
                    fills.append({
                        "type": "GRADIENT_ANGULAR",
                        "stops": g.get("stops", []),
                    })

        # Background image URL ✨ NEW
        bg_images = styles.get("backgroundImage")
        if bg_images:
            for url in bg_images:
                fills.append({
                    "type": "IMAGE",
                    "src": url,
                    "scaleMode": self._map_bg_size(styles.get("backgroundSize")),
                })

        return fills if fills else None

    def _map_bg_size(self, bg_size: Optional[str]) -> str:
        if not bg_size:
            return "FILL"
        if "contain" in bg_size:
            return "FIT"
        if "cover" in bg_size:
            return "FILL"
        return "FILL"

    # ════════════════════════════════════════════════════════════
    # Text
    # ════════════════════════════════════════════════════════════

    def _build_text(self, raw: dict, styles: dict) -> dict:
        text_data = {
            "characters": (raw.get("textContent") or "").strip(),
            "fontSize": styles.get("fontSize", 14),
            "fontFamily": styles.get("fontFamily", "Inter"),
            "fontWeight": styles.get("fontWeight", 400),
            "lineHeight": styles.get("lineHeight"),
            "letterSpacing": styles.get("letterSpacing", 0),
            "textAlign": self._map_text_align(styles.get("textAlign", "left")),
            "color": styles.get("color", "rgb(0, 0, 0)"),
        }

        # Text decoration ✨ NEW
        td = styles.get("textDecoration")
        if td:
            line = td.get("line", "")
            if "underline" in line:
                text_data["textDecoration"] = "UNDERLINE"
            elif "line-through" in line:
                text_data["textDecoration"] = "STRIKETHROUGH"

        # Font style ✨ NEW
        if styles.get("fontStyle") == "italic":
            text_data["fontStyle"] = "italic"

        # White space / truncation ✨ NEW
        if styles.get("textOverflow") == "ellipsis":
            text_data["truncation"] = "ENDING"
        if styles.get("whiteSpace") == "nowrap":
            text_data["maxLines"] = 1

        # CJK Font Fallback ✨ NEW
        if self._detect_cjk(text_data["characters"]):
            # If current font is the default system font or Inter, force CJK font
            current_font = text_data["fontFamily"]
            if current_font in ("Inter", "system-ui", "sans-serif", "-apple-system"):
                # Use the first preferred font as primary
                text_data["fontFamily"] = self.cjk_font_family[0]
                # Provide the full stack for the plugin to try
                text_data["fontFamilyStack"] = self.cjk_font_family

        return text_data

    # ════════════════════════════════════════════════════════════
    # Image
    # ════════════════════════════════════════════════════════════

    def _build_image(self, raw: dict) -> dict:
        img = {
            "scaleMode": "FILL",
        }
        if raw.get("imageSrc"):
            img["src"] = raw["imageSrc"]
        if raw.get("imageData"):
            img["base64"] = raw["imageData"]
        if raw.get("imageAlt"):
            img["alt"] = raw["imageAlt"]
        return img

    # ════════════════════════════════════════════════════════════
    # Pseudo Elements → Synthetic IR children ✨ NEW
    # ════════════════════════════════════════════════════════════

    def _convert_pseudos(self, pseudos: Optional[list], parent_path: str) -> list:
        if not pseudos:
            return []

        children = []
        for p in pseudos:
            pseudo_type = p.get("pseudo", "::before")
            content = p.get("content", "")

            ir_child = {
                "figmaName": f"_pseudo_{pseudo_type.replace('::', '')}",
                "figmaType": "TEXT" if content and content != '""' else "RECTANGLE",
                "htmlTag": pseudo_type,
                "_pseudoType": pseudo_type,
                "layout": {
                    "x": p.get("left", 0),
                    "y": p.get("top", 0),
                    "width": max(p.get("width", 0), 1),
                    "height": max(p.get("height", 0), 1),
                },
                "pluginData": {
                    "originalTag": pseudo_type,
                    "sourceFile": self.entry_file,
                    "selector": f"{parent_path}::{pseudo_type.replace('::', '')}",
                    "cssClasses": "",
                },
            }

            # Styles
            pseudo_styles = {}
            if p.get("backgroundColor"):
                pseudo_styles["fills"] = [{"type": "SOLID", "color": p["backgroundColor"]}]
            if p.get("borderRadius"):
                pseudo_styles["borderRadius"] = p["borderRadius"]
            if pseudo_styles:
                ir_child["styles"] = pseudo_styles

            # Text content
            if content and content != '""' and ir_child["figmaType"] == "TEXT":
                ir_child["text"] = {
                    "characters": content,
                    "fontSize": p.get("fontSize", 14),
                    "fontFamily": p.get("fontFamily", "Inter"),
                    "fontWeight": 400,
                    "color": p.get("color", "rgb(0,0,0)"),
                    "textAlign": "LEFT",
                    "letterSpacing": 0,
                }

            children.append(ir_child)

        return children

    # ════════════════════════════════════════════════════════════
    # Utilities
    # ════════════════════════════════════════════════════════════

    def _map_text_align(self, css_align: str) -> str:
        return {
            "left": "LEFT", "center": "CENTER", "right": "RIGHT",
            "justify": "JUSTIFIED", "start": "LEFT", "end": "RIGHT",
        }.get(css_align, "LEFT")

    def _build_selector(self, tag: str, attrs: dict) -> str:
        selector = tag
        if attrs.get("id"):
            selector += f"#{attrs['id']}"
        if attrs.get("class"):
            classes = attrs["class"].strip().split()[:3]
            for cls in classes:
                selector += f".{cls}"
        return selector


# ════════════════════════════════════════════════════════════
# High-level API (drop-in replacement for v1)
# ════════════════════════════════════════════════════════════

def build_ir_from_extraction(extraction_result: dict, config: dict) -> dict:
    naming_config = NamingConfig()
    naming_section = config.get("naming", {})
    if naming_section.get("separator"):
        naming_config.separator = naming_section["separator"]
    if naming_section.get("ignoreClasses"):
        naming_config.ignore_class_prefixes = naming_section["ignoreClasses"]

    naming_engine = NamingEngine(naming_config)
    source_config = config.get("source", {})
    export_config = config.get("export", {})

    builder = IRBuilderV2(
        naming_engine=naming_engine,
        framework=source_config.get("framework", "html"),
        style_strategy=source_config.get("styleStrategy", "inline"),
        entry_file=source_config.get("entryUrl", ""),
        cjk_font_family=export_config.get("cjkFontFamily", ["PingFang TC", "Microsoft JhengHei", "Noto Sans TC", "sans-serif"]),
    )

    return builder.build(
        raw_tree=extraction_result["tree"],
        viewport=extraction_result["viewport"],
    )


def save_ir(ir_doc: dict, output_dir: str = ".figma-sync") -> tuple[str, str]:
    os.makedirs(output_dir, exist_ok=True)

    ir_path = os.path.join(output_dir, "figma-import-payload.json")
    with open(ir_path, 'w', encoding='utf-8') as f:
        json.dump(ir_doc, f, indent=2, ensure_ascii=False)

    mapping_path = os.path.join(output_dir, "name-mapping.json")
    with open(mapping_path, 'w', encoding='utf-8') as f:
        json.dump(ir_doc.get("nameMapping", {}), f, indent=2, ensure_ascii=False)

    plugin_path = os.path.join(output_dir, "plugin-payload.json")
    with open(plugin_path, 'w', encoding='utf-8') as f:
        json.dump(ir_doc["tree"], f, indent=2, ensure_ascii=False)

    return ir_path, mapping_path
