# AiIRIS-pdm 目前架構確認

> 依據程式碼與既有文件整理，供快速對照。

---

## 一、定位與版本

- **專案**：AiIRIS-pdm（AiIRIS Project Design Model）
- **版本**：0.2.0（`airis_pdm/__init__.py`、`pyproject.toml`）
- **用途**：Code ↔ Figma 雙向同步（Python 管線 + 內建 Figma Plugin）

---

## 二、整體架構（單一管線）

```
                         IR (JSON Schema 2.0)
                         — 統一中間表示層
                                    │
        ┌───────────────────────────┼───────────────────────────┐
        │                           │                           │
        ▼                           ▼                           ▼
┌───────────────┐           ┌───────────────┐           ┌───────────────┐
│  Push         │           │  Figma 內     │           │  Pull          │
│  Code→Figma   │           │  匯入         │           │  Figma→Code    │
│               │           │               │           │               │
│ • Playwright  │  ──JSON──▶│ • 讀 payload  │  ──編輯──▶│ • Figma API   │
│ • DOM Walker │           │ • 建節點      │           │ • FigmaToIR   │
│ • 命名引擎    │           │ • pluginData  │           │ • IRDiffer    │
│ • IR 建構    │           │               │           │ • CodePatcher │
│ • 寫出 JSON  │           │               │           │ • (--apply)  │
└───────────────┘           └───────────────┘           └───────────────┘
 不需 Token                   不需 Token                  需 FIGMA_TOKEN
```

- **單一管線**：僅一套 DOM 擷取 + IR 2.0，無 v1/v2 並存、無 `--v2` 選項。
- **單一 Plugin**：`figma_plugin/` 僅一個入口 `src/code.ts` → `dist/code.js`，讀 `plugin-payload.json`。

---

## 三、目錄與模組

| 路徑 | 說明 |
|------|------|
| **airis_pdm/** | 主套件（Python） |
| ├── `cli.py` | CLI：`push` / `pull` / `preview` |
| ├── `config.py` | 讀取 `figma-sync.config.json` 或 `--config` |
| ├── `dom_extractor.py` | Playwright + 內嵌 DOM_WALKER_V2_JS，擷取 DOM 樹與樣式 |
| ├── `ir_builder.py` | IR 2.0 建構、`save_ir()` 寫出三份 JSON |
| ├── `naming_engine.py` | 命名規則（data-figma-name → 組件 → id → class → fallback） |
| ├── `figma_reader.py` | Figma API 客戶端、FigmaToIR、IRDiffer |
| ├── `code_patcher.py` | IR diff → 原始碼 patch（Tailwind/CSS 建議、--apply） |
| ├── `design_assets.py` | ErSlice 風格 manifest、completeness（選用） |
| └── `__init__.py` | 對外 API、version 0.2.0 |
| **figma_plugin/** | 內建 Figma Plugin（TypeScript） |
| ├── `src/code.ts` | 主邏輯：讀 IR JSON、建 Figma 節點、寫 pluginData |
| ├── `src/figma.d.ts` | Figma API 型別 |
| └── `dist/code.js` | `npm run build` 產出，供 Figma 載入 |
| **schemas/** | `ir_schema.json`（IR JSON Schema） |
| **tests/** | `test_smoke.py`、`test_smart_flatten.py`、`fixtures/minimal.html` 等 |
| **docs/** | ARCHITECTURE_REVIEW、PUSH_FLOW、COMPARISON_V2、ERSLICE_INTEGRATION 等 |

---

## 四、CLI 指令

| 指令 | 說明 | Token |
|------|------|--------|
| `figma-sync push <url>` | Code → 擷取 DOM → IR → 寫出 `.figma-sync/*.json` | 不需 |
| `figma-sync preview <url>` | 僅預覽命名樹，不寫檔 | 不需 |
| `figma-sync pull --file-key KEY [--apply]` | Figma API 讀檔 → IR diff → 報告（或寫回碼） | 需要 |

- 入口：`airis_pdm/cli.py`（或 `python -m airis_pdm.cli`）；安裝後亦可使用 `figma-sync`（pyproject script）。

---

## 五、Push 產出（.figma-sync/）

| 檔案 | 內容 |
|------|------|
| `plugin-payload.json` | 僅 IR 樹（`ir_doc["tree"]`），Figma Plugin 讀取 |
| `figma-import-payload.json` | 完整 IR 文件（version、source、viewport、nameMapping、stats、tree） |
| `name-mapping.json` | figmaName → { sourceFile, selector, componentName } |
| `reference-screenshot.png` | 擷取當下 viewport 截圖 |

---

## 六、依賴與介面

- **Push**：Playwright（Chromium）、本機；不需 Figma 帳號或 Token。
- **Figma 匯入**：在 Figma 內執行，選取本機 JSON；不需 Token。
- **Pull**：呼叫 Figma REST API `GET /v1/files/:file_key`，需 **FIGMA_TOKEN**（環境變數或 config 的 `figma.personalAccessToken`）。

詳見 `docs/ARCHITECTURE_REVIEW.md`（含 Token 說明與後續可補強點）。

---

## 七、對外 API（airis_pdm）

`__init__.py` 匯出：

- 版本：`__version__`
- 擷取：`extract_dom_tree`、`extract_dom_tree_sync`、`ExtractionConfig`
- 命名：`NamingConfig`、`NamingEngine`、`VueComponentDetector`、`ReactComponentDetector`、`preview_naming_tree`
- IR：`IRBuilder` / `IRBuilderV2`、`build_ir_from_extraction`、`save_ir`
- Figma / Diff：`FigmaAPIClient`、`FigmaToIR`、`IRDiffer`
- Patch：`CodePatcher`
- 設定：`load_config`
- 選用：`design_assets`（ErSlice manifest / completeness）

---

*最後對照：程式碼與 docs 2026-02。*
