# AiIRIS-pdm 專案整理與文件索引

> 本專案完整整理，供快速導覽與交接。最後更新：2026-02。

---

## 一、專案概覽

| 項目 | 說明 |
|------|------|
| **名稱** | AiIRIS-pdm（AiIRIS Project Design Model） |
| **版本** | 0.3.0 |
| **用途** | Code ↔ Figma 雙向同步 + DesignOps：Push / Pull / **Watch** / **Storybook Sync**，含 Smart Image、CJK Font、Layout Integrity |
| **輸入** | Push：網站 URL；Watch：URL + 監聽 srcRoot；push-stories：Storybook URL；Pull：file key + FIGMA_TOKEN |
| **產出** | `.figma-sync/`：plugin-payload.json、figma-import-payload.json、name-mapping.json、reference-screenshot.png |
| **技術** | Python 3.10+、Playwright、requests、**watchdog**；Figma Plugin：TypeScript → dist/code.js |
| **五大功能 (0.3.0)** | 1 Watch Mode 2 Storybook Sync 3 Smart Image Compression 4 Smart CJK Font 5 Layout Integrity Check — 見 CHANGELOG |

---

## 二、目錄與模組一覽

### 根目錄

| 路徑 | 說明 |
|------|------|
| `README.md` | 專案說明、快速開始、設定範例 |
| `CHANGELOG.md` | 版本變更紀錄 |
| `pyproject.toml` | 套件設定、script `figma-sync` |
| `figma-sync.config.json` | 設定範例（figma、source、viewport、naming、export） |

### airis_pdm/（主套件）

| 模組 | 職責 |
|------|------|
| `cli.py` | 入口：`push` / `pull` / `preview` |
| `config.py` | 讀取 `figma-sync.config.json` 或 `--config` |
| `dom_extractor.py` | Playwright 開瀏覽器、內嵌 DOM_WALKER_V2_JS 擷取樹與樣式 |
| `ir_builder.py` | IR 2.0 建構、`build_ir_from_extraction`、`save_ir` 寫三份 JSON |
| `naming_engine.py` | 命名規則、preview_naming_tree |
| `figma_reader.py` | FigmaAPIClient、FigmaToIR、IRDiffer |
| `code_patcher.py` | IR diff → 原始碼 patch（--apply） |
| `design_assets.py` | ErSlice manifest、completeness（選用） |
| `__init__.py` | 對外 API、`__version__` |

### figma_plugin/

| 路徑 | 說明 |
|------|------|
| `src/code.ts` | 主邏輯：讀 IR JSON、建 Figma 節點、寫 pluginData |
| `src/figma.d.ts` | Figma API 型別 |
| `dist/code.js` | `npm run build` 產出，供 Figma 載入 |
| `manifest.json` | Plugin 資訊 |

### tests/

| 檔案 | 說明 |
|------|------|
| `test_smoke.py` | 匯入、公開 API、build_ir_from_extraction |
| `test_ir_flattening.py` | IR 壓扁邏輯 |
| `fixtures/minimal.html` | E2E push 驗證用 |

### schemas/

| 檔案 | 說明 |
|------|------|
| `ir_schema.json` | IR JSON Schema |

---

## 三、docs 文件一覽

| 文件 | 內容 |
|------|------|
| **[INDEX.md](INDEX.md)**（本文件） | 專案整理與文件索引 |
| [ARCHITECTURE_CURRENT.md](ARCHITECTURE_CURRENT.md) | 目前架構對照（管線、模組、CLI、Token） |
| [ARCHITECTURE_REVIEW.md](ARCHITECTURE_REVIEW.md) | 架構審查、Push/Pull 完整性、**為何需要 Token** |
| [PUSH_FLOW.md](PUSH_FLOW.md) | Push 程式碼流程（cli → dom_extractor → ir_builder → save_ir） |
| [COMPARISON_V2.md](COMPARISON_V2.md) | 管線功能矩陣（vs html-figma） |
| [ERSLICE_INTEGRATION.md](ERSLICE_INTEGRATION.md) | 與 ErSlice 設計資產對齊 |
| [INSIGHT_AiIRIS-tdd_vs_AiIRIS-pdm.md](INSIGHT_AiIRIS-tdd_vs_AiIRIS-pdm.md) | 與 AiIRIS-tdd 雷同點、差異、Playwright 使用 |

---

## 四、常用指令速查

```bash
# 安裝（含 watchdog，Watch 必要）
pip install -e ".[dev]"
playwright install chromium

# Push（不需 Token）
figma-sync push http://localhost:5173
figma-sync push http://localhost:5173 --viewport 375x812
figma-sync preview http://localhost:5173

# Watch（即時監聽並自動 Push）
figma-sync watch http://localhost:5173

# Storybook 批次同步（6.4+）
figma-sync push-stories http://localhost:6006

# Figma Plugin 建置
cd figma_plugin && npm run build

# Pull（需 FIGMA_TOKEN；會顯示 Layout Integrity 警告若適用）
export FIGMA_TOKEN=...
figma-sync pull --file-key YOUR_FILE_KEY
figma-sync pull --file-key YOUR_FILE_KEY --apply

# 測試
pytest tests/ -v
```

---

## 五、與其他專案關係

- **figma-code-sync**：IR 管線與命名邏輯來源；本專案為 Python 版並整合 ErSlice 概念。
- **ErSlice**：design-assets、manifest、設計 token 概念對齊。
- **AiIRIS-tdd**：同屬 AiIRIS 工具家族；職責不同（TDD vs 設計同步），不合併；兩者皆依賴 Playwright（用途不同）。

---

*整理依據：AiIRIS-pdm 程式碼與 docs，2026-02。*
