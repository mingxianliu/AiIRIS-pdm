"""
Code Patcher — 將 Figma 變更回寫到原始碼

依 diff 與 nameMapping 找到對應的 Vue/React/HTML 並套用樣式變更。
"""

import re
from typing import Optional


class StyleConverter:
    """IR 樣式變更 ↔ Tailwind / CSS 轉換."""

    @staticmethod
    def figma_color_to_hex(color_str: str) -> str:
        match = re.match(r"rgba?\((\d+),\s*(\d+),\s*(\d+)", color_str)
        if match:
            r, g, b = int(match.group(1)), int(match.group(2)), int(match.group(3))
            return f"#{r:02x}{g:02x}{b:02x}"
        return color_str

    @staticmethod
    def ir_styles_to_tailwind(changes: dict) -> list:
        """將單一節點的 IR 變更轉成 Tailwind class 建議."""
        additions = []
        for prop, change in changes.items():
            after = change.get("after")
            if after is None or prop.startswith("_"):
                continue
            if prop == "styles.backgroundColor":
                hex_val = StyleConverter.figma_color_to_hex(after)
                additions.append(f"+bg-[{hex_val}]")
            elif prop == "styles.opacity":
                pct = int(float(after) * 100)
                additions.append(f"opacity-{pct}")
            elif prop == "styles.borderRadius":
                if isinstance(after, dict):
                    vals = list(after.values())
                    if len(set(vals)) == 1:
                        additions.append(f"rounded-[{int(vals[0])}px]")
            elif prop == "text.fontSize":
                additions.append(f"text-[{int(after)}px]")
            elif prop == "text.fontWeight":
                weight_map = {100: "thin", 200: "extralight", 300: "light", 400: "normal",
                             500: "medium", 600: "semibold", 700: "bold", 800: "extrabold", 900: "black"}
                tw = weight_map.get(int(after), f"[{int(after)}]")
                additions.append(f"font-{tw}")
            elif prop == "text.color":
                hex_val = StyleConverter.figma_color_to_hex(after)
                additions.append(f"text-[{hex_val}]")
            elif prop == "autoLayout.spacing":
                additions.append(f"gap-[{int(after)}px]")
        return additions

    @staticmethod
    def ir_styles_to_css(changes: dict) -> dict:
        """將單一節點的 IR 變更轉成 CSS 屬性."""
        css_props = {}
        for prop, change in changes.items():
            after = change.get("after")
            if after is None or prop.startswith("_"):
                continue
            if prop == "styles.backgroundColor":
                css_props["background-color"] = after
            elif prop == "styles.opacity":
                css_props["opacity"] = str(after)
            elif prop == "styles.borderRadius" and isinstance(after, dict):
                tl = int(after.get("topLeft", 0))
                tr = int(after.get("topRight", 0))
                br = int(after.get("bottomRight", 0))
                bl = int(after.get("bottomLeft", 0))
                css_props["border-radius"] = f"{tl}px {tr}px {br}px {bl}px"
            elif prop == "styles.border" and isinstance(after, dict):
                w = int(after.get("width", 1))
                c = after.get("color", "#000")
                s = "dashed" if after.get("style") == "DASHED" else "solid"
                css_props["border"] = f"{w}px {s} {c}"
            elif prop == "text.fontSize":
                css_props["font-size"] = f"{int(after)}px"
            elif prop == "text.fontWeight":
                css_props["font-weight"] = str(int(after))
            elif prop == "text.color":
                css_props["color"] = after
            elif prop == "text.letterSpacing":
                css_props["letter-spacing"] = f"{after}px"
            elif prop == "text.lineHeight" and after:
                css_props["line-height"] = f"{after}px"
            elif prop == "autoLayout.spacing":
                css_props["gap"] = f"{int(after)}px"
            elif prop.startswith("autoLayout.padding"):
                side = prop.split(".")[-1].replace("padding", "").lower()
                css_props[f"padding-{side}"] = f"{int(after)}px"
        return css_props


