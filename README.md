# AiPdM

**AiIRIS Project Design Model — Spec → Pencil AI → Fine-tune → React/Vue Code**

[![Python](https://img.shields.io/badge/python-3.10%2B-blue)](https://python.org)
[![Version](https://img.shields.io/badge/version-0.5.0-green)](CHANGELOG.md)

從規格出發，透過 Pencil AI 產生 UI 設計，人工微調後直接產出 React / Vue / HTML / Flutter 程式碼。

---

## 新工作流（v0.5.0+）

```
1. 規格（Spec）  →  AI 分析需求，產生結構化 UI 描述
          ↓
2. Pencil AI    →  透過 MCP batch_design 自動建立 .pen 設計稿
          ↓
3. 人工微調     →  在 Pencil AI 編輯器中可視化調整
          ↓
4. 匯出 IR      →  batch_get → PencilToIR → IR v2.0 (JSON)
          ↓
5. 產出程式碼   →  aipdm codegen ir.json --target vue → React/Vue/HTML/Flutter
```

---

## 功能總覽

| 能力 | 說明 |
|------|------|
| **Codegen (IR → Code)** | 從 IR v2.0 或 .pen 匯出 → React/Vue/HTML/Flutter |
| **PencilToIR** | .pen 節點 → IR v2.0 轉換 |
| **PencilMcpTools** | AI Agent 可用的 MCP 工具包 |
| **Spec → Design Ops** | 結構化規格 → Pencil batch_design 操作 |
| **Component/Variant** | `Button/Primary` → Component `Button`、Variant `Primary` |
| **Design Tokens** | 從 IR 擷取顏色/字型/字級 token |
| **Push/Watch** | DOM → IR snapshot（保留，不依賴 Figma） |
| **Figma Console 橋** | **純 Python** WebSocket（`aipdm figma-console`），對齊舊 FigmAI 本機轉發；Figma 內橋接檔仍為 JS（環境限制） |
| **FigmAI 對齊（UiIR）** | **`aipdm figmai`**：`GET /v1/files/...` 匯出的 JSON → UiIR → 既有 `generate_from_ir`（模組：`airis_pdm/figmai`） |

---

## Figma Desktop Console 橋（融入 aipdm，後端單一 Python）

已**移除**倉庫內 TypeScript **`figmai/`** monorepo；改以利兩條 **純 Python** 路徑取代：  
1）**`airis_pdm/figma_console_ws.py`** — 與原 `figma-console-mcp` 相同的 **WebSocket 轉發**（plugin ⇄ client）。  
2）**`airis_pdm/figmai/`** — **UiIR** 與 **`FigmaToIR` 同源**，可將 REST 匯出的節點樹轉成 codegen IR（見下方 **FigmAI import／codegen**）。

### 安裝

```bash
pip install -e ".[figma-console]"   # 含 websockets
```

### 流程

```bash
# 1) 啟動本機代理（預設 3055）
aipdm figma-console serve

# 2) 取得 bridge 檔完整路徑，整段貼到 Figma → Plugins → Development → Open Console
aipdm figma-console bridge-path

# 3) 轉發 RPC（範例）
aipdm figma-console request getSelection
aipdm figma-console request getNode --params '{"nodeId":"1:2","depth":2}'
```

回傳 JSON 若需進 **codegen**，可併用下方 **`aipdm figmai`**（REST File JSON）或 **Pencil → IR** 流程。

### FigmAI import／codegen（Figma File JSON → UiIR → 程式碼）

自 Figma REST API 下載的 **整份 file JSON**（`document` ＋ 內容樹）可先轉成 **UiIR**（`format: aipdm-ui-ir`），再直接走與 `aipdm codegen` 相同的產生器：

```bash
# 由 file JSON 產出 UiIR（預設第一頁；可用 --page-name / --page-index）
aipdm figmai import ./my-figma-file.json -o ui-ir.json

# UiIR → HTML / Vue / React / Flutter
aipdm figmai codegen ui-ir.json --target vue --output ./out

# chain-local（spec → design-ops → UiIR → codegen）
aipdm figmai chain-local ./component-spec.json --target react --output ./out/chain

# chain（remote）：連 figma-console 做節點拉取/同步，再 codegen
aipdm figmai chain ./component-spec.json --figma-node-id "1:2" --host localhost --port 3055 --target vue
aipdm figmai chain ./component-spec.json --sync --host localhost --port 3055 --target react
# chain（idempotent sync）：使用 state.json 做 pencil id ↔ figma id 映射（先 updateNode，不存在再 createNode）
aipdm figmai chain ./component-spec.json --sync --state-dir ./.figmai-state --target vue
# 缺失節點策略：keep / orphan / delete（預設 orphan）
aipdm figmai chain ./component-spec.json --sync --missing-node-strategy delete --target vue
# parent drift 修正：sync 時自動偵測父層偏移並 moveNode
aipdm figmai chain ./component-spec.json --sync --target react

# flow（批次頁面，支援 semantic / pixel）
aipdm figmai flow ./my-figma-file.json --pattern "[Page]" --framework both --fidelity pixel
# flow live（直接走 figma-console）
aipdm figmai flow --live --host localhost --port 3055 --pattern "[Page]" --framework both --fidelity semantic --include login,register --exclude draft
```

**Pixel 模式**支援哪些 Figma 欄位與限制，見 [`docs/PIXEL_RENDERER_COVERAGE.md`](docs/PIXEL_RENDERER_COVERAGE.md)。

**FigmAI 文件索引**：[`docs/SNAPSHOT_PARITY_PROCESS.md`](docs/SNAPSHOT_PARITY_PROCESS.md)（golden／baseline／CI）、[`docs/FIGMA_CONSOLE_OPS.md`](docs/FIGMA_CONSOLE_OPS.md)（本機 figma-console、重試、除錯）、[`docs/SKILLS_CONTRACT.md`](docs/SKILLS_CONTRACT.md)（skills 契約與 golden 維護）。
**第一次上手（chain／flow 一頁版）**：[`docs/QUICKSTART_FIGMAI.md`](docs/QUICKSTART_FIGMAI.md)。

### 一鍵 Live 驗證（收斂命令）

```bash
NODE_IDS="263:3241,263:3242,263:3243" make smoke-live
```

可選覆寫：

```bash
HOST=localhost PORT=3055 DEPTH=8 \
OUTPUT=./.tmp_verify/smoke_live \
BASELINE_REPORT=./tdd-output/smoke-baseline.json \
NODE_IDS="263:3241,263:3242,263:3243" \
make smoke-live
```

底層轉換與 **`FigmaToIR`** 一致，**`style` 欄位**為扁平 CSS 對照（與 `generator._style_dict` 同源邏輯），結構化 **`layout` / `styles` / `text` / `autoLayout`** 一併保留以便無損還原。

---

## 架構

```
                          ┌──────────────┐
                          │  規格 (Spec) │
                          └──────┬───────┘
                                 │
                     ┌───────────▼───────────┐
                     │  Pencil AI (.pen)      │
                     │  MCP batch_design /    │
                     │  batch_get             │
                     └───────────┬───────────┘
                                 │
                     ┌───────────▼───────────┐
                     │  PencilToIR            │
                     │  .pen → IR v2.0 (JSON) │
                     └───────────┬───────────┘
                                 │
              ┌──────────────────▼──────────────────┐
              │           AiIRIS-pdm                │
              │          generate_from_ir            │
              │  • React  • Vue  • HTML  • Flutter  │
              └─────────────────────────────────────┘
```

---

## 快速開始

### 1. 安裝

```bash
git clone https://github.com/mingxianliu/AiIRIS-pdm.git
cd AiIRIS-pdm
pip install -e ".[dev]"
playwright install chromium
# 可選：Figma Console 橋（WebSocket，純 Python）
pip install -e ".[figma-console]"
```

> CI 目前保證 Python **3.10 / 3.11 / 3.12**（Ubuntu + macOS）。若你在本機使用 3.9，可執行但不在 CI 保證範圍內。

## Snapshot / Golden 維護

快照匿名化與 nightly parity 維護流程請見：

- `docs/SNAPSHOT_PARITY_PROCESS.md`
- `docs/FIGMA_CONSOLE_OPS.md`
- `docs/TASK_STATUS_SUMMARY.md`

若要跑真機 smoke，可參考手動 workflow 骨架：

- `.github/workflows/figma-console-smoke-manual.yml`

建議使用指令 **`aipdm`**（AiIRIS PDM CLI）。舊名 `pdm` 仍會安裝但每次執行會印出遷移提示，且易與 [PyPA PDM](https://pdm-project.org/) 套件管理器混淆；另保留別名 `figma-sync`。

### 2. Codegen：IR → React/Vue/HTML/Flutter

```bash
# 從 IR JSON 產生 React
aipdm codegen ir-payload.json --target react --output ./out

# 從 .pen batch_get 匯出的 JSON 產生 Vue
aipdm codegen pen-export.json --target vue --output ./out

# 產生 HTML
aipdm codegen ir-payload.json --target html --output ./out

# 產生 Flutter
aipdm codegen ir-payload.json --target flutter --output ./out

# 可選：產生 utility.css
aipdm codegen ir-payload.json --target react --output ./out --with-utility-css
```

### 3. Push：DOM → IR Snapshot

```bash
aipdm push http://localhost:5173
aipdm push http://localhost:5173 --viewport 375x812
aipdm push http://localhost:5173 --selector '#login-form'
```

### 4. Watch：監聽變更自動 Push

```bash
aipdm watch http://localhost:5173
```

### 5. Export Tokens：IR → Design Tokens

```bash
aipdm export-tokens --from-dir .pdm --output tokens.json
aipdm export-tokens --format css --output tokens.css
```

---

## Python API（for AI Agent）

```python
from airis_pdm import PencilToIR, PencilMcpTools, generate_from_ir

# 1. Pencil → IR
converter = PencilToIR(page_name="首頁")
ir_doc = converter.convert(pen_data)  # pen_data from batch_get

# 2. IR → Code
result = generate_from_ir(
    ir_data=ir_doc["tree"],
    target="vue",
    output_dir="./out",
)

# 3. MCP Tools（AI Agent 使用）
tools = PencilMcpTools(page_name="首頁")
ir_json = tools.get_pen_ir(pen_data)
code_json = tools.generate_code(pen_data, target="react", output_dir="./out")
tokens_json = tools.get_design_tokens(pen_data)

# 4. 從規格產生 Pencil 設計操作
ops_json = tools.spec_to_design_ops({
    "name": "首頁",
    "width": 360, "height": 780,
    "theme": {"primary": "#0092B8", "bg": "#F8FAFC"},
    "sections": [
        {"type": "header", "title": "我的應用", "height": 56},
        {"type": "content"},
        {"type": "navbar", "items": [
            {"label": "首頁", "icon": "home"},
            {"label": "設定", "icon": "settings"},
        ]},
    ],
})
```

---

## CLI 參數

### codegen

| 參數 | 必填 | 說明 |
|------|------|------|
| `ir_file` | 是 | IR v2.0 JSON 或 .pen batch_get 匯出檔 |
| `--target` | 否 | `react` / `vue` / `html` / `flutter`（預設 `html`） |
| `--output` | 否 | 輸出目錄（預設 `./generated`） |
| `--page` | 否 | 頁面名稱 |
| `--with-utility-css` | 否 | 產生 utility.css |

### push

| 參數 | 必填 | 說明 |
|------|------|------|
| `url` | 是 | App URL |
| `--viewport` | 否 | WxH（如 `375x812`） |
| `--selector` | 否 | CSS selector |

---

## 產出結構

- **React**：`index.html`、`main.tsx`、`components/*.tsx`、`pages/*.tsx`、`*.module.css`、`styles/app.css`
- **Vue**：`index.html`、`main.ts`、`App.vue`、`components/*.vue`、`pages/*.vue`、`styles/app.css`
- **HTML**：`index.html`（多頁：`pages/*.html`）+ `styles/app.css`
- **Flutter**：`lib/components/*.dart`、`lib/pages/*.dart`

---

## 設定檔（pencil.config.json）

```json
{
  "pencil": {
    "defaultTarget": "vue",
    "outputDir": "./generated"
  },
  "source": {
    "framework": "vue",
    "styleStrategy": "tailwind",
    "entryUrl": "http://localhost:5173",
    "srcRoot": "./src"
  },
  "viewport": { "width": 375, "height": 812 },
  "naming": { "separator": "/" },
  "export": { "snapshotDir": ".pdm" }
}
```

---

## 專案結構

```
AiIRIS-pdm/
├── README.md
├── CHANGELOG.md
├── pyproject.toml
├── pencil.config.json            # 設定（取代 figma-sync.config.json）
├── airis_pdm/                    # 主套件 (v0.5.0)
│   ├── __init__.py
│   ├── assets/
│   │   └── figma_console_bridge.js  # 貼入 Figma Console 的 bridge（與 Python 代理搭配）
│   ├── figma_console_ws.py       # Figma Console WebSocket 代理（取代 Node figma-console-mcp）
│   ├── figmai/                   # FigmAI 對齊：Figma JSON → UiIR → codegen IR
│   ├── cli.py                    # CLI（建議 `aipdm`）：codegen / push / … / figma-console / figmai
│   ├── config.py                 # 設定載入 + 欄位驗證
│   ├── pencil_reader.py          # ⭐ .pen → IR v2.0 轉換器
│   ├── pencil_mcp_tools.py       # ⭐ AI Agent MCP 工具包
│   ├── generator.py              # IR → React/Vue/HTML/Flutter 程式碼產生
│   ├── dom_extractor.py          # Playwright DOM 擷取（push/watch 用）
│   ├── ir_builder.py             # DOM → IR v2.0
│   ├── naming_engine.py          # 7 層命名引擎
│   ├── code_patcher.py           # IR diff → 原始碼 patch
│   ├── design_assets.py          # ErSlice manifest / completeness
│   ├── token_export.py           # Design token 匯出
│   ├── figma_reader.py           # [DEPRECATED] Figma API
│   └── figma_mcp_tools.py        # [DEPRECATED] Figma MCP tools
├── tests/
├── schemas/
│   └── ir_schema.json            # IR JSON Schema
└── docs/
```

---

## 測試

```bash
pip install -e ".[dev]"
pytest tests/ -v
```

---

## 從 v0.4.0 遷移

v0.5.0 全面棄用 Figma 整合，改用 Pencil AI：

| v0.4.0 (Figma) | v0.5.0 (Pencil AI) |
|-----------------|---------------------|
| `figma-sync generate --file-key ...` | `aipdm codegen ir.json --target vue` |
| `figma-sync pull --file-key ...` | 棄用：改在 Pencil AI 設計 |
| `FigmaAPIClient` | 棄用 |
| `FigmaToIR` | `PencilToIR` |
| `FigmaMcpTools` | `PencilMcpTools` |
| `figma-sync.config.json` | `pencil.config.json` |
| `requests` 依賴 | 已移除（移至 `[legacy]`） |

---

## License

MIT — 見 [LICENSE](LICENSE)。
