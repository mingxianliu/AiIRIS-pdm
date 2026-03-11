# AiIRIS-pdm

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
5. 產出程式碼   →  pdm codegen ir.json --target vue → React/Vue/HTML/Flutter
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
```

### 2. Codegen：IR → React/Vue/HTML/Flutter

```bash
# 從 IR JSON 產生 React
pdm codegen ir-payload.json --target react --output ./out

# 從 .pen batch_get 匯出的 JSON 產生 Vue
pdm codegen pen-export.json --target vue --output ./out

# 產生 HTML
pdm codegen ir-payload.json --target html --output ./out

# 產生 Flutter
pdm codegen ir-payload.json --target flutter --output ./out

# 可選：產生 utility.css
pdm codegen ir-payload.json --target react --output ./out --with-utility-css
```

### 3. Push：DOM → IR Snapshot

```bash
pdm push http://localhost:5173
pdm push http://localhost:5173 --viewport 375x812
pdm push http://localhost:5173 --selector '#login-form'
```

### 4. Watch：監聽變更自動 Push

```bash
pdm watch http://localhost:5173
```

### 5. Export Tokens：IR → Design Tokens

```bash
pdm export-tokens --from-dir .pdm --output tokens.json
pdm export-tokens --format css --output tokens.css
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
│   ├── cli.py                    # CLI：codegen / push / watch / preview / export-tokens
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
| `figma-sync generate --file-key ...` | `pdm codegen ir.json --target vue` |
| `figma-sync pull --file-key ...` | 棄用：改在 Pencil AI 設計 |
| `FigmaAPIClient` | 棄用 |
| `FigmaToIR` | `PencilToIR` |
| `FigmaMcpTools` | `PencilMcpTools` |
| `figma-sync.config.json` | `pencil.config.json` |
| `requests` 依賴 | 已移除（移至 `[legacy]`） |

---

## License

MIT — 見 [LICENSE](LICENSE)。
