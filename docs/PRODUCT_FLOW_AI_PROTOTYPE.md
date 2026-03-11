# AI Prototype 驅動的正確產品開發流程（對齊版）

> 最實務、最穩、最適合 AI + Figma + PM + FE/BE 並行的標準流程。  
> 已對齊：Phase 2/3 依賴、Figma 產出形式、80% 定義、錯誤流程、與 AiIRIS-pdm 使用時機。

---

## 核心原則（三句）

1. **Figma 決定體驗與視覺，不決定資料模型。**
2. **Domain Model / API Contract 要先穩，再讓 prototype 串接。**
3. **Prototype 是驗證與加速工具，不是直接等於 production code。**

正確順序：

**需求/業務模型 → API Contract → AI Prototype → UX refine → Production Frontend**

---

## 全流程總覽

| Phase | 名稱 |
|-------|------|
| 1 | Product / PM Definition |
| 2 | UX / UI Foundation in Figma |
| 3 | Domain Model Design |
| 4 | API Contract Design |
| 5 | AI Prototype Generation |
| 6 | Prototype + API Parallel Iteration |
| 7 | Figma Fine-tune |
| 8 | Production Frontend Engineering |
| 9 | Integration / QA / UAT |
| 10 | Design System & Spec Backfill |

---

## Phase 1：Product / PM Definition

- **Business Goal**：模組要解決什麼、成功標準、MVP 範圍、不做什麼。
- **User / Role**：admin、operator、reviewer、guest 等。
- **Core Use Cases**：查詢設備、編輯設備、下發命令、查看 telemetry、異常告警等。
- **Business Rules**：角色權限、狀態可刪除條件、表單驗證、審批規則。
- **產出**：PRD / SDD、User flow、Page inventory、Field definition、Business rules。

---

## Phase 2：UX / UI Foundation in Figma

- **與 Phase 3 的關係**：可與 Phase 3 並行或略為領先；至少先有 **entity list + 主要 state**，再畫 sample screens，避免漏畫狀態／權限／error/empty。
- **建立**：UI Style Foundation（color、typography、spacing、radius、shadow、icon、breakpoint、interaction）、Base Components（button、input、select、table、tabs、modal、drawer、card、toast、badge、empty/loading/error）、Sample Screens（list、detail、form、dashboard、modal、search/filter）。
- **目標**：設計語言、元件風格、頁面節奏、主要互動模式；不是畫完全部頁面。
- **產出**：Figma style guide、base component library、sample UI screens。
- **與 pdm 對齊**：若後續要用 Code↔Figma 同步，可約定命名與結構（如 data-figma-name、元件階層），方便 Phase 5/7 使用 pdm push/pull。

---

## Phase 3：Domain Model Design

- **若 Phase 2 已動工**：用 domain/state 回頭檢視 Figma 是否漏畫狀態、權限、錯誤與空狀態。
- **定義**：業務實體（Device、SubDevice、Command、Telemetry、Alert、User、Organization）、關係（has many、owns、belongs to）、實體欄位（id、status、type、timestamp、owner_id、created_at）、state machine（draft→submitted→approved、online/offline/maintenance、pending/success/failed）。
- **產出**：domain entity map、entity relationship、state model、data dictionary。

---

## Phase 4：API Contract Design

- **依據 Domain Model**：設計 GET/POST/PUT/DELETE、request/response schema（field、type、required、nullable、enum、pagination、sort、filter）、錯誤格式（validation、auth、permission、not found、conflict）。
- **產出**：OpenAPI spec、JSON schema、API error contract、mock response examples。
- **用途**：mock server、frontend type 生成、backend 驗證、API doc。

---

## Phase 5：AI Prototype Generation

- **輸入包**：Figma style / sample UI、design tokens、component rules、SDD/PRD、domain model、API contract、mock data、frontend 技術約束。
- **Figma 產出形式**：design tokens 檔 + 關鍵畫面；若使用 **AiIRIS-pdm**，可經 Push 產出 IR / plugin-payload 或指定匯出格式，供 AI 生成 prototype（避免僅「給 Figma 連結」而 AI 無法直接讀取）。
- **前端約束**：Vue 3 / React、TypeScript、Tailwind/SCSS、UI 庫、router、store、i18n、form validation 策略。
- **Prototype 目標**：page skeleton、layout、component 結構、route、form flow、API 整合 placeholder、mock/real API 切換。
- **產出**：可點擊/可執行 prototype、page-level FE scaffolding、draft component 結構。
- **與 pdm 對齊**：若技術棧與 pdm 相容，可用 **pdm push** 將 prototype 畫面同步回 Figma，做「prototype 與 Figma 對齊」的第一次驗證。

---

## Phase 6：Prototype + API Parallel Iteration

