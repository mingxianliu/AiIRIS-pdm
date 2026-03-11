"""
Pencil MCP Tools — 將 airis_pdm 的 Pencil AI 能力包裝成 AI Agent 可呼叫的工具

新工作流：Spec → Pencil AI → Fine-tune → IR → React/Vue Code

使用方式：
    from airis_pdm.pencil_mcp_tools import PencilMcpTools
    tools = PencilMcpTools()

    # 1. 從 .pen 讀取 IR
    ir_json = tools.get_pen_ir(pen_data)

    # 2. 從 IR 產生 code
    result = tools.generate_code(pen_data, target="react", output_dir="./out")

    # 3. 擷取 design tokens
    tokens = tools.get_design_tokens(pen_data)
"""

from __future__ import annotations

import json
from typing import Any, Optional

from .pencil_reader import PencilToIR
from .generator import generate_from_ir
from .design_assets import extract_design_tokens_from_ir, _count_nodes, _has_any_styles, _has_any_text
from .token_export import extract_tokens_from_ir


def _ok(data: object) -> str:
    """統一成功回傳格式。"""
    return json.dumps({"status": "ok", "data": data}, ensure_ascii=False)


def _err(message: str) -> str:
    """統一失敗回傳格式。"""
    return json.dumps({"status": "error", "message": message}, ensure_ascii=False)


