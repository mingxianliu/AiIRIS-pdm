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

    def __init__(self, output_dir: str = "./generated"):
        self._converter = PencilToIR()
        self._output_dir = output_dir

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