- **Backend 並行**：API skeleton、mock server、DB schema、service、permission、workflow、validation、audit/logging。
- **Frontend**：先 mock API，再接 real API；API 未就緒時 fallback mock。
- **80% 前驗證**：user flow 順暢、data shape 合理、page composition 穩、form validation 完整、filter/sort/search 合理、permission 與狀態切換成立、edge case 識別、API 好用。
- **80% ready 定義**：核心流程可跑、主要頁面穩定、元件結構大致確定、API contract 穩定、真實資料格式已驗證、文案/欄位/邏輯大致定案、主要異常已識別；**且 Figma 與 prototype 在主要畫面上已對齊（layout/component 一致）**。
- **產出**：integrated prototype、validated UX flow、validated API usability、issue list / gap list。

---

## Phase 7：Figma Fine-tune

- **時機**：prototype 跑過一輪、80% 驗證後，再回 Figma 精修。
- **內容**：spacing、hierarchy、density、typography、button/CTA、modal/drawer、table 可讀性、長文、empty/loading/error、responsive。
- **不應再大改**：domain model、API contract、core flow、core permissions。
- **產出**：refined Figma screens、component variants、visual QA baseline、design annotations。
- **與 pdm 對齊**：Figma 精修後可用 **pdm pull** 比對差異、產生 patch 報告，再決定哪些納入 Phase 8 production refactor。

---

## Phase 8：Production Frontend Engineering

- **保留**：page structure、route、layout、部分 component shell、API 呼叫模式、state flow 概念。
- **重構**：component 抽象、hooks/composables、form engine、state management、error handling、loading、permission guard、caching、API client。
- **補齊**：accessibility、test、performance、code standards、storybook、tracking、logging、feature flags。
- **產出**：production-ready frontend、reusable component layer、maintainable 架構。

---

## Phase 9：Integration / QA / UAT

- **Integration QA**：FE/BE、auth、permission、error path、upload/download、pagination/filter/sort、responsive、browser。
- **UAT**：PM 驗收、user representative、operation/exception scenario。
- **產出**：tested release candidate、UAT signoff、change request list。

---

## Phase 10：Design System & Spec Backfill

- **回寫**：設計系統（新 component variant、spacing、state、responsive）、工程規格（API final contract、component guideline、storybook docs、implementation note、prompt template）、AI workflow（prompt template、screen generation pattern、review checklist、FE scaffold rule）。
- **產出**：updated design system、updated frontend standard、reusable AI workflow SOP。
- **與 pdm 對齊**：將「Figma ↔ Code 同步規則」與「何時使用 push/pull」寫入團隊 DesignOps SOP，與本流程一致。

---

## 角色分工

| 角色 | 主責 |
|------|------|
| **PM** | scope、business rules、user flow、field definition、acceptance criteria、SDD/PRD |
| **UI/UX** | style foundation、component 行為、page layout、visual hierarchy、usability refinement |
| **Backend** | domain model、API contract、service、DB、workflow/validation/permission |
| **Frontend** | prototype 串接、API 消費、component 架構、production refactor、interaction |
| **AI** | 加速 scaffold、生成 prototype、規格轉換、component 草稿、快速迭代 |

---

## 應先穩定 vs 可持續調整

| 應先穩定 | 可持續調整 |
|----------|------------|
| business goal、domain model、API contract、permission、workflow、field 語意 | layout、spacing、copy、CTA 位置、component 視覺、micro interaction |

---

## 應避免的錯誤流程

| # | 錯誤 | 結果 |
|---|------|------|
| 1 | 先把 Figma 畫滿，再讓 backend 硬配合 UI | API 醜、難維護、UI 一改 backend 炸 |
| 2 | prototype 完全不串 API，只看 mock | 真實資料一進來全壞 |
| 3 | 把 AI 生成的 prototype 當 production code | 短期快、長期難維護 |
| 4 | Figma refine 太晚或完全不回 Figma | 產品粗糙、設計系統失真 |
| 5 | **Domain/API 未定就讓 AI 大量產 prototype** | **prototype 快但一接真實 API 或改業務規則就整片重來** |

---

## 一句話總流程

先用 PM 規格定義業務與流程，用 Figma 建立設計語言與代表頁，再先穩定 Domain Model 與 API Contract，之後用 AI 快速產出可串接 API 的 prototype，在 80% 階段完成 UX、資料模型、流程與 API 可用性驗證（並確保 Figma 與 prototype 主要畫面對齊），再回 Figma 做視覺與交互精修，最後把 prototype 工程化為可維護的 frontend。

---

# 附錄 A：SOP 一頁表