class PencilMcpTools:
    """將 airis_pdm 的 Pencil AI 能力包裝成 MCP 工具。

    不需要 API token——所有資料透過 Pencil MCP 的 batch_get 取得，
    以 JSON dict 傳入。

    工作流：
        1. AI agent 用 Pencil MCP batch_get 讀取 .pen 節點
        2. 將節點資料傳入本工具的方法
        3. 取得 IR / 程式碼 / design tokens
    """

    def __init__(self, page_name: str = "Page") -> None:
        self._converter = PencilToIR(page_name=page_name)

    # ─────────────────────────────────────────────────
    # 工具 1：.pen 節點 → IR
    # ─────────────────────────────────────────────────

    def get_pen_ir(self, pen_data: list[dict] | dict) -> str:
        """將 Pencil AI 節點資料轉換為 IR v2.0。

        用途：AI 可讀取 .pen 設計稿的結構化 IR 資料，
        包含 layout、styles、text、autoLayout、children。

        參數：
            pen_data — batch_get 回傳的節點列表或單一節點 dict

        回傳 JSON：
            {
              "status": "ok",
              "data": {
                "version": "2.0.0",
                "tree": { "figmaName": "...", ... },
                "stats": { "nodeCount": 42 }
              }
            }
        """
        try:
            ir_doc = self._converter.convert(pen_data)
            return _ok(ir_doc)
        except Exception as e:
            return _err(f"IR 轉換失敗：{e}")

    # ─────────────────────────────────────────────────
    # 工具 2：.pen → React/Vue/HTML/Flutter 程式碼
    # ─────────────────────────────────────────────────

    def generate_code(
        self,
        pen_data: list[dict] | dict,
        target: str = "react",
        output_dir: str = "./generated",
        page_name: Optional[str] = None,
        with_utility_css: bool = False,
    ) -> str:
        """從 Pencil AI 設計直接產生前端程式碼。

        完整管線：.pen node → IR v2.0 → React/Vue/HTML/Flutter

        參數：
            pen_data        — batch_get 回傳的節點列表或單一節點
            target          — 輸出目標：'react', 'vue', 'html', 'flutter'
            output_dir      — 輸出目錄
            page_name       — 頁面名稱（可選，自動偵測）
            with_utility_css — 是否產出 utility.css

        回傳 JSON：
            {
              "status": "ok",
              "data": {
                "files": ["main.tsx", "pages/Home.tsx", ...],
                "target": "react",
                "output_dir": "./generated"
              }
            }
        """
        try:
            ir_doc = self._converter.convert(pen_data)
            ir_tree = ir_doc.get("tree", {})
            result = generate_from_ir(
                ir_data=ir_tree,
                target=target,
                output_dir=output_dir,
                page_name=page_name,
                with_utility_css=with_utility_css,
            )
            return _ok(result)
        except Exception as e:
            return _err(f"程式碼產生失敗：{e}")

    # ─────────────────────────────────────────────────
    # 工具 3：擷取設計 Token
    # ─────────────────────────────────────────────────

    def get_design_tokens(self, pen_data: list[dict] | dict) -> str:
        """從 Pencil AI 設計擷取 design tokens。

        用途：取得設計稿使用的顏色、字型、字級等 token，
        用於生成符合設計規範的程式碼。

        參數：
            pen_data — batch_get 回傳的節點列表或單一節點

        回傳 JSON：
            {
              "status": "ok",
              "data": {
                "colors": ["rgba(0,146,184,1)", ...],
                "fontSizes": ["14", "16", ...],
                "fontFamilies": ["Inter", ...]
              }
            }
        """
        try:
            ir_doc = self._converter.convert(pen_data)
            tokens = extract_design_tokens_from_ir(ir_doc.get("tree", {}))
            return _ok(tokens)
        except Exception as e:
            return _err(f"Token 擷取失敗：{e}")

    # ─────────────────────────────────────────────────
    # 工具 4：IR 完整度評分
    # ─────────────────────────────────────────────────

    def get_completeness(self, pen_data: list[dict] | dict) -> str:
        """評估 .pen 設計轉換為 IR 後的完整度。

        用途：確認設計是否足夠完整，可用於程式碼產生。

        參數：
            pen_data — batch_get 回傳的節點列表或單一節點

        回傳 JSON：
            {
              "status": "ok",
              "data": {
                "score": 85,
                "nodeCount": 42,
                "hasStyles": true,
                "hasText": true,
                "details": { ... }
              }
            }
        """
        try:
            ir_doc = self._converter.convert(pen_data)
            tree = ir_doc.get("tree", {})
            node_count = _count_nodes(tree)
            has_styles = _has_any_styles(tree)
            has_text = _has_any_text(tree)

            score = 0
            if node_count > 0:
                score += 25
            if node_count > 5:
                score += 25
            if has_styles:
                score += 25
            if has_text:
                score += 25

            return _ok({
                "score": score,
                "nodeCount": node_count,
                "hasStyles": has_styles,
                "hasText": has_text,
            })
        except Exception as e:
            return _err(f"完整度評分失敗：{e}")

    # ─────────────────────────────────────────────────
    # 工具 5：規格 → 批次設計操作
    # ─────────────────────────────────────────────────

    def spec_to_design_ops(self, spec: dict) -> str:
        """將結構化規格轉為 Pencil batch_design 操作指令。

        用途：AI 可將使用者的 UI 規格自動轉為 Pencil 操作，
        加速設計稿產出流程。

        參數：
            spec — 結構化規格，格式：
                {
                    "name": "首頁",
                    "width": 360, "height": 780,
                    "theme": { "primary": "#0092B8", "bg": "#F8FAFC" },
                    "sections": [
                        {
                            "type": "header",
                            "title": "我的應用",
                            "height": 56
                        },
                        {
                            "type": "grid",
                            "columns": 4,
                            "items": [
                                {"label": "首頁", "icon": "home"},
                                ...
                            ]
                        },
                        {
                            "type": "card",
                            "title": "公告",
                            "content": "系統維護通知"
                        },
                        {
                            "type": "list",
                            "items": [
                                {"title": "項目 1", "subtitle": "說明"},
                                ...
                            ]
                        },
                        {
                            "type": "navbar",
                            "items": [
                                {"label": "首頁", "icon": "home"},
                                ...
                            ]
                        }
                    ]
                }

        回傳 JSON：
            {
              "status": "ok",
              "data": {
                "operations": [
                    "root=I(\\"parent\\", {...})",
                    ...
                ],
                "description": "產生了 N 個操作"
              }
            }
        """
        try:
            ops = self._generate_ops(spec)
            return _ok({
                "operations": ops,
                "description": f"產生了 {len(ops)} 個操作",
            })
        except Exception as e:
            return _err(f"操作生成失敗：{e}")

    def _generate_ops(self, spec: dict) -> list[str]:
        """從規格產生 batch_design 操作指令。"""
        ops: list[str] = []
        name = spec.get("name", "App")
        width = spec.get("width", 360)
        height = spec.get("height", 780)
        theme = spec.get("theme", {})
        primary = theme.get("primary", "#0092B8")
        bg = theme.get("bg", "#F8FAFC")
        text_dark = theme.get("textDark", "#1D293D")
        text_light = theme.get("textLight", "#FFFFFF")

        # 根框架
        ops.append(
            f'root=I("parent", {{"type":"frame","name":"{name}",'
            f'"width":{width},"height":{height},'
            f'"fill":"{primary}","layout":"vertical","clip":true,'
            f'"cornerRadius":20}})'
        )

        sections = spec.get("sections", [])
        for i, section in enumerate(sections):
            sec_type = section.get("type", "")
            var = f"sec{i}"

            if sec_type == "header":
                title = section.get("title", "")
                h = section.get("height", 56)
                ops.append(
                    f'{var}=I(root, {{"type":"frame","name":"Header",'
                    f'"width":"fill_container","height":{h},'
                    f'"layout":"horizontal","justifyContent":"space_between",'
                    f'"alignItems":"center","padding":{{"left":16,"right":16}}}})'
                )
                ops.append(
                    f'I({var}, {{"type":"text","content":"{title}",'
                    f'"fontSize":18,"fontWeight":600,"color":"{text_light}"}})'
                )

            elif sec_type == "content":
                ops.append(
                    f'{var}=I(root, {{"type":"frame","name":"Content",'
                    f'"width":"fill_container","height":"fill_container",'
                    f'"fill":"{bg}","layout":"vertical","gap":16,'
                    f'"padding":{{"top":16,"left":16,"right":16,"bottom":16}}}})'
                )

            elif sec_type == "grid":
                cols = section.get("columns", 4)
                items = section.get("items", [])
                ops.append(
                    f'{var}=I(root, {{"type":"frame","name":"Grid",'
                    f'"width":"fill_container","layout":"horizontal",'
                    f'"gap":16,"justifyContent":"space_around",'
                    f'"padding":{{"top":12,"bottom":12}}}})'
                )
                for j, item in enumerate(items):
                    label = item.get("label", "")
                    icon = item.get("icon", "")
                    cell = f"cell{i}_{j}"
                    ops.append(
                        f'{cell}=I({var}, {{"type":"frame","name":"{label}",'
                        f'"layout":"vertical","alignItems":"center","gap":4}})'
                    )
                    if icon:
                        ops.append(
                            f'I({cell}, {{"type":"icon_font","icon":"{icon}",'
                            f'"fontSize":24,"color":"{text_dark}"}})'
                        )
                    ops.append(
                        f'I({cell}, {{"type":"text","content":"{label}",'
                        f'"fontSize":12,"color":"{text_dark}"}})'
                    )

            elif sec_type == "card":
                title = section.get("title", "")
                content = section.get("content", "")
                ops.append(
                    f'{var}=I(root, {{"type":"frame","name":"Card-{title}",'
                    f'"width":"fill_container","layout":"vertical",'
                    f'"fill":"#FFFFFF","cornerRadius":12,"gap":8,'
                    f'"padding":{{"top":16,"left":16,"right":16,"bottom":16}}}})'
                )
                if title:
                    ops.append(
                        f'I({var}, {{"type":"text","content":"{title}",'
                        f'"fontSize":16,"fontWeight":600,"color":"{text_dark}"}})'
                    )
                if content:
                    ops.append(
                        f'I({var}, {{"type":"text","content":"{content}",'
                        f'"fontSize":14,"color":"#64748B"}})'
                    )

            elif sec_type == "list":
                items = section.get("items", [])
                title = section.get("title", "")
                ops.append(
                    f'{var}=I(root, {{"type":"frame","name":"List",'
                    f'"width":"fill_container","layout":"vertical","gap":8}})'
                )
                if title:
                    ops.append(
                        f'I({var}, {{"type":"text","content":"{title}",'
                        f'"fontSize":16,"fontWeight":600,"color":"{text_dark}"}})'
                    )
                for j, item in enumerate(items):
                    t = item.get("title", "")
                    sub = item.get("subtitle", "")
                    row = f"row{i}_{j}"
                    ops.append(
                        f'{row}=I({var}, {{"type":"frame","name":"ListItem-{t}",'
                        f'"width":"fill_container","layout":"horizontal",'
                        f'"fill":"#FFFFFF","cornerRadius":12,'
                        f'"padding":{{"top":12,"left":16,"right":16,"bottom":12}},'
                        f'"alignItems":"center","gap":12}})'
                    )
                    inner = f"inner{i}_{j}"
                    ops.append(
                        f'{inner}=I({row}, {{"type":"frame","layout":"vertical","gap":2}})'
                    )
                    ops.append(
                        f'I({inner}, {{"type":"text","content":"{t}",'
                        f'"fontSize":14,"fontWeight":500,"color":"{text_dark}"}})'
                    )
                    if sub:
                        ops.append(
                            f'I({inner}, {{"type":"text","content":"{sub}",'
                            f'"fontSize":12,"color":"#94A3B8"}})'
                        )

            elif sec_type == "navbar":
                items = section.get("items", [])
                ops.append(
                    f'{var}=I(root, {{"type":"frame","name":"NavBar",'
                    f'"width":"fill_container","height":64,'
                    f'"layout":"horizontal","justifyContent":"space_around",'
                    f'"alignItems":"center",'
                    f'"fill":"rgba(255,255,255,0.95)"}})'
                )
                for j, item in enumerate(items):
                    label = item.get("label", "")
                    icon = item.get("icon", "")
                    tab = f"tab{i}_{j}"
                    ops.append(
                        f'{tab}=I({var}, {{"type":"frame","name":"Tab-{label}",'
                        f'"layout":"vertical","alignItems":"center","gap":2}})'
                    )
                    if icon:
                        ops.append(
                            f'I({tab}, {{"type":"icon_font","icon":"{icon}",'
                            f'"fontSize":24,"color":"#64748B"}})'
                        )
                    ops.append(
                        f'I({tab}, {{"type":"text","content":"{label}",'
                        f'"fontSize":10,"color":"#64748B"}})'
                    )

        return ops
