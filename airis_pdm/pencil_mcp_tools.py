"""
Pencil MCP Tools — 將 airis_pdm 的 PencilAI 整合能力包裝成工具

這套工具讓 AI Agent 能夠直接操作 .pen 檔案，並與 AiIRIS-pdm 的生成器對接。
支援設計合規檢查、視覺回歸（Playwright 截圖比對）與設計標記 (Design Tokens)。
"""

import asyncio
import json
import os
from datetime import datetime, timezone
from typing import Any, List, Optional

from .pencil_reader import PencilToIR
from .generator import generate_from_ir
from .visual_compliance import run_visual_compliance, VisualComplianceResult

def _ok(data: Any) -> str:
    return json.dumps({"status": "ok", "data": data}, ensure_ascii=False)

def _err(message: str) -> str:
    return json.dumps({"status": "error", "message": message}, ensure_ascii=False)

class PencilMcpTools:
    """
    Focus on PencilAI: 提供 .pen 與代碼生成之間的橋樑。
    """

    def __init__(self, output_dir: str = "./generated", page_name: str = "Page"):
        self._converter = PencilToIR(page_name=page_name)
        self._output_dir = output_dir
        self._page_name = page_name

    # ── 核心 API（與 test_pencil_mcp_tools 對齊） ──

    def get_pen_ir(self, pen_data: Any) -> str:
        """將 Pencil 節點資料轉為 IR v2.0 文件。"""
        try:
            ir_doc = self._converter.convert(pen_data)
            return _ok(ir_doc)
        except Exception as e:
            return _err(f"IR 轉換失敗: {e}")

    def generate_code(self, pen_data: Any, target: str = "vue", output_dir: Optional[str] = None) -> str:
        """從 Pencil 節點資料生成前端代碼（簡化介面）。"""
        out = output_dir or self._output_dir
        try:
            ir_doc = self._converter.convert(pen_data if isinstance(pen_data, (list, dict)) else [pen_data])
            result = generate_from_ir(
                ir_data=ir_doc["tree"],
                target=target,
                output_dir=out,
            )
            return _ok(result)
        except Exception as e:
            return _err(f"生成代碼失敗: {e}")

    def get_design_tokens(self, pen_data: Any) -> str:
        """從 Pencil 節點萃取 design tokens（顏色、字級、字族）。"""
        try:
            ir_doc = self._converter.convert(pen_data if isinstance(pen_data, (list, dict)) else [pen_data])
            tree = ir_doc["tree"]
            colors: list[str] = []
            font_sizes: list[int] = []
            font_families: list[str] = []

            def _walk(node: dict) -> None:
                styles = node.get("styles") or {}
                bg = styles.get("backgroundColor")
                if isinstance(bg, str) and bg:
                    colors.append(bg)
                color = styles.get("color")
                if isinstance(color, str) and color:
                    colors.append(color)
                fills = node.get("fills") or []
                for f in fills:
                    c = f.get("color")
                    if isinstance(c, dict):
                        r, g, b = int(c.get("r", 0) * 255), int(c.get("g", 0) * 255), int(c.get("b", 0) * 255)
                        colors.append(f"rgb({r}, {g}, {b})")
                txt = node.get("text") or {}
                fs = txt.get("fontSize")
                if isinstance(fs, (int, float)) and fs > 0:
                    font_sizes.append(int(fs))
                ff = txt.get("fontFamily")
                if isinstance(ff, str) and ff:
                    font_families.append(ff)
                for child in node.get("children") or []:
                    _walk(child)

            _walk(tree)
            return _ok({
                "colors": sorted(set(colors)),
                "fontSizes": sorted(set(font_sizes)),
                "fontFamilies": sorted(set(font_families)),
            })
        except Exception as e:
            return _err(f"萃取 design tokens 失敗: {e}")

    def get_completeness(self, pen_data: Any) -> str:
        """評估設計稿完整度（節點數、有無樣式、有無文字）。"""
        try:
            ir_doc = self._converter.convert(pen_data if isinstance(pen_data, (list, dict)) else [pen_data])
            tree = ir_doc["tree"]
            node_count = ir_doc["stats"]["nodeCount"]
            has_styles = False
            has_text = False

            def _walk(node: dict) -> None:
                nonlocal has_styles, has_text
                if node.get("styles"):
                    has_styles = True
                if node.get("text", {}).get("characters"):
                    has_text = True
                fills = node.get("fills")
                if fills:
                    has_styles = True
                for child in node.get("children") or []:
                    _walk(child)

            _walk(tree)
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
                "nodeCount": node_count,
                "score": score,
                "hasStyles": has_styles,
                "hasText": has_text,
            })
        except Exception as e:
            return _err(f"完整度評估失敗: {e}")

    def spec_to_design_ops(self, spec: dict) -> str:
        """將 component spec 轉為 Pencil batch_design 操作列表。"""
        try:
            ops: list[str] = []
            name = spec.get("name") or "Component"
            theme = spec.get("theme") or {}
            width = spec.get("width") or 360
            height = spec.get("height") or 780
            bg = theme.get("bg") or "#FFFFFF"
            primary = theme.get("primary") or "#0092B8"
            text_dark = theme.get("textDark") or "#1D293D"
            text_light = theme.get("textLight") or "#FFFFFF"

            ops.append(
                f'root=I("canvas", {{"type":"frame","name":"{name}",'
                f'"width":{width},"height":{height},"fill":"{bg}",'
                f'"layout":"vertical","gap":0,"padding":0}})'
            )

            sections = spec.get("sections") or []
            for idx, sec in enumerate(sections):
                sec_type = (sec.get("type") or "frame").lower()
                if sec_type == "header":
                    title = sec.get("title") or "Header"
                    h = sec.get("height") or 56
                    ops.append(
                        f'sec{idx}=I(root, {{"type":"frame","name":"Header",'
                        f'"width":{width},"height":{h},"fill":"{primary}",'
                        f'"layout":"horizontal","gap":8,"padding":16}})'
                    )
                    ops.append(
                        f'I(sec{idx}, {{"type":"text","name":"HeaderTitle",'
                        f'"content":"{title}","fontSize":18,"fontWeight":600,"color":"{text_light}"}})'
                    )
                elif sec_type == "content":
                    ops.append(
                        f'sec{idx}=I(root, {{"type":"frame","name":"Content",'
                        f'"width":{width},"layout":"vertical","gap":16,"padding":16}})'
                    )
                elif sec_type == "grid":
                    cols = sec.get("columns") or 2
                    items = sec.get("items") or []
                    ops.append(
                        f'sec{idx}=I(root, {{"type":"frame","name":"Grid",'
                        f'"width":{width},"layout":"horizontal","gap":12,"padding":16}})'
                    )
                    for j, item in enumerate(items):
                        label = item.get("label") or f"Item{j}"
                        icon = item.get("icon")
                        cell_w = (width - 32 - 12 * (cols - 1)) // cols
                        ops.append(
                            f'cell{idx}_{j}=I(sec{idx}, {{"type":"frame","name":"GridCell-{label}",'
                            f'"width":{cell_w},"layout":"vertical","gap":8,"padding":12,"fill":"#F1F5F9"}})'
                        )
                        if icon:
                            ops.append(
                                f'I(cell{idx}_{j}, {{"type":"icon_font","name":"Icon-{label}",'
                                f'"content":"{icon}","fontSize":24,"color":"{primary}"}})'
                            )
                        ops.append(
                            f'I(cell{idx}_{j}, {{"type":"text","name":"Label-{label}",'
                            f'"content":"{label}","fontSize":14,"color":"{text_dark}"}})'
                        )
                elif sec_type == "card":
                    title = sec.get("title") or "Card"
                    content = sec.get("content") or ""
                    ops.append(
                        f'sec{idx}=I(root, {{"type":"frame","name":"Card-{title}",'
                        f'"width":{width - 32},"layout":"vertical","gap":8,"padding":16,"fill":"#FFFFFF"}})'
                    )
                    ops.append(
                        f'I(sec{idx}, {{"type":"text","name":"CardTitle-{title}",'
                        f'"content":"{title}","fontSize":16,"fontWeight":600,"color":"{text_dark}"}})'
                    )
                    if content:
                        ops.append(
                            f'I(sec{idx}, {{"type":"text","name":"CardContent-{title}",'
                            f'"content":"{content}","fontSize":14,"color":"{text_dark}"}})'
                        )
                elif sec_type == "list":
                    title = sec.get("title") or "List"
                    items = sec.get("items") or []
                    ops.append(
                        f'sec{idx}=I(root, {{"type":"frame","name":"List-{title}",'
                        f'"width":{width},"layout":"vertical","gap":0,"padding":16}})'
                    )
                    for j, item in enumerate(items):
                        item_title = item.get("title") or f"Item{j}"
                        subtitle = item.get("subtitle") or ""
                        ops.append(
                            f'row{idx}_{j}=I(sec{idx}, {{"type":"frame","name":"Row-{item_title}",'
                            f'"width":{width - 32},"layout":"vertical","gap":2,"padding":12}})'
                        )
                        ops.append(
                            f'I(row{idx}_{j}, {{"type":"text","name":"RowTitle-{item_title}",'
                            f'"content":"{item_title}","fontSize":16,"color":"{text_dark}"}})'
                        )
                        if subtitle:
                            ops.append(
                                f'I(row{idx}_{j}, {{"type":"text","name":"RowSub-{item_title}",'
                                f'"content":"{subtitle}","fontSize":12,"color":"#94A3B8"}})'
                            )
                elif sec_type == "navbar":
                    items = sec.get("items") or []
                    ops.append(
                        f'sec{idx}=I(root, {{"type":"frame","name":"NavBar",'
                        f'"width":{width},"height":56,"layout":"horizontal","gap":0,"padding":0,"fill":"#FFFFFF"}})'
                    )
                    tab_w = width // max(len(items), 1)
                    for j, item in enumerate(items):
                        label = item.get("label") or f"Tab{j}"
                        icon = item.get("icon")
                        ops.append(
                            f'tab{idx}_{j}=I(sec{idx}, {{"type":"frame","name":"Tab-{label}",'
                            f'"width":{tab_w},"layout":"vertical","gap":4,"padding":8}})'
                        )
                        if icon:
                            ops.append(
                                f'I(tab{idx}_{j}, {{"type":"icon_font","name":"TabIcon-{label}",'
                                f'"content":"{icon}","fontSize":20,"color":"{primary}"}})'
                            )
                        ops.append(
                            f'I(tab{idx}_{j}, {{"type":"text","name":"TabLabel-{label}",'
                            f'"content":"{label}","fontSize":10,"color":"{text_dark}"}})'
                        )

            return _ok({
                "operations": ops,
                "description": f"從 spec「{name}」產生 {len(ops)} 個 batch_design 操作",
            })
        except Exception as e:
            return _err(f"spec_to_design_ops 失敗: {e}")

    # ── 進階 API ──

    def generate_code_from_pen(
        self,
        pen_data: List[dict],
        target: str = "vue",
        use_design_tokens: bool = False,
        multi_page: bool = False,
    ) -> str:
        """
        從 Pencil AI 節點資料直接生成前端代碼。

        參數：
            pen_data — 由 mcp_pencil_batch_get 取得的節點列表
            target   — 目標框架 (vue, react, html, flutter)
            use_design_tokens — 若為 True，產出 :root 變數並以 var(--token-*) 取代硬編碼顏色/間距
            multi_page — 若為 True，將多個根節點視為獨立頁面
        """
        try:
            ir_doc = self._converter.convert(pen_data, multi_page=multi_page)
            result = generate_from_ir(
                ir_data=ir_doc["tree"],
                target=target,
                output_dir=self._output_dir,
                use_design_tokens=use_design_tokens,
            )
            return _ok({
                "message": f"成功從 Pencil 節點生成 {target} 代碼",
                "output_dir": os.path.abspath(self._output_dir),
                "generated_files": result["files"],
            })
        except Exception as e:
            return _err(f"生成代碼失敗: {str(e)}")

    def validate_design_system_compliance(self, pen_data: List[dict]) -> str:
        """
        檢查 Pencil 設計稿是否符合設計系統規範。
        """
        try:
            ir_doc = self._converter.convert(pen_data)
            tree = ir_doc["tree"]
            
            # 簡單檢查：是否有 Auto Layout, 是否有正確的命名
            node_count = ir_doc["stats"]["nodeCount"]
            issues = []
            
            def check_recursive(node):
                if node.get("figmaType") == "FRAME" and not node.get("autoLayout"):
                    # 如果不是葉子節點且沒有 Auto Layout
                    if node.get("children"):
                         issues.append(f"警告: 節點 '{node['figmaName']}' 缺少 Auto Layout")
                for child in node.get("children", []):
                    check_recursive(child)
            
            check_recursive(tree)
            
            score = max(0, 100 - len(issues) * 10)
            return _ok({
                "score": score,
                "node_count": node_count,
                "issues": issues,
                "summary": "設計合規度評分完成"
            })
        except Exception as e:
            return _err(f"驗證設計失敗: {str(e)}")

    def get_screenshot(self, reference_image_path: str) -> str:
        """
        取得設計稿參考圖路徑，供視覺回歸比對使用。

        若 Pencil 匯出或 MCP 有提供截圖，可回傳該路徑；否則回傳呼叫端提供的 reference 路徑。
        用途：run_visual_compliance 的 reference_image_path 可由此取得。
        """
        if os.path.isfile(reference_image_path):
            return _ok({
                "reference_image_path": os.path.abspath(reference_image_path),
                "message": "使用指定路徑作為設計稿參考圖",
            })
        return _err(f"參考圖不存在: {reference_image_path}")

    def run_visual_compliance(
        self,
        reference_image_path: str,
        live_url: str,
        output_dir: Optional[str] = None,
        pixel_diff_threshold: float = 0.01,
        viewport_width: int = 1280,
        viewport_height: int = 720,
        run_root_cause_on_failure: bool = False,
        workspace_id: str = "default",
    ) -> str:
        """
        執行視覺合規：Playwright 截取 live_url 與參考圖進行像素比對。
        若比對失敗且 run_root_cause_on_failure 為 True，會呼叫 RootCauseAnalyzer 分析差異。
        """
        output_dir = output_dir or self._output_dir
        on_failure = None
        if run_root_cause_on_failure:
            try:
                from ai_tdd_cli.services.analyzer import RootCauseAnalyzer
                analyzer = RootCauseAnalyzer(workspace_id=workspace_id)

                async def _on_failure(error: dict) -> None:
                    await analyzer.analyze(error, [], {})

                on_failure = _on_failure
            except ImportError:
                pass

        try:
            result: VisualComplianceResult = asyncio.run(
                run_visual_compliance(
                    reference_image_path=reference_image_path,
                    live_url=live_url,
                    output_dir=output_dir,
                    pixel_diff_threshold=pixel_diff_threshold,
                    viewport_width=viewport_width,
                    viewport_height=viewport_height,
                    on_failure_analyze=on_failure,
                )
            )
            return _ok({
                "passed": result.passed,
                "diff_ratio": result.diff_ratio,
                "message": result.message,
                "actual_path": result.actual_path,
                "diff_image_path": result.diff_image_path,
            })
        except Exception as e:
            return _err(f"視覺合規檢查失敗: {str(e)}")
