"""
命名引擎 — Figma 圖層 100% 命名控制

優先順序：data-figma-name → 組件名 → id → 語意 class → ARIA/tag → fallback
"""

import re
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class NamingConfig:
    """命名引擎設定."""
    separator: str = "/"
    strategy: str = "component-hierarchy"
    ignore_class_prefixes: list = field(default_factory=lambda: [
        "flex", "grid", "block", "inline", "hidden", "relative", "absolute",
        "fixed", "sticky", "overflow", "z-", "opacity-",
        "w-", "h-", "min-w-", "min-h-", "max-w-", "max-h-",
        "p-", "px-", "py-", "pt-", "pr-", "pb-", "pl-",
        "m-", "mx-", "my-", "mt-", "mr-", "mb-", "ml-",
        "gap-", "space-",
        "text-", "font-", "leading-", "tracking-", "align-",
        "bg-", "from-", "via-", "to-", "gradient-",
        "border-", "rounded-", "ring-", "outline-",
        "shadow-", "blur-", "brightness-", "contrast-",
        "transition-", "duration-", "ease-", "delay-",
        "animate-", "transform-", "scale-", "rotate-", "translate-",
        "cursor-", "select-", "pointer-events-",
        "sm:", "md:", "lg:", "xl:", "2xl:", "dark:", "hover:", "focus:",
        "group-", "peer-",
    ])
    semantic_tags: dict = field(default_factory=lambda: {
        "nav": "Nav", "header": "Header", "footer": "Footer", "main": "Main",
        "aside": "Sidebar", "section": "Section", "article": "Article",
        "form": "Form", "button": "Button", "input": "Input",
        "textarea": "TextArea", "select": "Select", "img": "Image",
        "video": "Video", "audio": "Audio", "canvas": "Canvas", "svg": "SVG",
        "table": "Table", "ul": "List", "ol": "OrderedList", "li": "ListItem",
        "a": "Link",
        "h1": "Heading1", "h2": "Heading2", "h3": "Heading3",
        "h4": "Heading4", "h5": "Heading5", "h6": "Heading6",
        "p": "Paragraph", "span": "Text", "label": "Label", "dialog": "Dialog",
    })
    custom_overrides: dict = field(default_factory=dict)


class NamingEngine:
    """將 DOM 節點轉成可完全控制的 Figma 圖層名稱."""

    def __init__(self, config: Optional[NamingConfig] = None):
        self.config = config or NamingConfig()
        self._sibling_counters: dict[str, dict[str, int]] = {}

    def resolve_name(
        self,
        *,
        parent_path: str,
        tag: str,
        attrs: dict,
        component_name: Optional[str] = None,
        sibling_index: int = 0,
        sibling_tag_count: int = 1,
    ) -> str:
        """解析單一節點的 Figma 圖層名稱（可含階層路徑，如 LoginPage/Header/Title）."""
        sep = self.config.separator
        local_name = self._resolve_local_name(
            tag=tag,
            attrs=attrs,
            component_name=component_name,
            sibling_index=sibling_index,
            sibling_tag_count=sibling_tag_count,
        )
        if parent_path:
            return f"{parent_path}{sep}{local_name}"
        return local_name

    def _resolve_local_name(
        self,
        *,
        tag: str,
        attrs: dict,
        component_name: Optional[str],
        sibling_index: int,
        sibling_tag_count: int,
    ) -> str:
        # 1. data-figma-name
        explicit_name = attrs.get("data-figma-name", "").strip()
        if explicit_name:
            return self._sanitize(explicit_name)
        # 2. Vue/React 組件名
        if component_name and component_name not in ("div", "span", "template"):
            return self._to_pascal_case(component_name)
        # 3. id
        node_id = attrs.get("id", "").strip()
        if node_id:
            return self._to_pascal_case(node_id)
        # 4. 語意 class
        class_name = self._extract_semantic_class(attrs.get("class", ""))
        if class_name:
            return self._to_pascal_case(class_name)
        # 5. ARIA role
        role = attrs.get("role", "").strip()
        if role:
            return self._to_pascal_case(role)
        # 6. 語意 HTML tag
        semantic = self.config.semantic_tags.get(tag.lower())
        if semantic:
            if sibling_tag_count > 1:
                return f"{semantic}_{sibling_index + 1}"
            return semantic
        # 7. fallback
        if sibling_tag_count > 1:
            return f"{tag}_{sibling_index + 1}"
        return tag

    def _extract_semantic_class(self, class_string: str) -> Optional[str]:
        if not class_string:
            return None
        for cls in class_string.strip().split():
            if not self._is_utility_class(cls):
                return cls
        return None

    def _is_utility_class(self, cls: str) -> bool:
        cls_lower = cls.lower()
        for prefix in self.config.ignore_class_prefixes:
            if cls_lower.startswith(prefix.lower()):
                return True
        if len(cls) <= 2 or cls.isdigit():
            return True
        return False

    def _to_pascal_case(self, s: str) -> str:
        s = re.sub(r'[^a-zA-Z0-9]', ' ', s)
        words = s.split()
        return ''.join(w.capitalize() for w in words) if words else s

    def _sanitize(self, name: str) -> str:
        return name.strip()


