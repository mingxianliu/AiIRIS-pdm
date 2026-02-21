# AiIRIS-tdd 與 AiIRIS-pdm 雷同點與洞察

> 兩專案對照與可複用模式整理。

---

## 一、一句話對照

| 專案 | 定位 | 主要 input | 主要 output |
|------|------|------------|-------------|
| **AiIRIS-tdd** | AI 驅動的 TDD CLI（測試規劃→執行→分析→修復→報告） | 專案路徑 `--project` | 測試報告（Markdown/HTML）、AI 決策紀錄 |
| **AiIRIS-pdm** | Code ↔ Figma 雙向同步 CLI（DOM→IR→Figma / Figma→diff→patch） | Push: 網站 URL；Pull: Figma file key | IR JSON、plugin-payload、name-mapping、截圖 |

---

## 二、雷同點（為什麼會覺得像）

### 1. 同屬 AiIRIS 生態、都是「拆出來的 CLI」

- **AiIRIS-tdd**：從 AiIRIS 主專案拆出的 **AI-TDD 工作流**（Coach、Vibe Coding、多 AI 協調、分層測試執行、報告）。
- **AiIRIS-pdm**：從 **figma-code-sync** + ErSlice 概念彙整成的 **設計模型管線**（DOM 擷取、IR、Figma Plugin）。
- 兩者都是「單一職責的獨立 Python CLI」，可單獨安裝、單獨使用，不再綁在 monolith 裡。

### 2. 專案結構很像

```
AiIRIS-tdd/                    AiIRIS-pdm/
├── ai_tdd_cli/                ├── airis_pdm/
│   ├── core/                  │   ├── (無 core 子包，模組平鋪)
│   ├── services/              │   ├── dom_extractor, ir_builder,
│   ├── executors/              │   │   naming_engine, figma_reader,
│   ├── reporters/              │   │   code_patcher, config, design_assets
│   └── cli/                    │   └── cli.py
├── tests/                      ├── tests/
│   ├── unit/                   │   ├── test_smoke.py, test_*...
│   └── integration/            │   └── fixtures/
├── docs/                       ├── docs/
├── pyproject.toml              ├── pyproject.toml
└── README.md                   └── README.md
```

- 都是 **Python 3.10+**、**pyproject.toml**、**單一主套件**、**tests + docs**。
- 差在 tdd 用 **Click + Rich**、子包較多（core/services/executors/reporters）；pdm 用 **argparse**、模組平鋪。

### 3. 都是「管線型」、config 驅動

- **AiIRIS-tdd**：`run` 時帶 `--project`、`--test-command`，內部有 config（max_iterations、auto_fix、project_path），流程是 **規劃 → 檢查 → 測試 → 分析 → 修復 → 報告**。
- **AiIRIS-pdm**：`push <url>` / `pull --file-key`，讀 `figma-sync.config.json`（viewport、source、naming、export），流程是 **擷取 → 命名 → IR → 寫出** 或 **Figma API → IR diff → patch**。
- 共通點：**輸入（路徑/URL/key）+ 設定 → 多步驟管線 → 產出檔案**。

### 4. 都有「多步驟、可單獨測」的設計

- **AiIRIS-tdd**：unit（coach、analyzer、vibe_coding、layered）+ integration（workflow、report）+ 分層執行（unit → integration → e2e）。
- **AiIRIS-pdm**：smoke（匯入、公開 API、build_ir_from_extraction）、fixtures（minimal.html）、可單獨跑 push 或 plugin build。
- 兩邊都適合「單步驗證 + 整合驗證」。

### 5. 品牌與發行方式一致

- **pyproject**：authors 都掛 AiIRIS；tdd 用 `ai-tdd-cli`、pdm 用 `airis-pdm`。
- **版本**：tdd 0.1.0-alpha、pdm 0.2.0。
- 都是「可 pip install、可當獨立工具」的 CLI，不是 library-first。

---

## 三、差異（職責不同）

| 維度 | AiIRIS-tdd | AiIRIS-pdm |
|------|------------|------------|
| 領域 | 測試、品質、AI 決策 | 設計、Code–Figma 同步 |
| 依賴 | Click, Rich, httpx, pyyaml, **Playwright** | **Playwright**, requests |
| **Playwright** | **有依賴**：E2E 前用 Python 確保 Chromium 已安裝（`playwright install chromium`），再執行 `npx playwright test` 跑使用者 E2E | **直接使用**：Python API 開瀏覽器、擷取 DOM、截圖（Push 核心） |
| 外部介面 | 本機專案、Ollama、雲端 CLI | 本機 URL、Figma API（Pull 需 Token） |
| 產物 | 報告、狀態、決策紀錄 | JSON payload、截圖、name-mapping |
| 多 AI | Coach + 多 CLI（Claude/Gemini/Codex/Copilot/Local） | 無；純管線，無 AI 推理 |

---

## 四、洞察與建議

### 1. 雷同點的本質

- **同源策略**：都是從大系統「拆出單一職責 CLI」的結果，所以會有類似的**專案形狀**（結構、config、管線、測試分層）。
- **可複用模式**：若未來再拆第三個 AiIRIS-xxx CLI，可沿用：  
  - 單一主包 + pyproject + 明確 input（路徑/URL/key）  
  - config 檔 + 多步驟管線 + 產出到指定目錄  
  - unit + integration + 少量 e2e/fixtures  

### 2. 要不要合併？

- **不建議合併成一個 repo**：領域不同（測試 vs 設計）、依賴不同、使用者情境不同；維持兩個獨立 CLI 較清晰。
- **可考慮的共用**：  
  - **共用的 docs 模板**（例如「AiIRIS CLI 使用慣例」）：如何寫 README、config 範例、如何跑 tests。  
  - **共用的 meta**：若有一個「AiIRIS」官網或總覽頁，可並列 ai-tdd-cli 與 airis-pdm，說明各自 input/output。

### 3. 命名與發現性

- **AiIRIS-tdd** → 套件名 `ai-tdd-cli`、指令 `ai-tdd`（若對外）；**AiIRIS-pdm** → 套件名 `airis-pdm`、指令 `figma-sync`。  
- 雷同點在「專案結構與工作方式」，而不是指令名稱；若要在文件裡標示「同屬 AiIRIS」，可在兩邊 README 都加一句：「Part of the AiIRIS tool family (e.g. AiIRIS-tdd for TDD, AiIRIS-pdm for Figma sync).」

---

## 五、對照表（快速查）

| 項目 | AiIRIS-tdd | AiIRIS-pdm |
|------|------------|------------|
| 套件名 | ai-tdd-cli | airis-pdm |
| 主包 | ai_tdd_cli | airis_pdm |
| CLI 框架 | Click | argparse |
| 典型指令 | ai-tdd run / scan / analyze / report | figma-sync push / pull / preview |
| Input | --project 路徑 | push: URL；pull: --file-key |
| Config | 程式內 config 物件 + 可擴充 | figma-sync.config.json |
| 版本 | 0.1.0 | 0.2.0 |

---

*依據兩專案 README、pyproject、目錄結構與既有文件整理。*