| Phase | 名稱 | 主要動作 | 主責 | 輸入 | 產出 | 備註 |
|-------|------|----------|------|------|------|------|
| 1 | PM Definition | 定義目標、角色、用例、規則、PRD | PM | 業務需求 | PRD、user flow、page list、field、rules | 不急著畫 UI |
| 2 | Figma Foundation | style、base components、sample screens | UI/UX | PRD、entity list + 主要 state | style guide、component lib、sample UI | 可與 Phase 3 並行；約定命名利於 pdm |
| 3 | Domain Model | 實體、關係、欄位、state machine | Backend + PM | PRD、use cases | entity map、ER、state、data dictionary | 回頭檢視 Figma 是否漏狀態 |
| 4 | API Contract | 設計 API、schema、錯誤格式、OpenAPI | Backend | Domain model | OpenAPI、schema、mock examples | 前後端共同語言 |
| 5 | AI Prototype | 以完整輸入包生成可執行 prototype | Frontend + AI | Figma 產出、tokens、PRD、domain、API、mock、技術約束 | runnable prototype、scaffold | Figma 需有明確產出形式；可 pdm push 對齊 |
| 6 | Parallel Iteration | Backend 實作 + FE 串 mock/real API；驗證至 80% | FE + BE | prototype、API contract | integrated prototype、validated flow、issue list | 80% 含設計–程式對齊 |
| 7 | Figma Fine-tune | 精修 spacing、hierarchy、元件、狀態、responsive | UI/UX | prototype 驗證結果 | refined Figma、annotations | 可 pdm pull 產 patch 報告 |
| 8 | Production FE | 保留結構、重構元件與架構、補齊工程內容 | Frontend | refined Figma、prototype、API | production frontend、component layer | 非直接照搬 prototype |
| 9 | Integration / UAT | 整合測試、PM 與 user 驗收 | QA + PM | release candidate | signoff、change list | |
| 10 | Backfill | 回寫 design system、spec、AI workflow SOP | 全員 | 實作結果 | design system、spec、SOP | 含 DesignOps/pdm 規則 |

---

# 附錄 B：各階段交付物清單

| Phase | 交付物 | 格式/說明 | 負責 |
|-------|--------|-----------|------|
| 1 | PRD / SDD | 文件 | PM |
| 1 | User flow | 圖/表 | PM |
| 1 | Page inventory | 清單 | PM |
| 1 | Field definition | 表/文件 | PM |
| 1 | Business rules | 文件 | PM |
| 2 | Figma style guide | Figma | UI/UX |
| 2 | Base component library | Figma | UI/UX |
| 2 | Sample UI screens | Figma | UI/UX |
| 3 | Domain entity map | 圖/表 | Backend + PM |
| 3 | Entity relationship | 圖 | Backend |
| 3 | State model | 圖/表 | Backend |
| 3 | Data dictionary | 表 | Backend |
| 4 | OpenAPI spec | YAML/JSON | Backend |
| 4 | API error contract | 文件 | Backend |
| 4 | Mock response examples | 檔案/Postman | Backend |
| 5 | Runnable prototype | Repo | Frontend + AI |
| 5 | Page-level scaffold | 程式碼 | Frontend |
| 6 | Integrated prototype | Repo | Frontend |
| 6 | Validated UX / API 結論 | 文件/清單 | PM + FE |
| 6 | Issue / gap list | 清單 | 全員 |
| 7 | Refined Figma screens | Figma | UI/UX |
| 7 | Component variants | Figma | UI/UX |
| 7 | Visual QA baseline | Figma / 文件 | UI/UX |
| 8 | Production frontend | Repo | Frontend |
| 8 | Component layer / Storybook | Repo | Frontend |
| 9 | Test report / UAT signoff | 文件 | QA + PM |
| 9 | Change request list | 清單 | PM |
| 10 | Updated design system | Figma + 文件 | UI/UX |
| 10 | Updated frontend standard | 文件 | Frontend |
| 10 | AI workflow SOP | 文件 | 全員 |

---

# 附錄 C：角色責任矩陣（主責 / 協作 / 審閱）

| Phase | PM | UI/UX | Backend | Frontend | AI/工具 |
|-------|-----|--------|---------|----------|---------|
| 1 | 主責 | 審閱 | 協作 | 審閱 | — |
| 2 | 協作 | 主責 | 協作 | 審閱 | — |
| 3 | 主責 | 協作 | 主責 | 審閱 | — |
| 4 | 審閱 | 協作 | 主責 | 協作 | — |
| 5 | 協作 | 協作 | 協作 | 主責 | 主責 |
| 6 | 主責(驗收) | 協作 | 主責(API) | 主責(串接) | 協作 |
| 7 | 審閱 | 主責 | — | 協作 | — |
| 8 | 審閱 | 協作 | 協作 | 主責 | 協作 |
| 9 | 主責(UAT) | 協作 | 協作 | 主責 | — |
| 10 | 協作 | 主責(設計系統) | 協作 | 主責(spec) | 協作(SOP) |

---

*對齊版：已納入 Phase 2/3 依賴、Figma 產出形式、80% 設計對齊、錯誤 5、與 AiIRIS-pdm 於 Phase 2/5/7/10 之使用建議。*