class VueComponentDetector:
    """掃描 Vue SFC 取得組件名稱對應."""

    def __init__(self, src_root: str):
        self.src_root = src_root
        self._component_map: dict[str, str] = {}

    def scan_project(self) -> dict[str, str]:
        import os
        for root, _, files in os.walk(self.src_root):
            for f in files:
                if f.endswith('.vue'):
                    filepath = os.path.join(root, f)
                    self._component_map[filepath] = self._extract_component_name(filepath, f)
        return self._component_map

    def _extract_component_name(self, filepath: str, filename: str) -> str:
        try:
            with open(filepath, 'r', encoding='utf-8') as fh:
                content = fh.read()
            match = re.search(r'''name\s*:\s*['"]([^'"]+)['"]''', content)
            if match:
                return match.group(1)
            match = re.search(r'''defineOptions\(\s*\{\s*name\s*:\s*['"]([^'"]+)['"]''', content)
            if match:
                return match.group(1)
        except (IOError, UnicodeDecodeError):
            pass
        return NamingEngine()._to_pascal_case(filename.replace('.vue', ''))


class ReactComponentDetector:
    """掃描 React/TSX 取得組件名稱對應."""

    def __init__(self, src_root: str):
        self.src_root = src_root
        self._component_map: dict[str, str] = {}

    def scan_project(self) -> dict[str, str]:
        import os
        for root, _, files in os.walk(self.src_root):
            for f in files:
                if f.endswith(('.tsx', '.jsx')) and not f.endswith('.test.tsx'):
                    filepath = os.path.join(root, f)
                    self._component_map[filepath] = self._extract_component_name(filepath, f)
        return self._component_map

    def _extract_component_name(self, filepath: str, filename: str) -> str:
        try:
            with open(filepath, 'r', encoding='utf-8') as fh:
                content = fh.read()
            for pattern in [
                r'export\s+default\s+function\s+(\w+)',
                r'export\s+default\s+class\s+(\w+)',
                r'export\s+default\s+(\w+)',
            ]:
                match = re.search(pattern, content)
                if match:
                    return match.group(1)
        except (IOError, UnicodeDecodeError):
            pass
        return NamingEngine()._to_pascal_case(re.sub(r'\.(tsx|jsx)$', '', filename))


def preview_naming_tree(ir_tree: dict, indent: int = 0) -> str:
    """除錯用：印出 IR 命名樹."""
    lines = []
    prefix = "  " * indent
    name = ir_tree.get("figmaName", "???")
    ftype = ir_tree.get("figmaType", "?")
    tag = ir_tree.get("htmlTag", "")
    comp = ir_tree.get("componentRef", "")
    label = f"{prefix}├─ {name}  [{ftype}]"
    if comp:
        label += f"  <{comp}>"
    elif tag:
        label += f"  <{tag}>"
    lines.append(label)
    for child in ir_tree.get("children", []):
        lines.append(preview_naming_tree(child, indent + 1))
    return "\n".join(lines)
