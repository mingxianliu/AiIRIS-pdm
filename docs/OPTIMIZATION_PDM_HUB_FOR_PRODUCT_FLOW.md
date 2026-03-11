# 優化 pdm 與 hub 以符合「AI Prototype 驅動產品流程」

> 對照 [PRODUCT_FLOW_AI_PROTOTYPE.md](PRODUCT_FLOW_AI_PROTOTYPE.md) 十階段，列出 pdm / hub 現有支援、缺口與具體優化建議。

---

## 一、各 Phase 對應 pdm / hub 現況與缺口

| Phase | 名稱 | pdm 現有 | hub 現有 | 缺口 |
|-------|------|----------|----------|------|
| 1 | PM Definition | — | spec 插件、agent | 無需改 pdm；hub 可提供「流程檢查清單」 |
| 2 | Figma Foundation | push 產出 IR/tokens | pdm.push、MCP get_design_tokens | pdm：產出 **design tokens 檔** 供 AI；hub：Phase 2 指引 |
| 3 | Domain Model | — | — | 非 pdm/hub 主責；hub 可連結 spec/OpenAPI |
| 4 | API Contract | — | — | 同上 |
| 5 | AI Prototype | push、generate | pdm.push、pdm.generate、get_figma_ir、get_design_tokens、get_ir_completeness | pdm：**export-tokens** 或 push 內建寫出 tokens；hub：**pdm.watch、pdm.push-stories** 未暴露 |
| 6 | Parallel Iteration | watch、push、pull | pdm.push、pdm.pull | hub：**pdm.watch** 未支援；pdm：可加 **--phase=prototype** 預設選項 |
| 7 | Figma Fine-tune | pull（含 Layout Integrity） | pdm.pull、diff_ir_with_snapshot、get_ir_completeness | hub：pull 後可提示「是否產生 patch 報告」；pdm：pull 輸出可標註 phase 建議 |
| 8 | Production FE | generate | pdm.generate | 可加 **--production** 或 preset（storybook、tests、a11y 註記） |
| 9 | Integration / UAT | — | tdd 插件 | 無需改 pdm；hub 可串 tdd + pdm |
| 10 | Backfill | pull、design_assets | pdm.pull、list_snapshots、get_design_tokens | pdm：**design tokens 匯出** 與 design system 回寫指引；hub：**workflow backfill** 指令 |

---

## 二、AiIRIS-pdm 優化建議

### 2.1 支援「流程階段」的產出（Phase 2 / 5 / 10）

- **設計 Tokens 匯出**
  - **現況**：push 產出 IR、name-mapping、screenshot，design_assets 可寫 ErSlice manifest。
  - **建議**：新增 **`figma-sync export-tokens [--from-push-dir .figma-sync] --output tokens.json`**，從既有 IR（或本次 push）擷取 color、typography、spacing 等，產出單一 JSON 供 Phase 5 的 AI 輸入包與 Phase 10 的 design system 回填。
  - **實作要點**：讀 `figma-import-payload.json`，遍歷 tree 蒐集 fills、fontFamily、fontSize、spacing，去重後輸出；可選 `--format css` 產出 CSS variables。

### 2.2 Phase 5 / 6：明確「給 AI 的輸入包」產出

- **建議**：在文件與 CLI 中明確標註「**AI Prototype 輸入包**」可由 pdm 產出：
  - `figma-sync push <url>` → `.figma-sync/plugin-payload.json`（或 IR）＋ **export-tokens** → `tokens.json`。
  - 於 README 或 `docs/PRODUCT_FLOW_AI_PROTOTYPE.md` 加一節「Phase 5：用 pdm 準備 Figma 產出」，列出指令與檔案清單（IR、tokens、screenshot、name-mapping）。

### 2.3 Phase 6：Watch 與 config 對齊流程

- **現況**：`figma-sync watch <url>` 已支援，依 config `source.srcRoot` 監聽。
  - **建議**：在 `figma-sync.config.json` 範例或 schema 中加 **可選欄位 `phase`**（如 `"phase": "prototype"`），未來可依 phase 調整預設（例如 prototype 階段預設寫出 tokens、不寫 ErSlice）。非必須，可當文件約定先做。

### 2.4 Phase 7：Pull 產出標註「建議 Phase 8 處理」

- **建議**：`figma-sync pull` 的 console 輸出或報告中，加一句「本差異報告建議於 **Phase 8 Production Frontend** 中擇項納入 refactor」，並在 `docs/PRODUCT_FLOW_AI_PROTOTYPE.md` Phase 7 再次引用。

### 2.5 Phase 8：Generate 的「生產用」選項

- **建議**：若尚未有，可為 **`figma-sync generate`** 增加選項或 preset，例如：
  - `--with-storybook`：產出 Storybook story 骨架。
  - `--with-a11y`：在產出註解或屬性中標註 a11y 建議。
  - 或 `--preset production`：同時開啟多個與 Phase 8 對齊的選項（可先在文件說明，實作後補）。

### 2.6 Phase 10：Design System 回填說明

- **建議**：在 `docs/` 新增 **「Design System Backfill 與 pdm」** 短文（或併入 PRODUCT_FLOW），說明：何時用 **pull** 取回 Figma 變更、何時用 **export-tokens** 更新 token 檔、如何與 design system 文件/Storybook 同步，並連結 Phase 10 交付物清單。

---

## 三、AiIRIS-hub 優化建議

### 3.1 PDM Plugin 補齊 pdm 能力（Phase 5 / 6 / 7）

