"""
Code Patcher — 將 Figma 變更回寫到原始碼

依 diff 與 nameMapping 找到對應的 Vue/React/HTML 並套用樣式變更。
"""

import re
import os
from pathlib import Path
from typing import Optional


def url_to_local_path(url: str, src_root: str) -> Optional[str]:
    """將 entryUrl（如 http://localhost:5173）嘗試對應到本機 srcRoot 目錄。

    name_mapping 的 sourceFile 目前存的是 entryUrl，而非本機路徑。
    此函數用於 Pull --apply 時，嘗試在 srcRoot 下搜尋對應的檔案。
    若 sourceFile 已是本機路徑（以 / 或 . 開頭且對應檔案存在）則直接使用。
    """
    if not url or not url.strip():
        return None
    # 起頭為 http:// 的 URL 無法直接對應本機路徑
    if url.startswith("http"):
        return None
    # 不是 URL，嘗試當作本機路徑
    p = Path(url)
    if p.is_file():
        return str(p)
    return None


def find_files_by_selector(src_root: str, selector: str, extensions=None) -> list:
    """在 srcRoot 下搜尋包含指定 selector（id or class）的原始碼與樣式檔案。

    Returns: list of matching absolute file paths
    """
    if not src_root or not selector:
        return []
    if extensions is None:
        extensions = {".vue", ".tsx", ".jsx", ".html", ".css", ".scss", ".module.css"}

    # 萃取 id 或 class 名稱，依副檔名類型建立不同 pattern
    html_exts = {".vue", ".tsx", ".jsx", ".html", ".js", ".ts"}
    css_exts = {".css", ".scss"}

    patterns_html = []
    patterns_css = []

    if selector.startswith("#"):
        name = selector[1:]
        # HTML: id="name" 形式
        patterns_html.append(re.compile(rf'\bid=["\']?{re.escape(name)}["\']?'))
        # CSS: #name { 形式
        patterns_css.append(re.compile(rf'#{re.escape(name)}\s*[{{,]'))
    elif selector.startswith("."):
        name = selector[1:]
        # HTML: class="... name ..." 形式
        patterns_html.append(re.compile(rf'\bclass=["\'][^"\']*\b{re.escape(name)}\b'))
        # CSS: .name { 或 .name, 或 .name: 形式
        patterns_css.append(re.compile(rf'\.{re.escape(name)}[\s{{,:#]'))
    else:
        # 一般文字搜尋
        patterns_html.append(re.compile(re.escape(selector)))
        patterns_css.append(re.compile(re.escape(selector)))

    matched = []
    root = Path(src_root)
    if not root.exists():
        return []

    for path in root.rglob("*"):
        if path.suffix not in extensions and ".module.css" not in path.name:
            continue
        try:
            content = path.read_text(encoding="utf-8")
            # 依副檔名選合適 pattern 組
            if path.suffix in css_exts or path.name.endswith(".module.css"):
                if any(p.search(content) for p in patterns_css):
                    matched.append(str(path))
            else:
                if any(p.search(content) for p in patterns_html):
                    matched.append(str(path))
        except (OSError, UnicodeDecodeError):
            continue
    return matched


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
                additions.append(f"bg-[{hex_val}]")
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
                weight_map = {
                    100: "thin", 200: "extralight", 300: "light", 400: "normal",
                    500: "medium", 600: "semibold", 700: "bold",
                    800: "extrabold", 900: "black",
                }
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

    def __init__(
        self,
        name_mapping: dict,
        style_strategy: str = "tailwind",
        src_root: str = "",
        dry_run: bool = False,
    ):
        self.name_mapping = name_mapping
        self.style_strategy = style_strategy
        self.src_root = src_root
        self.dry_run = dry_run  # True = 只產報告，不寫檔
        self.converter = StyleConverter()

    def apply_changes(self, diff: dict) -> dict:
        """套用 diff，真正寫回原始檔。回傳 { filepath: [套用說明] }."""
        summary = {}
        for figma_name, changes in diff.items():
            if changes.get("_status") in ("added", "deleted"):
                continue
            mapping = self.name_mapping.get(figma_name) or self._find_mapping(figma_name)
            if not mapping:
                continue
            source_file = mapping.get("sourceFile", "")
            selector = mapping.get("selector", "")
            if not selector:
                continue

            # 解析本機檔案路徑
            local_path = url_to_local_path(source_file, self.src_root)

            if self.style_strategy == "tailwind":
                applied = self._apply_tailwind(local_path, selector, changes)
            elif self.style_strategy in ("css-modules", "scss"):
                applied = self._apply_css(local_path, selector, changes)
            else:
                applied = self._apply_inline(local_path, selector, changes)

            if applied:
                key = local_path or source_file or selector
                summary.setdefault(key, []).extend(applied)
        return summary

    def _find_mapping(self, figma_name: str) -> Optional[dict]:
        for key, mapping in self.name_mapping.items():
            if key.endswith(figma_name) or figma_name.endswith(key.split("/")[-1]):
                return mapping
        return None

    def _resolve_file(self, local_path: Optional[str], selector: str, exts=None) -> Optional[str]:
        """嘗試找到實際可讀寫的本機檔案路徑."""
        if local_path and Path(local_path).exists():
            return local_path
        # 透過 selector 在 srcRoot 搜尋
        if self.src_root:
            matches = find_files_by_selector(self.src_root, selector, exts)
            if matches:
                return matches[0]
        return None

    def _apply_tailwind(
        self, local_path: Optional[str], selector: str, changes: dict
    ) -> list:
        """在 Vue/JSX/HTML 檔案中依 selector 找到元素，新增 Tailwind class。"""
        new_classes = StyleConverter.ir_styles_to_tailwind(changes)
        if not new_classes:
            return []

        filepath = self._resolve_file(
            local_path, selector, {".vue", ".tsx", ".jsx", ".html"}
        )
        if not filepath:
            return [
                f"  [DRY] selector={selector}: class += {' '.join(new_classes)}"
                " (找不到原始檔，請確認 source.srcRoot 設定)"
            ]

        # 讀取原始檔
        content = Path(filepath).read_text(encoding="utf-8")
        original = content

        # 依 selector 類型找目標元素並加入 class
        if selector.startswith("#"):
            id_name = selector[1:]
            # 找 id="xxx" 並在同行的 class="..." 中加入新 class
            content = self._inject_tailwind_by_id(content, id_name, new_classes)
        elif selector.startswith("."):
            cls_name = selector[1:]
            content = self._inject_tailwind_by_class(content, cls_name, new_classes)

        results = [f"  {selector}: +class {' '.join(new_classes)}"]
        if content != original and not self.dry_run:
            Path(filepath).write_text(content, encoding="utf-8")
            results.append(f"  ✅ Written to {filepath}")
        elif self.dry_run:
            results.append(f"  [DRY-RUN] Would write to {filepath}")
        return results

    def _inject_tailwind_by_id(self, content: str, id_name: str, new_classes: list) -> str:
        """在含有 id="id_name" 的元素行中，把 new_classes 加進 class 屬性。"""
        new_cls_str = " ".join(new_classes)

        def replacer(m):
            tag_content = m.group(0)
            if 'class="' in tag_content:
                return re.sub(
                    r'class="([^"]*)"',
                    lambda cm: f'class="{cm.group(1)} {new_cls_str}"',
                    tag_content,
                    count=1,
                )
            elif "class='" in tag_content:
                return re.sub(
                    r"class='([^']*)'",
                    lambda cm: f"class='{cm.group(1)} {new_cls_str}'",
                    tag_content,
                    count=1,
                )
            # 無 class 屬性 → 在 id 屬性後插入
            return re.sub(
                rf'(id=["\']?{re.escape(id_name)}["\']?)',
                rf'\1 class="{new_cls_str}"',
                tag_content,
                count=1,
            )

        # 匹配含有 id="id_name" 的開始標籤（跨行上限 3 行）
        pattern = re.compile(
            rf"<[a-zA-Z][^>]*\bid=['\"]?{re.escape(id_name)}['\"]?[^>]*>",
            re.DOTALL,
        )
        return pattern.sub(replacer, content)

    def _inject_tailwind_by_class(self, content: str, cls_name: str, new_classes: list) -> str:
        """在含有 class="... cls_name ..." 的元素行中加入 new_classes。"""
        new_cls_str = " ".join(new_classes)

        def replacer(m):
            return m.group(0).replace(
                m.group(1), f"{m.group(1)} {new_cls_str}", 1
            )

        pattern = re.compile(
            rf'class=["\']([^"\']*\b{re.escape(cls_name)}\b[^"\']*)["\']'
        )
        return pattern.sub(replacer, content)

    def _apply_css(
        self, local_path: Optional[str], selector: str, changes: dict
    ) -> list:
        """在 CSS/SCSS 檔案中找到 selector 段落並插入/更新屬性。"""
        css_props = StyleConverter.ir_styles_to_css(changes)
        if not css_props:
            return []

        filepath = self._resolve_file(
            local_path, selector, {".css", ".scss", ".module.css"}
        )
        if not filepath:
            lines = [f"  [DRY] {selector} {{"]
            for k, v in css_props.items():
                lines.append(f"    {k}: {v};")
            lines.append("  } (找不到原始檔)")
            return lines

        content = Path(filepath).read_text(encoding="utf-8")
        original = content

        # 嘗試在現有 selector 區塊內更新屬性
        block_pattern = re.compile(
            rf"{re.escape(selector)}\s*\{{([^}}]*)\}}", re.DOTALL
        )
        match = block_pattern.search(content)
        if match:
            block_body = match.group(1)
            for prop, val in css_props.items():
                prop_pattern = re.compile(
                    rf"({re.escape(prop)}\s*:\s*)[^;]+;", re.MULTILINE
                )
                if prop_pattern.search(block_body):
                    block_body = prop_pattern.sub(rf"\g<1>{val};", block_body)
                else:
                    block_body = block_body.rstrip() + f"\n  {prop}: {val};"
            new_block = f"{selector} {{{block_body}}}"
            content = block_pattern.sub(new_block, content, count=1)
        else:
            # 找不到現有區塊 → 在檔案末尾加入
            new_block = f"\n{selector} {{\n"
            for prop, val in css_props.items():
                new_block += f"  {prop}: {val};\n"
            new_block += "}\n"
            content += new_block

        results = [f"  {selector} {{ {'; '.join(f'{k}: {v}' for k, v in css_props.items())} }}"]
        if content != original and not self.dry_run:
            Path(filepath).write_text(content, encoding="utf-8")
            results.append(f"  ✅ Written to {filepath}")
        elif self.dry_run:
            results.append(f"  [DRY-RUN] Would write to {filepath}")
        return results

    def _apply_inline(
        self, local_path: Optional[str], selector: str, changes: dict
    ) -> list:
        """將樣式以 inline style 方式寫入元素。"""
        css_props = StyleConverter.ir_styles_to_css(changes)
        if not css_props:
            return []

        style_str = "; ".join(f"{k}: {v}" for k, v in css_props.items())
        filepath = self._resolve_file(
            local_path, selector, {".vue", ".tsx", ".jsx", ".html"}
        )
        if not filepath:
            return [f'  [DRY] style="{style_str}" (找不到原始檔)']

        content = Path(filepath).read_text(encoding="utf-8")
        original = content

        if selector.startswith("#"):
            id_name = selector[1:]
            pattern = re.compile(
                rf"(<[a-zA-Z][^>]*\bid=['\"]?{re.escape(id_name)}['\"]?[^>]*?)(/?>)",
                re.DOTALL,
            )
            def replacer(m):
                tag = m.group(1)
                close = m.group(2)
                if "style=" in tag:
                    tag = re.sub(r'style=["\']([^"\']*)["\']',
                                 lambda sm: f'style="{sm.group(1)}; {style_str}"', tag, count=1)
                else:
                    tag += f' style="{style_str}"'
                return tag + close
            content = pattern.sub(replacer, content)

        results = [f'  {selector}: style="{style_str}"']
        if content != original and not self.dry_run:
            Path(filepath).write_text(content, encoding="utf-8")
            results.append(f"  ✅ Written to {filepath}")
        elif self.dry_run:
            results.append(f"  [DRY-RUN] Would write to {filepath}")
        return results

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
            if mapping.get("sourceFile"):
                lines.append(f"     source:   {mapping['sourceFile']}")
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
