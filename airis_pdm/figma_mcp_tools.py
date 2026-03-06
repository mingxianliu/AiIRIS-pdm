"""
Figma MCP Tools — 將 airis_pdm 的 Figma 能力包裝成 AI Agent 可呼叫的工具

仿照 FMtest McpTools 設計模式：
  - 每個工具回傳 JSON string（成功或失敗都統一格式）
  - description 說明用途、參數範例、回傳欄位
  - 依功能分層：IR 讀取 / Diff / Design Token / 完整度

使用方式：
    from airis_pdm.figma_mcp_tools import FigmaMcpTools
    tools = FigmaMcpTools(token="YOUR_TOKEN", snapshot_dir=".figma-sync")
    print(tools.get_figma_ir("abc123", "1:2"))
"""

import json
import os
from typing import Optional

from .figma_reader import FigmaAPIClient, FigmaToIR, IRDiffer
from .design_assets import (
    extract_design_tokens_from_ir,
    _count_nodes,
    _has_any_styles,
    _has_any_text,
)


def _ok(data: object) -> str:
    """統一成功回傳格式。"""
    return json.dumps({"status": "ok", "data": data}, ensure_ascii=False)


def _err(message: str) -> str:
    """統一失敗回傳格式。"""
    return json.dumps({"status": "error", "message": message}, ensure_ascii=False)


