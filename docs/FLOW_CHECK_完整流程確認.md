# 完整流程再確認 — AI Prototype 驅動產品開發 + pdm / hub 指令對應

> 對應 `PRODUCT_FLOW_AI_PROTOTYPE.md` 與目前實作的 **export-tokens**、**hub workflow** 指令。

---

## 一、全流程一覽（10 Phase）

```
Phase 1   PM Definition（目標、角色、用例、規則、PRD）
    ↓
Phase 2   Figma Foundation（style、base components、sample screens）
    ↓
Phase 3   Domain Model（實體、關係、欄位、state machine）
    ↓
Phase 4   API Contract（OpenAPI、schema、錯誤格式）
    ↓
Phase 5   AI Prototype Generation（完整輸入包 → 可執行 prototype）  ← pdm push + export-tokens
    ↓
Phase 6   Parallel Iteration（BE 實作 + FE 串 API，驗證至 80%）   ← 可選 watch
    ↓
Phase 7   Figma Fine-tune（精修 spacing、hierarchy、元件）       ← pdm pull
    ↓
Phase 8   Production Frontend（重構、補齊工程）
    ↓
Phase 9   Integration / QA / UAT
    ↓
Phase 10  Design System & Spec Backfill（回寫設計系統、規格）   ← pdm push + export-tokens
```

**核心三句**：  
1. Figma 決定體驗與視覺，不決定資料模型。  
2. Domain Model / API Contract 要先穩，再讓 prototype 串接。  
3. Prototype 是驗證與加速工具，不是直接等於 production code。

---

## 二、pdm / hub 指令在流程中的位置

| Phase | 用途 | 指令（pdm 或 hub） | 說明 |
|-------|------|--------------------|------|
| **2** | 約定命名利於後續同步 | （人為）約定 data-figma-name、元件階層 | 方便 Phase 5/7 使用 push/pull |
| **5** | 產出 AI 輸入：IR + tokens | `figma-sync push <url>` → `figma-sync export-tokens` | 從「執行中 prototype/Storybook」擷取 IR，再萃出 tokens.json |
| **5** | 同上（經 hub） | `aiiris pdm push <url>` → `aiiris workflow phase5-prototype --run` | hub 的 --run 會執行 `pdm.export_tokens`（需先有 IR） |
| **6** | 檔案變更即時同步到 Figma | `figma-sync watch <url>` 或 `aiiris pdm watch <url>` | 可選；需 config 內 source.srcRoot |
| **7** | Figma 精修後拉回 code | `figma-sync pull --file-key <KEY> [--apply]` 或 `aiiris workflow phase7-figma-refine --run` | pull 比對差異、產 patch；--apply 套用（需 source.srcRoot） |
| **10** | 回寫設計系統後更新 tokens | `figma-sync push <url>` → `figma-sync export-tokens` 或 `aiiris workflow phase10-backfill --run` | 更新 IR 後再產出 tokens.json |

---

## 三、指令對照（figma-sync vs aiiris）

### 1. 本機直接使用 pdm（figma-sync）

| 目的 | 指令 |
|------|------|
| Code → Figma（產 IR 快照） | `figma-sync push <url>` |
| 監聽檔案變更並自動 push | `figma-sync watch <url>` |
| Storybook 批次產 IR | `figma-sync push-stories <storybook_url>` |
| 從 IR 產出 design tokens | `figma-sync export-tokens [--from-dir .figma-sync] [--output tokens.json] [--format json\|css]` |
| Figma → Code（比對 + 可選套用） | `figma-sync pull --file-key <KEY> [--apply]` |
| 預覽命名樹 | `figma-sync preview <url>` |

### 2. 經 AiIRIS-hub（aiiris）

| 目的 | 指令 |
|------|------|
| Phase 5：看說明 + 產 tokens | `aiiris workflow phase5-prototype`（只看說明）<br>`aiiris workflow phase5-prototype --path <專案路徑> --run`（執行 export_tokens） |
| Phase 7：看說明 + 執行 pull | `aiiris workflow phase7-figma-refine`<br>`aiiris workflow phase7-figma-refine --run`（需 `FIGMA_FILE_KEY` 或 config 內 `plugins.pdm.figma_file_key`） |
| Phase 10：看說明 + 產 tokens | `aiiris workflow phase10-backfill`<br>`aiiris workflow phase10-backfill --path <專案路徑> --run` |
| 直接呼叫 pdm | `aiiris pdm push <url>`、`aiiris pdm pull --file-key <KEY>` 等（見 hub pdm plugin） |

