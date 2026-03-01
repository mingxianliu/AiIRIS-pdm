# PDM 在 Hub 架構下的六步驟完成確認流程

日期: 2026-03-01
目標: 以 AiIRIS-hub 為協調層，確認 PDM 的六大步驟能被完整執行，形成端到端閉環。

## 前置假設
- Hub 負責命令路由、能力匹配與插件調度。
- PDM Plugin 對外提供 Figma to Code 能力。
- Tauri Plugin 提供 LLM 代碼優化能力。
- TDD Plugin 提供測試生成與驗證能力。
- 外部工具以輕量包裝器方式接入 Hub（如 Figma API、opencode 等）。

## 入口描述 (只有兩種起點)

### 入口 A: 從規格開始
- 目的: 先完成規格文件，再進入 Figma 調適與產碼。
- Hub 指令:
  - aiiris init
  - aiiris spec init --name <SPEC_NAME>
  - aiiris spec validate --name <SPEC_NAME>
- 接續步驟: 進入 Step 2 (Figma 手動調適) 與 Step 4 (PDM CLI 產碼)。

### 入口 B: 從 Figma 開始
- 目的: 已有設計或直接在 Figma 生成 wireframe。
- Hub 指令:
  - aiiris pdm pull --file-key <FILE_KEY> [--apply]
  - aiiris pdm generate --file-key <FILE_KEY> --target <react|vue|html|flutter> --output <DIR>
  - aiiris pdm push --url <URL>
- 手動/CLI:
  - 在 Figma 內完成 wireframe 與規格補註
  - 使用 PDM CLI 產生 Vue/React

## 六大步驟與 Hub 協調流程

### 1) 需求收集與規格定義
- 入口: 使用者先完成規格文件（spec-kit 產出或人工整理），此流程從規格開始。
- Hub 行為:
  - Smart Hub 分析需求，判斷需要 PDM 能力。
  - 若有 Spec 管理需求，調用 spec-kit 插件取得結構化規格。
- 完成條件:
  - 產出結構化規格（MD/JSON），可供 Figma Prompt 或後續生成使用。

### 2) AI 生成 Wireframe / Prototype
- 入口: 使用者在 Figma 內用 UX Pilot / Figma Make 生成或調整。
- Hub 行為:
  - 無 (此步驟為 Figma 內手動操作)
- 完成條件:
  - 指定的 Figma 檔案產出可編輯 frames，含基本互動連結。

### 3) 補充規格細節與使用者流程
- 入口: 使用者在 Figma 內補註解、流程圖、Dev Mode 標記。
- Hub 行為:
  - 無 (此步驟為 Figma 內手動操作)
- 完成條件:
  - Figma 內含關鍵註解，或產出對應的註解文件與流程描述。

### 4) 生成 Vue / React 程式碼
- 入口: 使用者以 AiIRIS-pdm CLI 執行 figma-sync generate。
- Hub 行為:
  - 無 (Hub 尚未整合 pdm.generate)
- 完成條件:
  - 產出可編譯的 Vue/React 程式碼與必要的樣式檔。

### 5) 分享與團隊協作
- 入口: Hub 接收 publish/share 指令。
- Hub 行為:
  - 產出可分享的連結或文件（Figma link、規格 MD、程式碼片段）。
  - 可同步到指定的平台（Notion/Jira/Confluence），視擴充而定。
- 完成條件:
  - 相關連結與文件被整合並可被團隊成員訪問。

### 6) 迭代與驗證
- 入口: Hub 接收 feedback 或 revision 指令。
- Hub 行為:
  - TDD Plugin 生成對應測試或驗證步驟。
  - 若需要重新生成設計或程式碼，回到步驟 2 或 4。
- 完成條件:
  - 測試通過或驗證報告產出，並記錄迭代版本。

## PDM 需要確保的關鍵能力
- Figma to IR: 能穩定取得設計節點與結構資訊。
- IR to Code: 能依 target 產生 Vue/React/HTML。
- 可追蹤輸出: 輸出目錄結構一致，可與 Hub 任務流程對接。
- 外部工具整合: 能接受 Hub 的命令與參數，不直接依賴使用者手動操作。

## Hub 對 PDM 的最小協調介面 (目前狀態)
- 已有 Hub 插件指令 (非 Figma/PDM 產線):
  - speckit.init / speckit.validate / speckit.list / speckit.read / speckit.update
  - tdd.run / tdd.watch / agent.chat / agent.analyze / spec.init / spec.validate
  - llm.chat / llm.generate / llm.list_models
  - project.init / project.info / deps.add / deps.remove / deps.update / deps.list / deps.lock / venv.create / build.run / build.publish
