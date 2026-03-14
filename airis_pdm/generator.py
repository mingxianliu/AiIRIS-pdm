"""
Generator — Figma → new frontend (React/Vue/HTML/Flutter).

Uses Figma layer name rules: Component/Variant.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional, TYPE_CHECKING

from .figma_reader import FigmaAPIClient, FigmaToIR

if TYPE_CHECKING:
    from .theme_manager import ThemeManager


@dataclass
class ComponentSpec:
    name: str
    variants: Dict[str, dict]


@dataclass
class StyleSheet:
    prefix: str
    counter: int = 0
    rules: Dict[str, Dict[str, str]] = None
    theme_manager: Optional["ThemeManager"] = None

    def __post_init__(self) -> None:
        if self.rules is None:
            self.rules = {}

    def add_node(self, node: dict) -> str:
        self.counter += 1
        base = _kebab(node.get("figmaName", "node"))
        class_name = f"{self.prefix}-{base}-{self.counter}"
        self.rules[class_name] = _style_dict(node, self.theme_manager)
        return class_name

    def to_css(self) -> str:
        blocks = []
        for class_name, styles in self.rules.items():
            if not styles:
                continue
            body = "\n".join(f"  {prop}: {val};" for prop, val in styles.items())
            blocks.append(f".{class_name} {{\n{body}\n}}")
        return "\n\n".join(blocks) + "\n" if blocks else ""


@dataclass
class StyleBundle:
    sheets: list

    def add(self, sheet: StyleSheet) -> None:
        self.sheets.append(sheet)

    def to_css(self) -> str:
        return "\n".join(sheet.to_css() for sheet in self.sheets if sheet.to_css())


def _sanitize_name(name: str) -> str:
    safe = "".join(ch if ch.isalnum() else " " for ch in name).strip()
    if not safe:
        return "Unnamed"
    parts = [p for p in safe.split() if p]
    return "".join(p[:1].upper() + p[1:] for p in parts)


def _kebab(name: str) -> str:
    out = []
    for ch in name:
        if ch.isalnum():
            out.append(ch.lower())
        else:
            out.append("-")
    slug = "".join(out).strip("-")
    while "--" in slug:
        slug = slug.replace("--", "-")
    return slug or "unnamed"


def parse_component_variant(layer_name: str) -> tuple[str, str]:
    parts = [p.strip() for p in layer_name.split("/") if p.strip()]
    if not parts:
        return "Unnamed", "Default"
    component = parts[0]
    variant = parts[1] if len(parts) > 1 else "Default"
    return component, variant


def select_pages(document: dict, page_name: Optional[str], page_index: Optional[int], all_pages: bool) -> list:
    pages = document.get("children", [])
    if not pages:
        return []
    if all_pages:
        return pages
    if page_name:
        for page in pages:
            if page.get("name") == page_name:
                return [page]
        return []
    if page_index is not None:
        if 0 <= page_index < len(pages):
            return [pages[page_index]]
        return []
    return [pages[0]]


def _collect_components(node: dict, components: Dict[str, ComponentSpec]) -> None:
    if not node:
        return
    figma_type = node.get("figmaType")
    node_name = node.get("figmaName", "Unnamed")
    component, variant = parse_component_variant(node_name)
    component_name = _sanitize_name(component)

    if figma_type in ("COMPONENT", "INSTANCE") or "/" in node_name:
        spec = components.get(component_name)
        if not spec:
            spec = ComponentSpec(name=component_name, variants={})
            components[component_name] = spec
        if variant not in spec.variants:
            spec.variants[variant] = node

    for child in node.get("children", []):
        _collect_components(child, components)


def _css_align(value: str, axis: str) -> str:
    if value == "CENTER":
        return "center"
    if value == "MAX":
        return "flex-end"
    if value == "SPACE_BETWEEN" and axis == "primary":
        return "space-between"
    if value == "STRETCH" and axis == "counter":
        return "stretch"
    return "flex-start"


_FONT_WEIGHT_MAP = {
    "thin": "100", "extralight": "200", "light": "300", "normal": "400",
    "regular": "400", "medium": "500", "semibold": "600", "bold": "700",
    "extrabold": "800", "black": "900",
}


def _css_font_weight(value) -> str:
    """Convert fontWeight to CSS value — handles int, str-number, or name like 'bold'."""
    if isinstance(value, (int, float)):
        return str(int(value))
    s = str(value).strip().lower()
    if s.isdigit():
        return s
    return _FONT_WEIGHT_MAP.get(s, "400")


def _style_dict(node: dict, theme_manager: Optional["ThemeManager"] = None) -> Dict[str, str]:
    styles: Dict[str, str] = {"box-sizing": "border-box"}
    layout = node.get("layout", {})
    width = layout.get("width")
    height = layout.get("height")
    if width:
        styles["width"] = f"{int(width)}px"
    if height:
        styles["height"] = f"{int(height)}px"

    ir_styles = node.get("styles", {}) or {}
    if ir_styles.get("backgroundColor"):
        val = ir_styles["backgroundColor"]
        styles["background-color"] = theme_manager.resolve_color(val) if theme_manager else val
    if ir_styles.get("opacity") is not None:
        styles["opacity"] = str(ir_styles["opacity"])
    if ir_styles.get("borderRadius"):
        br = ir_styles["borderRadius"]
        styles["border-radius"] = f"{int(br.get('topLeft',0))}px {int(br.get('topRight',0))}px {int(br.get('bottomRight',0))}px {int(br.get('bottomLeft',0))}px"
    if ir_styles.get("border"):
        border = ir_styles["border"]
        width = int(border.get("width", 1))
        color = border.get("color", "#000")
        color = theme_manager.resolve_color(color) if theme_manager else color
        style = "dashed" if border.get("style") == "DASHED" else "solid"
        styles["border"] = f"{width}px {style} {color}"
    if ir_styles.get("shadow"):
        shadow = ir_styles["shadow"][0]
        styles["box-shadow"] = f"{shadow.get('offsetX',0)}px {shadow.get('offsetY',0)}px {shadow.get('blur',0)}px {shadow.get('spread',0)}px {shadow.get('color','rgba(0,0,0,0.2)')}"

    if node.get("autoLayout"):
        al = node["autoLayout"]
        styles["display"] = "flex"
        styles["flex-direction"] = "row" if al.get("direction") == "HORIZONTAL" else "column"
        sp = al.get("spacing", 0)
        styles["gap"] = theme_manager.resolve_spacing(sp) if theme_manager else f"{int(sp)}px"
        styles["padding-top"] = f"{int(al.get('paddingTop',0))}px"
        styles["padding-right"] = f"{int(al.get('paddingRight',0))}px"
        styles["padding-bottom"] = f"{int(al.get('paddingBottom',0))}px"
        styles["padding-left"] = f"{int(al.get('paddingLeft',0))}px"
        styles["justify-content"] = _css_align(al.get("primaryAlign", "MIN"), "primary")
        styles["align-items"] = _css_align(al.get("counterAlign", "MIN"), "counter")

    text = node.get("text")
    if text:
        fs = text.get("fontSize", 14)
        styles["font-size"] = theme_manager.resolve_font_size(fs) if theme_manager else f"{int(fs)}px"
        styles["font-family"] = text.get("fontFamily", "Inter")
        styles["font-weight"] = _css_font_weight(text.get("fontWeight", 400))
        if text.get("lineHeight"):
            styles["line-height"] = f"{int(text['lineHeight'])}px"
        styles["letter-spacing"] = f"{text.get('letterSpacing',0)}px"
        styles["text-align"] = text.get("textAlign", "LEFT").lower()
        color = text.get("color", "#000")
        styles["color"] = theme_manager.resolve_color(color) if theme_manager else color

    return styles


def _render_html(node: dict, sheet: StyleSheet, indent: int = 0) -> str:
    pad = "  " * indent
    tag = "div"
    if node.get("figmaType") == "TEXT":
        content = node.get("text", {}).get("characters", "")
        class_name = sheet.add_node(node)
        return f"{pad}<span class=\"{class_name}\">{content}</span>"

    class_name = sheet.add_node(node)
    children = node.get("children", []) or []
    if not children:
        return f"{pad}<{tag} class=\"{class_name}\"></{tag}>"
    inner = "\n".join(_render_html(child, sheet, indent + 1) for child in children)
    return f"{pad}<{tag} class=\"{class_name}\">\n{inner}\n{pad}</{tag}>"


def _render_vue(node: dict, sheet: StyleSheet, indent: int = 0) -> str:
    pad = "  " * indent
    tag = "div"
    if node.get("figmaType") == "TEXT":
        content = node.get("text", {}).get("characters", "")
        class_name = sheet.add_node(node)
        return f"{pad}<span class=\"{class_name}\">{content}</span>"

    class_name = sheet.add_node(node)
    children = node.get("children", []) or []
    if not children:
        return f"{pad}<{tag} class=\"{class_name}\"></{tag}>"
    inner = "\n".join(_render_vue(child, sheet, indent + 1) for child in children)
    return f"{pad}<{tag} class=\"{class_name}\">\n{inner}\n{pad}</{tag}>"


def _render_react(node: dict, sheet: StyleSheet, indent: int = 0, css_module: bool = False) -> str:
    pad = "  " * indent
    tag = "div"
    if node.get("figmaType") == "TEXT":
        content = node.get("text", {}).get("characters", "")
        class_name = sheet.add_node(node)
        if css_module:
            return f"{pad}<span className={{styles['{class_name}']}}>{content}</span>"
        return f"{pad}<span className=\"{class_name}\">{content}</span>"

    class_name = sheet.add_node(node)
    children = node.get("children", []) or []
    if not children:
        if css_module:
            return f"{pad}<{tag} className={{styles['{class_name}']}}></{tag}>"
        return f"{pad}<{tag} className=\"{class_name}\"></{tag}>"
    inner = "\n".join(_render_react(child, sheet, indent + 1, css_module) for child in children)
    if css_module:
        return f"{pad}<{tag} className={{styles['{class_name}']}}>\n{inner}\n{pad}</{tag}>"
    return f"{pad}<{tag} className=\"{class_name}\">\n{inner}\n{pad}</{tag}>"


def _flutter_color(color: str) -> str:
    if color.startswith("rgba"):
        nums = color[color.find("(") + 1: color.find(")")].split(",")
        r, g, b = [int(float(nums[i])) for i in range(3)]
        a = float(nums[3]) if len(nums) > 3 else 1.0
        alpha = int(a * 255)
        return f"Color(0x{alpha:02x}{r:02x}{g:02x}{b:02x})"
    if color.startswith("rgb"):
        nums = color[color.find("(") + 1: color.find(")")].split(",")
        r, g, b = [int(float(nums[i])) for i in range(3)]
        return f"Color(0xff{r:02x}{g:02x}{b:02x})"
    return "Color(0xff000000)"


def _render_flutter(node: dict, indent: int = 0) -> str:
    pad = "  " * indent
    if node.get("figmaType") == "TEXT":
        text = node.get("text", {})
        content = text.get("characters", "")
        font_size = int(text.get("fontSize", 14))
        weight = int(text.get("fontWeight", 400))
        color = _flutter_color(text.get("color", "rgb(0,0,0)"))
        return (
            f"{pad}Text(\n"
            f"{pad}  '{content}',\n"
            f"{pad}  style: TextStyle(fontSize: {font_size}, fontWeight: FontWeight.w{weight}, color: {color}),\n"
            f"{pad})"
        )

    styles = _style_dict(node)
    width = styles.get("width")
    height = styles.get("height")
    bg = styles.get("background-color")
    br = styles.get("border-radius")

    children = node.get("children", []) or []
    child_str = ""
    if children:
        rendered_children = ",\n".join(_render_flutter(child, indent + 2) for child in children)
        axis = "Axis.horizontal" if node.get("autoLayout", {}).get("direction") == "HORIZONTAL" else "Axis.vertical"
        child_str = (
            f"{pad}  child: Flex(\n"
            f"{pad}    direction: {axis},\n"
            f"{pad}    children: [\n{rendered_children}\n{pad}    ],\n"
            f"{pad}  ),\n"
        )

    decoration = []
    if bg:
        decoration.append(f"color: {_flutter_color(bg)}")
    if br:
        parts = br.split()
        if len(parts) == 4:
            tl = int(parts[0].replace("px", ""))
            decoration.append(f"borderRadius: BorderRadius.circular({tl})")

    decoration_str = ""
    if decoration:
        decoration_str = f"decoration: BoxDecoration({', '.join(decoration)}),"

    width_str = f"width: {width.replace('px','')}," if width else ""
    height_str = f"height: {height.replace('px','')}," if height else ""

    return (
        f"{pad}Container(\n"
        f"{pad}  {width_str}\n"
        f"{pad}  {height_str}\n"
        f"{pad}  {decoration_str}\n"
        f"{child_str}"
        f"{pad})"
    )


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _build_html_page(title: str, body: str, css_path: str) -> str:
    return (
        "<!doctype html>\n"
        "<html>\n<head>\n  <meta charset=\"utf-8\">\n  <title>" + title + "</title>\n"
        f"  <link rel=\"stylesheet\" href=\"{css_path}\">\n"
        "</head>\n<body>\n" + body + "\n</body>\n</html>\n"
    )

def _visually_hidden_css() -> str:
    return (
        ".visually-hidden {\n"
        "  position: absolute;\n"
        "  width: 1px;\n"
        "  height: 1px;\n"
        "  padding: 0;\n"
        "  margin: -1px;\n"
        "  overflow: hidden;\n"
        "  clip: rect(0, 0, 0, 0);\n"
        "  white-space: nowrap;\n"
        "  border: 0;\n"
        "}\n"
    )


def _write_app_css(
    base: Path,
    content: str,
    include_utility_css: bool,
    theme_manager: Optional["ThemeManager"] = None,
) -> None:
    if theme_manager:
        content = theme_manager.to_css_root() + "\n\n" + content
    if include_utility_css:
        app_css = "@import './utility.css';\n\n" + content
        _write(base / "styles" / "utility.css", _visually_hidden_css())
    else:
        app_css = content
    _write(base / "styles" / "app.css", app_css)


def generate_project(
    figma_token: str,
    file_key: str,
    target: str,
    output_dir: str,
    page_name: Optional[str] = None,
    page_index: Optional[int] = None,
    all_pages: bool = False,
    include_utility_css: bool = False,
) -> None:
    client = FigmaAPIClient(figma_token)
    figma_data = client.get_file(file_key)
    document = figma_data.get("document", {})
    pages = select_pages(document, page_name, page_index, all_pages)
    if not pages:
        raise ValueError("No matching Figma pages found.")

    converter = FigmaToIR()
    multi_page_html = target.lower() == "html" and all_pages
    html_bundle = StyleBundle(sheets=[]) if multi_page_html else None
    index_body = ""
    index_title = "Index"
    html_pages: list[tuple[str, str]] = []

    for page in pages:
        ir_page = converter.convert(page)
        components: Dict[str, ComponentSpec] = {}
        _collect_components(ir_page, components)
        page_title = page.get("name", "Page")
        if multi_page_html and html_bundle is not None:
            sheet = StyleSheet(prefix=_kebab(page_title))
            body = "\n".join(_render_html(child, sheet, 1) for child in ir_page.get("children", []) or [])
            page_slug = _kebab(page_title)
            html = _build_html_page(page_title, body, "../styles/app.css")
            _write(Path(output_dir) / "pages" / f"{page_slug}.html", html)
            html_bundle.add(sheet)
            html_pages.append((page_title, page_slug))
            if not index_body:
                index_body = body
                index_title = page_title
            continue

        _generate_target(
            target,
            output_dir,
            page_title,
            ir_page,
            components,
            include_utility_css=include_utility_css,
        )

    if multi_page_html and html_bundle:
        footer_links = "\n".join(
            f"    <li><a href=\"./pages/{slug}.html\">{title}</a></li>"
            for title, slug in html_pages
        )
        hidden_footer = (
            "<footer class=\"visually-hidden\">\n"
            "  <nav aria-hidden=\"false\">\n"
            "  <ul>\n"
            f"{footer_links}\n"
            "  </ul>\n"
            "  </nav>\n"
            "</footer>"
        )
        index_html = _build_html_page(index_title, index_body + "\n" + hidden_footer, "./styles/app.css")
        _write(Path(output_dir) / "index.html", index_html)
        _write_app_css(Path(output_dir), html_bundle.to_css(), include_utility_css)


def generate_from_ir(
    ir_data: dict,
    target: str = "vue",
    output_dir: str = "./generated",
    page_name: Optional[str] = None,
    with_utility_css: bool = False,
    use_design_tokens: bool = False,
) -> dict:
    """Generate frontend code from IR data (no Figma API needed).

    This is the primary entry point for the Pencil AI pipeline:
    Pencil .pen → IR → generate_from_ir → Vue/React/HTML/Flutter.

    Args:
        ir_data: IR dict — either a single page node (with 'children',
                 'figmaType', 'figmaName') or a multi-page wrapper
                 with 'pages' key.
        target: Output framework — 'vue', 'react', 'html', 'flutter'.
        output_dir: Directory to write generated files.
        page_name: Optional page name; auto-detected from IR if omitted.
        with_utility_css: Include utility CSS.
        use_design_tokens: If True, extract design tokens from IR and output
                           :root CSS variables; generated CSS uses var(--token-*).

    Returns:
        dict with 'files' (list of relative paths written) and 'target'.
    """
    from .theme_manager import ThemeManager

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    files_before = set(_list_files(output_path))

    pages: list[tuple[str, dict]] = []

    # Support multi-page wrapper: {"pages": [{...}, ...]}
    if "pages" in ir_data and isinstance(ir_data["pages"], list):
        for pg in ir_data["pages"]:
            name = pg.get("figmaName") or pg.get("name") or "Page"
            pages.append((name, pg))
    else:
        name = page_name or ir_data.get("figmaName") or ir_data.get("name") or "Page"
        pages.append((name, ir_data))

    theme_manager: Optional["ThemeManager"] = None
    if use_design_tokens and pages:
        theme_manager = ThemeManager()
        theme_manager.load_from_ir({"tree": pages[0][1]})

    for i, (pg_name, ir_page) in enumerate(pages):
        components: Dict[str, ComponentSpec] = {}
        _collect_components(ir_page, components)
        _generate_target(
            target=target,
            output_dir=output_dir,
            page_name=pg_name,
            ir_page=ir_page,
            components=components,
            include_utility_css=with_utility_css,
            theme_manager=theme_manager,
            is_first=(i == 0),
        )

    files_after = set(_list_files(output_path))
    new_files = sorted(str(f.relative_to(output_path)) for f in files_after - files_before)

    return {
        "files": new_files,
        "target": target,
        "output_dir": output_dir,
    }


def _list_files(directory: Path) -> list:
    """Recursively list all files under directory."""
    return [p for p in directory.rglob("*") if p.is_file()]


def _generate_target(
    target: str,
    output_dir: str,
    page_name: str,
    ir_page: dict,
    components: Dict[str, ComponentSpec],
    include_utility_css: bool,
    theme_manager: Optional["ThemeManager"] = None,
    is_first: bool = True,
) -> None:
    target = target.lower()
    base = Path(output_dir)
    page_slug = _kebab(page_name)
    page_children = ir_page.get("children", []) or []
    bundle = StyleBundle(sheets=[])

    if target == "html":
        sheet = StyleSheet(prefix=page_slug, theme_manager=theme_manager)
        body = "\n".join(_render_html(child, sheet, 1) for child in page_children)
        if is_first:
            html = _build_html_page(page_name, body, "./styles/app.css")
            _write(base / "index.html", html)
        else:
            (base / "pages").mkdir(parents=True, exist_ok=True)
            html = _build_html_page(page_name, body, "../styles/app.css")
            _write(base / "pages" / f"{page_slug}.html", html)
        bundle.add(sheet)
        _write_app_css(base, bundle.to_css(), include_utility_css, theme_manager)
        return

    if target == "react":
        page_component_name = _sanitize_name(page_name)
        for spec in components.values():
            comp_file = base / "components" / f"{spec.name}.tsx"
            sheet = StyleSheet(prefix=_kebab(spec.name), theme_manager=theme_manager)
            variants = []
            for variant_name, node in spec.variants.items():
                variant_label = variant_name or "Default"
                variants.append(
                    f"    case '{variant_label}':\n      return (\n{_render_react(node, sheet, 4, True)}\n      );"
                )
            comp_content = (
                f"import styles from './{spec.name}.module.css';\n\n"
                "type Props = { variant?: string };\n\n"
                f"export const {spec.name} = ({{ variant = 'Default' }}: Props) => {{\n"
                "  switch (variant) {\n"
                + "\n".join(variants)
                + "\n    default:\n      return (\n"
                + _render_react(next(iter(spec.variants.values())), sheet, 4, True)
                + "\n      );\n  }\n};\n"
            )
            _write(comp_file, comp_content)
            _write(base / "components" / f"{spec.name}.module.css", sheet.to_css())
            bundle.add(sheet)

        page_sheet = StyleSheet(prefix=page_slug, theme_manager=theme_manager)
        page_body = "\n".join(_render_react(child, page_sheet, 2, True) for child in page_children)
        page_content = (
            f"import styles from './{_sanitize_name(page_name)}.module.css';\n\n"
            f"export const {page_component_name}Page = () => (\n  <div>\n{page_body}\n  </div>\n);\n"
        )
        _write(base / "pages" / f"{page_component_name}.tsx", page_content)
        _write(base / "pages" / f"{page_component_name}.module.css", page_sheet.to_css())
        bundle.add(page_sheet)
        _write_app_css(base, bundle.to_css(), include_utility_css, theme_manager)

        main_content = (
            "import React from 'react';\n"
            "import { createRoot } from 'react-dom/client';\n"
            "import './styles/app.css';\n"
            f"import {{ {page_component_name}Page }} from './pages/{page_component_name}';\n\n"
            "const root = createRoot(document.getElementById('root') as HTMLElement);\n"
            f"root.render(<{page_component_name}Page />);\n"
        )
        _write(base / "main.tsx", main_content)

        index_html = (
            "<!doctype html>\n"
            "<html>\n<head>\n  <meta charset=\"utf-8\">\n  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">\n"
            f"  <title>{page_component_name}</title>\n"
            "</head>\n<body>\n  <div id=\"root\"></div>\n  <script type=\"module\" src=\"./main.tsx\"></script>\n</body>\n</html>\n"
        )
        _write(base / "index.html", index_html)
        return

    if target == "vue":
        page_component_name = _sanitize_name(page_name)
        for spec in components.values():
            comp_file = base / "components" / f"{spec.name}.vue"
            sheet = StyleSheet(prefix=_kebab(spec.name), theme_manager=theme_manager)
            variant_blocks = []
            for variant_name, node in spec.variants.items():
                v = variant_name or "Default"
                variant_blocks.append(
                    f"  <template v-if=\"variant === '{v}'\">\n{_render_vue(node, sheet, 2)}\n  </template>"
                )
            template = "\n".join(variant_blocks)
            comp_content = (
                "<template>\n  <div>\n"
                + template
                + "\n  </div>\n</template>\n\n"
                "<script setup>\n"
                "const props = defineProps({ variant: { type: String, default: 'Default' } });\n"
                "</script>\n\n"
                "<style scoped>\n"
                + sheet.to_css()
                + "</style>\n"
            )
            _write(comp_file, comp_content)
            bundle.add(sheet)

        page_sheet = StyleSheet(prefix=page_slug, theme_manager=theme_manager)
        page_body = "\n".join(_render_vue(child, page_sheet, 2) for child in page_children)
        page_content = (
            f"<template>\n  <div>\n{page_body}\n  </div>\n</template>\n\n"
            "<style scoped>\n"
            + page_sheet.to_css()
            + "</style>\n"
        )
        _write(base / "pages" / f"{page_component_name}.vue", page_content)
        bundle.add(page_sheet)
        _write_app_css(base, bundle.to_css(), include_utility_css, theme_manager)

        app_content = (
            "<template>\n"
            f"  <{page_component_name}Page />\n"
            "</template>\n\n"
            "<script setup>\n"
            f"import {page_component_name}Page from './pages/{page_component_name}.vue';\n"
            "</script>\n\n"
            "<style src=\"./styles/app.css\"></style>\n"
        )
        _write(base / "App.vue", app_content)

        main_content = (
            "import { createApp } from 'vue';\n"
            "import App from './App.vue';\n"
            "import './styles/app.css';\n\n"
            "createApp(App).mount('#app');\n"
        )
        _write(base / "main.ts", main_content)

        index_html = (
            "<!doctype html>\n"
            "<html>\n<head>\n  <meta charset=\"utf-8\">\n  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">\n"
            f"  <title>{page_component_name}</title>\n"
            "</head>\n<body>\n  <div id=\"app\"></div>\n  <script type=\"module\" src=\"./main.ts\"></script>\n</body>\n</html>\n"
        )
        _write(base / "index.html", index_html)
        return

    if target == "flutter":
        for spec in components.values():
            comp_file = base / "lib" / "components" / f"{_kebab(spec.name)}.dart"
            variant_cases = []
            for variant_name, node in spec.variants.items():
                v = variant_name or "Default"
                variant_cases.append(
                    f"      case '{v}':\n        return\n{_render_flutter(node, 4)};"
                )
            comp_content = (
                "import 'package:flutter/widgets.dart';\n\n"
                f"class {spec.name} extends StatelessWidget {{\n"
                "  final String variant;\n"
                f"  const {spec.name}({{super.key, this.variant = 'Default'}});\n\n"
                "  @override\n  Widget build(BuildContext context) {\n"
                "    switch (variant) {\n"
                + "\n".join(variant_cases)
                + "\n      default:\n        return\n"
                + _render_flutter(next(iter(spec.variants.values())), 4)
                + ";\n    }\n  }\n}\n"
            )
            _write(comp_file, comp_content)

        page_file = base / "lib" / "pages" / f"{_kebab(page_name)}.dart"
        page_children_rendered = ",\n".join(_render_flutter(child, 2) for child in page_children)
        page_content = (
            "import 'package:flutter/widgets.dart';\n\n"
            f"class { _sanitize_name(page_name) }Page extends StatelessWidget {{\n"
            f"  const { _sanitize_name(page_name) }Page({{super.key}});\n\n"
            "  @override\n  Widget build(BuildContext context) {\n"
            "    return Column(\n"
            "      children: [\n"
            + page_children_rendered
            + "\n      ],\n    );\n  }\n}\n"
        )
        _write(page_file, page_content)
        return

    raise ValueError(f"Unsupported target: {target}")