---

## 四、Phase 5 / 7 / 10 實際操作順序

### Phase 5（AI Prototype 輸入）

1. 已有：Figma style / sample UI、PRD、domain model、API contract、技術約束。  
2. 若 prototype 或 Storybook 已可跑：  
   - `figma-sync push http://localhost:5173`（或 Storybook URL）  
   - 會寫入 `.figma-sync/figma-import-payload.json`（及 name-mapping、plugin-payload）。  
3. 產出 tokens 給 AI：  
   - `figma-sync export-tokens`  
   - 預設讀取 `.figma-sync/figma-import-payload.json`，寫出 `tokens.json`（或 `--format css`）。  
4. 將 **IR（或 plugin-payload）+ tokens.json + PRD/API/domain** 一併交給 AI 生成 prototype。

經 hub 時：先 `aiiris pdm push <url>`（在 pdm 或專案端視你設定），再 `aiiris workflow phase5-prototype --path <專案路徑> --run` 即會執行 export_tokens。

### Phase 7（Figma 精修後拉回）

1. 在 Figma 完成精修。  
2. 本地已有先前 push 產生的快照（`.figma-sync/figma-import-payload.json`）。  
3. 執行：  
   - `figma-sync pull --file-key <Figma 檔案 KEY> [--apply]`  
   - 會 diff、產出報告；有設 `source.srcRoot` 時可用 `--apply` 套用變更。  
4. 經 hub：設好 `FIGMA_FILE_KEY` 或 config 後，`aiiris workflow phase7-figma-refine --run` 會執行 pull --apply。

### Phase 10（設計系統回寫後更新 tokens）

1. 設計系統 / 規格已回寫到 Figma 或 code。  
2. 再次從現有畫面產 IR：  
   - `figma-sync push <url>`  
3. 更新 tokens：  
   - `figma-sync export-tokens`（或 `aiiris workflow phase10-backfill --path <專案路徑> --run`）。  
4. 將更新後的 tokens / 規格寫入設計系統文件與 SOP。

---

## 五、路徑與設定注意

- **figma-sync**：  
  - `push` / `pull` / `export-tokens` 的 `--from-dir`、`--output`、config 的 `export.snapshotDir` 等，決定 IR 與 tokens 的讀寫位置。  
  - 若在「專案目錄」執行，通常 `--from-dir .figma-sync`、`--output tokens.json` 即為專案下的 `.figma-sync` 與 `tokens.json`。

- **hub**：  
  - `aiiris workflow ... --path <路徑>` 會把該路徑當成專案根（.figma-sync 與 tokens 輸出在此）。  
  - `aiiris pdm push/pull` 目前由 pdm plugin 依其 `path`（例如 AiIRIS-pdm 目錄）執行 figma-sync；若你要對「某專案」做 push，需在該專案有 config 或透過 path 參數對應到正確的 .figma-sync。

- **Phase 7 pull**：  
  - 需 Figma 檔案 key。  
  - 需先做過 push 才有本地快照可 diff。  
  - 要套用變更時需在 config 設定 `source.srcRoot`。

---

## 六、一句話總流程（與 pdm 對齊）

先用 PM 規格定義業務與流程，用 Figma 建立設計語言與代表頁，穩定 Domain Model 與 API Contract 後，用 **pdm push + export-tokens** 產出 IR 與 design tokens，交給 AI 產出可串 API 的 prototype；在 80% 階段驗證 UX、資料與 API，再回 Figma 精修，用 **pdm pull** 把變更拉回 code；最後將 prototype 工程化，並在 Phase 10 用 **push + export-tokens** 回寫設計系統與規格。

---

*最後更新：對應 export-tokens CLI、hub workflow phase5/7/10、PRODUCT_FLOW_AI_PROTOTYPE 附錄。*