- 已在 Hub 實作的 Figma/PDM 介面:
  - pdm.generate / pdm.pull / pdm.push
- AiIRIS-pdm CLI 可用指令:
  - figma-sync generate (Figma -> New Frontend)
  - python -m airis_pdm.cli push / pull / preview / watch

## 六步驟對應的實際可用指令/事件

手動定義: 無法透過 Hub 現有插件指令完成，且需要使用者在 Figma/文件工具中直接操作的步驟。
編號對齊: 下列 Step 1-6 與「六大步驟與 Hub 協調流程」的順序一致，且保留補充規格這一步。

## 操作細節 (PDM 必須記載)

### PDM CLI: Figma -> New Frontend (Generate)
- 目的: 從 Figma 生成新前端專案檔 (React/Vue/HTML/Flutter)。
- 必要輸入:
  - FIGMA_TOKEN
  - fileKey
  - target (react|vue|html|flutter)
- 指令:
  - figma-sync generate --file-key <FILE_KEY> --target <react|vue|html|flutter> --output <DIR>
- 常用選項:
  - --all-pages
  - --page / --page-index
  - --with-utility-css

### PDM CLI: Code -> Figma (Push)
- 目的: 將目前前端畫面轉成 IR snapshot 給 Figma Plugin 匯入。
- 指令:
  - python -m airis_pdm.cli push <url>
- 產出:
  - .figma-sync/plugin-payload.json
  - .figma-sync/reference-screenshot.png

### PDM CLI: Figma -> Code (Pull)
- 目的: 從 Figma 讀取 IR，並可選擇套用到程式碼。
- 指令:
  - python -m airis_pdm.cli pull --file-key <FILE_KEY> [--apply]

### PDM CLI: Preview / Watch
- 目的: 預覽命名樹或監聽檔案變更自動 push。
- 指令:
  - python -m airis_pdm.cli preview <url>
  - python -m airis_pdm.cli watch <url>

## 六步驟對照表 (Repo / Plugin / 手動)

| 步驟 | Repo | Hub 插件 | 現況 |
|------|------|----------|------|
| 1. 需求收集與規格定義 | spec-kit / AiIRIS-tdd | speckit / tdd | 可用 (規格管理與驗證) |
| 2. AI 生成 Wireframe / Prototype | 無 | 無 | 需手動 (Figma 內操作) |
| 3. 補充規格細節與使用者流程 | 無 | 無 | 需手動 (Figma 內操作) |
| 4. 生成 Vue / React 程式碼 | AiIRIS-pdm | 無 | 可用 (CLI)，Hub 未整合 |
| 5. 分享與團隊協作 | 無 | 無 | 需手動 (分享連結/文件) |
| 6. 迭代與驗證 | AiIRIS-tdd | tdd | 可用 (測試/驗證) |

### Step 1: 需求收集與規格定義
- Hub 可用:
  - speckit.init / speckit.validate / speckit.list / speckit.read / speckit.update
  - spec.init / spec.validate (TDD 插件)
- 事件:
  - 無對應事件

### Step 2: AI 生成 Wireframe / Prototype
- Hub 可用:
  - pdm.pull (用於從 Figma 取得內容，仍需手動調適)
- 使用者需手動:
  - Figma 內調整 layout、互動連結與元件結構

### Step 3: 補充規格細節與使用者流程
- 使用者需手動:
  - Figma 註解、流程圖、Dev Mode 標記

### Step 4: 生成 Vue / React 程式碼
- Hub 可用:
  - pdm.generate
- AiIRIS-pdm CLI 可用:
  - figma-sync generate --target react|vue|html|flutter
- 事件:
  - 無對應事件

### Step 5: 分享與團隊協作
- Hub 可用:
  - 無 (尚未有 publish 指令)
- 使用者需手動:
  - Figma Share link / 文件貼入 Notion 或 Jira

### Step 6: 迭代與驗證
- Hub 可用:
  - tdd.run / tdd.watch
- 事件:
  - file.changed / test.failed / test.passed

## 驗收清單 (最小可行)
- 需求被轉為結構化規格。
- Figma 內有可編輯的 prototype。
- 規格與流程註解被附加或輸出。
- Vue/React 代碼可成功生成。
- 分享文件可被團隊存取。
- 迭代後測試或驗證報告可追蹤。

## 風險與限制
- Figma API 速率限制或權限不足，會影響步驟 2/3。
- LLM 生成品質不穩定，需要人工校正。
- 如果 PDM 只提供 CLI，Hub 需以 subprocess 包裝並處理錯誤。