- **pdm.watch**
  - **現況**：hub 僅暴露 `pdm.push`、`pdm.pull`、`pdm.generate`，未暴露 **watch**、**push-stories**。
  - **建議**：在 `plugins/pdm/plugin.py` 新增：
    - **`pdm.watch`**：傳入 `url`、可選 `viewport`、`src_root`、`config`，呼叫 `figma-sync watch`（或 subprocess 執行對應指令），供 Phase 6 迭代時「改碼即同步」。
    - **`pdm.push_stories`**：傳入 `storybook_url`，呼叫 `figma-sync push-stories`，供 Phase 5/6 批次同步 Storybook 元件到 Figma。

- **pdm.push / pdm.pull 參數對齊**
  - **建議**：`_pdm_push` 支援可選參數：`viewport`、`selector`、`erslice`、`config`，並傳給底層 figma-sync，以支援 Phase 5/6 的進階情境。  
  - `_pdm_pull` 支援可選 `config`、`output_report`（是否產出 patch 報告路徑），以對齊 Phase 7。

### 3.2 流程階段指令（Phase-aware commands）

- **建議**：新增 **workflow** 子命令或對等概念，讓使用者依「階段」一鍵執行建議動作，例如：
  - **`aiiris workflow phase5-prototype --url <app_url> [--figma-file-key <key>]`**  
    說明：準備 AI Prototype 輸入包；內部可呼叫 pdm.push、export-tokens（若 pdm 已實作），並輸出「輸入包清單」與建議下一步。
  - **`aiiris workflow phase7-figma-refine --file-key <key> [--apply]`**  
    說明：執行 pdm.pull、若有 Layout Integrity 警告則提示，並可選產出 patch 報告路徑。
  - **`aiiris workflow phase10-backfill --file-key <key> [--tokens-out tokens.json]`**  
    說明：呼叫 pdm.pull / list_snapshots / get_design_tokens，並可選匯出 tokens、寫入指定路徑，供 design system 回填。

 實作可先以「腳本包裝既有 hub 指令 + 說明文案」方式，再視需求收納為正式子命令。

### 3.3 MCP 工具與流程對齊

- **現況**：hub 已提供 `pdm.get_figma_ir`、`pdm.diff_ir_with_snapshot`、`pdm.get_design_tokens`、`pdm.get_ir_completeness`、`pdm.list_snapshots`，利於 Phase 5（AI 讀取 Figma 結構/tokens）與 Phase 7（diff、完整度評估）。
  - **建議**：在 MCP 工具描述或 hub 文件中，註明建議使用階段（例如「Phase 5：AI Prototype 輸入」「Phase 7：Figma 精修後比對」），讓 Agent 或人類依流程選擇工具。

### 3.4 配置與文件

- **建議**：在 hub 的 config 範例（如 `~/.aiiris/config.yaml`）或 docs 中：
  - 註明 **figma_token**、**pdm path**、**figma_sync_command** 與產品流程的關係（Phase 5/6/7 會用到）。
  - 新增一節「**與 AI Prototype 產品流程對齊**」，連結至 AiIRIS-pdm 的 `PRODUCT_FLOW_AI_PROTOTYPE.md`，並列出各 Phase 建議使用的 hub 指令與 MCP 工具。

### 3.5 與 TDD / Spec 插件協作（Phase 9）

- **建議**：在 hub 文件或 workflow 說明中，註明 Phase 9 可搭配 **tdd** 插件（例如 `aiiris tdd run`）執行測試，並可與 **pdm.pull** 產出的變更清單交叉參考（例如：先 pull 取得 Figma 變更，再跑 tdd 確保 refactor 未破壞既有行為）。

---

## 四、建議實作優先級

| 優先級 | 項目 | 所屬 | 說明 |
|--------|------|------|------|
| P0 | hub：暴露 **pdm.watch**、**pdm.push_stories** | hub | 補齊 Phase 5/6 常用能力，改動集中於 plugin |
| P0 | hub：**pdm.push** 支援 viewport、selector、config | hub | 與 pdm 實際用法一致，利於 Phase 5/6 |
| P1 | pdm：**export-tokens**（從 IR 產出 tokens 檔） | pdm | 明確支援 Phase 2/5/10 的「Figma 產出形式」 |
| P1 | 文件：Phase 5「用 pdm 準備 AI 輸入包」、Phase 10「Design System 與 pdm」 | pdm + hub | 降低落地門檻，無需改 code 即可對齊流程 |
| P2 | hub：**workflow** 指令（phase5 / phase7 / phase10） | hub | 一鍵對齊階段，可先腳本再正式化 |
| P2 | pdm：generate **--with-storybook** 或 **--preset production** | pdm | 對齊 Phase 8 交付物 |
| P3 | pdm：config 可選 **phase** 欄位、pull 輸出 phase 建議文案 | pdm | 流程語意更清晰 |

---

## 五、小結

- **pdm**：透過 **export-tokens**、文件對齊（Phase 5 輸入包、Phase 10 回填）、以及可選的 generate preset / phase 欄位，讓「Figma 產出形式」與「Design System 回填」明確對應流程。
- **hub**：透過 **補齊 pdm.watch / push_stories / push 參數**、可選的 **workflow 階段指令**、以及 **config/docs 與流程對齊**，讓同一入口即可依 Phase 操作 pdm 與 MCP，並與 TDD/Spec 協作。

以上優化後，pdm 與 hub 即可在「AI Prototype 驅動的正確產品開發流程」中擔任 Phase 2 / 5 / 6 / 7 / 8 / 10 的明確支撐，而不偏離既有架構。