class FigmaMcpTools:
    """
    將 airis_pdm 的 Figma 能力包裝成 MCP 工具，
    讓 AI Agent（Claude / Cursor 等）可直接呼叫。

    初始化參數：
        token       — Figma Personal Access Token（必填）
        snapshot_dir — 本地快照目錄，預設 '.figma-sync'
        plugin_ns   — Figma Plugin namespace，預設 'figma-code-sync'
    """

    def __init__(
        self,
        token: str,
        snapshot_dir: str = ".figma-sync",
        plugin_ns: str = "figma-code-sync",
    ):
        self._client = FigmaAPIClient(token=token)
        self._to_ir = FigmaToIR(plugin_namespace=plugin_ns)
        self._differ = IRDiffer()
        self._snapshot_dir = snapshot_dir

    # ─────────────────────────────────────────────────
    # 工具 1：取得 Figma 節點的 IR
    # ─────────────────────────────────────────────────

    def get_figma_ir(self, file_key: str, node_id: str) -> str:
        """
        取得 Figma 節點的 IR（中間表示）格式。

        用途：AI 可讀取 Figma 設計稿的結構化資料，
        包含 layout、styles、text、autoLayout、children 等資訊。

        參數：
            file_key — Figma 檔案 Key（如 'abc123XYZ'，從 Figma URL 取得）
            node_id  — 節點 ID（如 '1:2' 或 '10:5'，在 Figma 選取節點後可取得）

        回傳 JSON：
            {
              "status": "ok",
              "data": {
                "figmaName": "...",
                "figmaType": "FRAME|AUTO_LAYOUT|TEXT|...",
                "layout": { "x", "y", "width", "height" },
                "styles": { ... },
                "children": [ ... ]
              }
            }
        """
        try:
            raw = self._client.get_file_nodes(file_key, [node_id])
            nodes = raw.get("nodes", {})
            node_data = nodes.get(node_id, {})
            document = node_data.get("document")
            if not document:
                return _err(f"找不到節點 {node_id}（file_key={file_key}）")
            ir = self._to_ir.convert(document)
            return _ok(ir)
        except Exception as e:
            return _err(str(e))

    # ─────────────────────────────────────────────────
    # 工具 2：與本地快照比對 diff
    # ─────────────────────────────────────────────────

    def diff_ir_with_snapshot(self, file_key: str, node_id: str) -> str:
        """
        比對 Figma 目前版本與本地快照的差異。

        用途：偵測 Figma 設計稿有哪些變更（顏色、字級、layout 等），
        回傳 diff 清單，供 AI 決定是否需要更新程式碼。

        參數：
            file_key — Figma 檔案 Key（如 'abc123XYZ'）
            node_id  — 節點 ID（如 '1:2'）

        快照位置：{snapshot_dir}/{node_id_safe}/ir.json
        （node_id 的 ':' 會被替換為 '_'）

        回傳 JSON：
            {
              "status": "ok",
              "data": {
                "hasChanges": true,
                "changes": {
                  "Header/Title": {
                    "styles.backgroundColor": { "before": "#fff", "after": "#f5f5f5" }
                  }
                }
              }
            }
        """
        try:
            # 取得 Figma 最新 IR
            raw = self._client.get_file_nodes(file_key, [node_id])
            nodes = raw.get("nodes", {})
            document = nodes.get(node_id, {}).get("document")
            if not document:
                return _err(f"找不到節點 {node_id}（file_key={file_key}）")
            after_ir = self._to_ir.convert(document)

            # 讀取本地快照
            node_id_safe = node_id.replace(":", "_")
            snapshot_path = os.path.join(
                self._snapshot_dir, node_id_safe, "ir.json"
            )
            if not os.path.exists(snapshot_path):
                return _err(
                    f"快照不存在：{snapshot_path}，請先執行 push 建立快照。"
                )
            with open(snapshot_path, "r", encoding="utf-8") as f:
                before_ir = json.load(f)

            # Diff
            changes = self._differ.diff(before_ir, after_ir)
            return _ok({"hasChanges": bool(changes), "changes": changes})
        except Exception as e:
            return _err(str(e))

    # ─────────────────────────────────────────────────
    # 工具 3：擷取設計 Token
    # ─────────────────────────────────────────────────

    def get_design_tokens(self, file_key: str, node_id: str) -> str:
        """
        從 Figma 節點擷取設計 Token（顏色、字級、字型）。

        用途：AI 可知道目前設計稿使用的設計系統 token，
        用於生成符合設計規範的程式碼，或確認品牌色是否正確。

        參數：
            file_key — Figma 檔案 Key（如 'abc123XYZ'）
            node_id  — 節點 ID（如 '1:2'），通常傳入頁面或 Frame 根節點

        回傳 JSON：
            {
              "status": "ok",
              "data": {
                "colors": ["rgba(0, 122, 255, 1)", "rgba(255, 255, 255, 1)"],
                "fontSizes": ["14", "16", "24"],
                "fontFamilies": ["Inter", "Noto Sans TC"]
              }
            }
        """
        try:
            raw = self._client.get_file_nodes(file_key, [node_id])
            nodes = raw.get("nodes", {})
            document = nodes.get(node_id, {}).get("document")
            if not document:
                return _err(f"找不到節點 {node_id}（file_key={file_key}）")
            ir = self._to_ir.convert(document)
            tokens = extract_design_tokens_from_ir(ir)
            return _ok(tokens)
        except Exception as e:
            return _err(str(e))

    # ─────────────────────────────────────────────────
    # 工具 4：IR 完整度評分
    # ─────────────────────────────────────────────────

    def get_ir_completeness(self, file_key: str, node_id: str) -> str:
        """
        計算 Figma 節點轉換成 IR 後的完整度評分。

        用途：AI 可評估設計稿的轉換品質，
        判斷是否有節點缺少 Auto Layout、樣式或文字內容，
        並決定是否需要人工修正後再進行後續處理。

        參數：
            file_key — Figma 檔案 Key（如 'abc123XYZ'）
            node_id  — 節點 ID（如 '1:2'）

        回傳 JSON：
            {
              "status": "ok",
              "data": {
                "score": 85,
                "nodeCount": 42,
                "hasStyles": true,
                "hasText": true,
                "layoutWarnings": 3,
                "summary": "良好 — 有少量 NO_AUTO_LAYOUT 警告"
              }
            }
        """
        try:
            raw = self._client.get_file_nodes(file_key, [node_id])
            nodes = raw.get("nodes", {})
            document = nodes.get(node_id, {}).get("document")
            if not document:
                return _err(f"找不到節點 {node_id}（file_key={file_key}）")
            ir = self._to_ir.convert(document)

            node_count = _count_nodes(ir)
            has_styles = _has_any_styles(ir)
            has_text = _has_any_text(ir)
            layout_warnings = _count_layout_warnings(ir)

            score = min(
                100,
                node_count * 2
                + (20 if has_styles else 0)
                + (10 if has_text else 0)
                - layout_warnings * 3,
            )
            score = max(0, score)

            if score >= 80:
                summary = "良好" + (f" — 有 {layout_warnings} 個 NO_AUTO_LAYOUT 警告" if layout_warnings else "")
            elif score >= 50:
                summary = f"普通 — 需檢查（警告：{layout_warnings}，樣式：{'有' if has_styles else '無'}）"
            else:
                summary = "不完整 — 建議重新在 Figma 整理 Auto Layout 後再執行"

            return _ok({
                "score": score,
                "nodeCount": node_count,
                "hasStyles": has_styles,
                "hasText": has_text,
                "layoutWarnings": layout_warnings,
                "summary": summary,
            })
        except Exception as e:
            return _err(str(e))

    # ─────────────────────────────────────────────────
    # 工具 5：列出本地已有的快照節點
    # ─────────────────────────────────────────────────

    def list_snapshots(self) -> str:
        """
        列出本地 snapshot_dir 中已儲存的所有快照節點。

        用途：AI 可知道目前哪些 Figma 節點已有快照可供 diff，
        避免對沒有快照的節點呼叫 diff_ir_with_snapshot 而得到錯誤。

        回傳 JSON：
            {
              "status": "ok",
              "data": {
                "snapshotDir": ".figma-sync",
                "snapshots": [
                  { "nodeId": "1:2", "hasIr": true, "hasScreenshot": false }
                ]
              }
            }
        """
        try:
            if not os.path.isdir(self._snapshot_dir):
                return _ok({"snapshotDir": self._snapshot_dir, "snapshots": []})

            snapshots = []
            for entry in sorted(os.listdir(self._snapshot_dir)):
                entry_path = os.path.join(self._snapshot_dir, entry)
                if not os.path.isdir(entry_path):
                    continue
                node_id = entry.replace("_", ":", 1)
                has_ir = os.path.exists(os.path.join(entry_path, "ir.json"))
                has_screenshot = any(
                    f.endswith((".png", ".jpg", ".webp"))
                    for f in os.listdir(entry_path)
                )
                snapshots.append({
                    "nodeId": node_id,
                    "hasIr": has_ir,
                    "hasScreenshot": has_screenshot,
                })

            return _ok({"snapshotDir": self._snapshot_dir, "snapshots": snapshots})
        except Exception as e:
            return _err(str(e))


# ─────────────────────────────────────────────────────────────────────────────
# 內部輔助
# ─────────────────────────────────────────────────────────────────────────────

def _count_layout_warnings(node: Optional[dict]) -> int:
    """遞迴統計 IR 樹中 NO_AUTO_LAYOUT 警告的數量。"""
    if not node:
        return 0
    count = 1 if node.get("_layoutWarning") == "NO_AUTO_LAYOUT" else 0
    for child in node.get("children", []):
        count += _count_layout_warnings(child)
    return count
