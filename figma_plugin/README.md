# Figma Plugin — Code-to-Figma Sync (AiIRIS-pdm)

本目錄為 Figma 外掛，用於載入 AiIRIS-pdm `push` 產出的 `plugin-payload.json`，在 Figma 中建立對應節點並保留命名與 pluginData（供 pull 回寫）。

## 建置

需先產生 `dist/code.js` 與 `dist/ui.html`：

```bash
cd figma_plugin
npm install   # 可選：僅需 TypeScript
npx tsc src/code.ts --outDir dist
cp src/ui.html dist/
```

或使用 npm script（若已加入 package.json）：

```bash
npm run build
```

## 安裝到 Figma

1. 在 Figma 桌面版：Plugins → Development → Import plugin from manifest...
2. 選擇本目錄下的 `manifest.json`（建置後需能讀取到 `dist/code.js` 與 `dist/ui.html`）。
3. 之後在 Plugins → Development 中執行「Code-to-Figma Sync (AiIRIS-pdm)」。

## 使用

1. 在專案根目錄執行 `python -m airis_pdm.cli push http://localhost:5173`，產生 `.figma-sync/plugin-payload.json`。
2. 在 Figma 開啟外掛，於 Import 分頁載入該 JSON（拖放或貼上）。
3. 點「Preview Names」檢查命名樹，再點「Import to Figma」建立圖層。
4. Export 分頁可匯出選取 frame 的節點樹（含 pluginData），供除錯或回寫對照。

## 相容性

Plugin 使用的 `sharedPluginData` 命名空間為 `figma-code-sync`，與 figma-code-sync 及 AiIRIS-pdm 的 pull 流程相容。

---

## MCP 整合 — AI Agent 呼叫流程

`AiIRIS-pdm` 提供 `FigmaMcpTools`，讓 AI Agent（Claude / Cursor / AiIRIS-hub 等）透過 MCP 協議直接操作 Figma 設計稿，無需手動執行 CLI。

### 完整流程圖

```
Figma 設計稿
    │  Figma Plugin（push 建立快照）
    │  airis_pdm push http://localhost:5173
    ▼
.figma-sync/
    ├── {node_id}/ir.json       ← 快照
    └── plugin-payload.json     ← Plugin 載入用

AI Agent（Claude / Cursor / Hub）
    │  MCP 呼叫
    ▼
FigmaMcpTools（airis_pdm/figma_mcp_tools.py）
    ├── get_figma_ir(file_key, node_id)        → 讀取設計稿 IR
    ├── diff_ir_with_snapshot(file_key, node_id) → 比對變更
    ├── get_design_tokens(file_key, node_id)   → 擷取設計 Token
    ├── get_ir_completeness(file_key, node_id) → 完整度評分
    └── list_snapshots()                       → 列出本地快照
         │
         ▼
    FigmaAPIClient（呼叫 Figma REST API）
    FigmaToIR（轉換 IR 格式）
    IRDiffer（比對差異）
```

### Python 直接使用

```python
from airis_pdm.figma_mcp_tools import FigmaMcpTools
import json

tools = FigmaMcpTools(token="YOUR_FIGMA_TOKEN", snapshot_dir=".figma-sync")

# 取得 IR
result = json.loads(tools.get_figma_ir("abc123", "1:2"))
if result["status"] == "ok":
    print(result["data"]["figmaType"])

# 比對 diff（需先有快照）
diff = json.loads(tools.diff_ir_with_snapshot("abc123", "1:2"))
if diff["data"]["hasChanges"]:
    print(diff["data"]["changes"])

# 取得設計 Token
tokens = json.loads(tools.get_design_tokens("abc123", "0:1"))
print(tokens["data"]["colors"])
```

### Hub Plugin 整合（透過 mcpRouter）

Hub 的 PDM Plugin 已實作 `get_mcp_tools()`，可透過 `McpRouter` 直接呼叫：

```python
from hub.core.mcp_router import McpRouter

router = McpRouter(plugin_registry)
tools = router.list_tools()     # 取得所有工具清單
# 工具名稱：pdm.get_figma_ir / pdm.diff_ir_with_snapshot / ...

result = await router.call_tool("pdm.get_figma_ir", {
    "file_key": "abc123",
    "node_id": "1:2",
})
```

### 工具權限設定（.claude/settings.local.json）

在專案根目錄設定白名單，限制 AI 只能呼叫核准的工具：

```json
{
  "permissions": {
    "allow": [
      "mcp__figma__get_design_context"
    ]
  }
}
```