class CodePatcher:
    """依 nameMapping 將 Figma diff 套回原始碼（Tailwind / CSS / inline）."""

    def __init__(self, name_mapping: dict, style_strategy: str = "tailwind"):
        self.name_mapping = name_mapping
        self.style_strategy = style_strategy
        self.converter = StyleConverter()
        self._patched_files: dict = {}

    def apply_changes(self, diff: dict) -> dict:
        """套用 diff。回傳 { filepath: [ 套用項目 ] }."""
        summary = {}
        for figma_name, changes in diff.items():
            if changes.get("_status") in ("added", "deleted"):
                continue
            mapping = self.name_mapping.get(figma_name) or self._find_mapping(figma_name)
            if not mapping:
                continue
            source_file = mapping.get("sourceFile", "")
            selector = mapping.get("selector", "")
            if not source_file or not selector:
                continue
            if source_file not in summary:
                summary[source_file] = []
            if self.style_strategy == "tailwind":
                applied = self._apply_tailwind(source_file, selector, changes)
            elif self.style_strategy in ("css-modules", "scss"):
                applied = self._apply_css(selector, changes)
            else:
                applied = self._apply_inline(changes)
            summary[source_file].extend(applied)
        return summary

    def _find_mapping(self, figma_name: str) -> Optional[dict]:
        for key, mapping in self.name_mapping.items():
            if key.endswith(figma_name) or figma_name.endswith(key.split("/")[-1]):
                return mapping
        return None

    def _apply_tailwind(self, filepath: str, selector: str, changes: dict) -> list:
        new_classes = StyleConverter.ir_styles_to_tailwind(changes)
        if not new_classes:
            return []
        return [f"  + class: {c}" for c in new_classes]

    def _apply_css(self, selector: str, changes: dict) -> list:
        css_props = StyleConverter.ir_styles_to_css(changes)
        if not css_props:
            return []
        return [f"  {selector} {{ {k}: {v}; }}" for k, v in css_props.items()]

    def _apply_inline(self, changes: dict) -> list:
        css_props = StyleConverter.ir_styles_to_css(changes)
        if not css_props:
            return []
        style_str = "; ".join(f"{k}: {v}" for k, v in css_props.items())
        return [f'  style="{style_str}"']

    def generate_patch_report(self, diff: dict) -> str:
        """產生可讀的 patch 報告."""
        lines = [
            "═══════════════════════════════════════════════════════",
            "  Figma → Code Patch Report",
            "═══════════════════════════════════════════════════════",
            "",
        ]
        for figma_name, changes in diff.items():
            status = changes.get("_status")
            if status == "added":
                lines.append(f"  ✨ NEW: {figma_name}")
                continue
            if status == "deleted":
                lines.append(f"  🗑️  DEL: {figma_name}")
                continue
            lines.append(f"  📝 CHANGED: {figma_name}")
            mapping = self.name_mapping.get(figma_name) or {}
            if mapping.get("selector"):
                lines.append(f"     selector: {mapping['selector']}")
            for prop, change in changes.items():
                if prop.startswith("_"):
                    continue
                before = change.get("before", "—")
                after = change.get("after", "—")
                lines.append(f"     {prop}: {before} → {after}")
            if self.style_strategy == "tailwind":
                tw = StyleConverter.ir_styles_to_tailwind(changes)
                if tw:
                    lines.append(f"     tailwind: {' '.join(tw)}")
            else:
                css = StyleConverter.ir_styles_to_css(changes)
                if css:
                    for k, v in css.items():
                        lines.append(f"     css: {k}: {v};")
            lines.append("")
        lines.append("═══════════════════════════════════════════════════════")
        lines.append(f"  Total changes: {len(diff)}")
        lines.append("═══════════════════════════════════════════════════════")
        return "\n".join(lines)
